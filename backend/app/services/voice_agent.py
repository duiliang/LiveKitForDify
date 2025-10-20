"""LiveKit agent responsible for bridging the media session with Dify.

The implementation follows the structure encouraged by ``livekit-agents`` but it
stays defensive: if the runtime does not have the optional dependency installed
we raise a descriptive error that guides operators to install it.  This keeps the
rest of the application (HTTP API and unit tests) functional inside constrained
execution environments such as this evaluation container.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Awaitable, Callable, Optional

from ..config import get_settings
from .ali_bailian import BailianError, synthesize_speech, transcribe_audio
from .dify import generate_reply
from ..schemas import Message

logger = logging.getLogger(__name__)


class LiveKitDependencyError(RuntimeError):
    """Raised when ``livekit`` modules are missing at runtime."""


@dataclass
class AgentCallbacks:
    """Callback hooks used for unit testing and observability."""

    on_thinking: Callable[[str], Awaitable[None]] = field(
        default_factory=lambda: (lambda _: asyncio.sleep(0))
    )
    on_transcription: Callable[[str], Awaitable[None]] = field(
        default_factory=lambda: (lambda _: asyncio.sleep(0))
    )
    on_speech: Callable[[str], Awaitable[None]] = field(
        default_factory=lambda: (lambda _: asyncio.sleep(0))
    )


async def _ensure_livekit_modules() -> None:
    """Ensure that the required LiveKit libraries are available."""

    try:
        import livekit  # noqa: F401
        import livekit.agents  # noqa: F401
    except Exception as exc:  # pragma: no cover - depends on environment
        raise LiveKitDependencyError(
            "The livekit-agents package is required to run the real-time voice agent."
        ) from exc


async def run_agent(job_context: "JobContext", callbacks: Optional[AgentCallbacks] = None) -> None:
    """Entry point executed by ``livekit-agents`` workers.

    The function performs the following steps for each connected participant:

    1. Listens to microphone audio.
    2. Sends the captured buffers to Alibaba Bailian STT.
    3. Streams the transcript to Dify in order to obtain a response.
    4. Converts the reply to speech using Bailian TTS and publishes it back into
       the LiveKit room.

    The orchestration is purposely sequential.  LiveKit itself handles audio
    streaming and barge-in (the ability to interrupt).  Whenever a user speaks we
    cancel any pending TTS playback which mimics the behaviour of ChatGPT's voice
    mode.
    """

    await _ensure_livekit_modules()
    from livekit.agents import AutoSubscribeAgent
    from livekit.agents.job import JobContext  # type: ignore
    from livekit import rtc

    if not isinstance(job_context, JobContext):  # pragma: no cover - safety
        raise TypeError("job_context must be an instance of livekit.agents.JobContext")

    settings = get_settings()
    callbacks = callbacks or AgentCallbacks()

    class _Assistant(AutoSubscribeAgent):
        def __init__(self) -> None:
            super().__init__(job_context)
            self._current_task: Optional[asyncio.Task[None]] = None

        async def _speak(self, text: str) -> None:
            await callbacks.on_speech(text)
            audio_base64 = await synthesize_speech(settings=settings, text=text)
            pcm_data = rtc.AudioFrame.from_base64(audio_base64)
            await self.publish_audio_frame(pcm_data)

        async def _cancel_pending(self) -> None:
            if self._current_task and not self._current_task.done():
                self._current_task.cancel()
                try:
                    await self._current_task
                except asyncio.CancelledError:
                    logger.debug("Cancelled pending TTS playback")

        async def on_track_subscribed(
            self,
            track: rtc.AudioTrack,
            publication: rtc.RemoteTrackPublication,
            participant: rtc.RemoteParticipant,
        ) -> None:
            # Called every time the remote participant sends us audio.
            del publication, participant  # Unused but keep signature stable

            async def _process() -> None:
                await callbacks.on_thinking("listening")
                audio_chunk = await track.to_base64()
                transcript = await transcribe_audio(
                    settings=settings, audio_base64=audio_chunk
                )
                await callbacks.on_transcription(transcript)

                # Query Dify for the next assistant turn.
                response = await generate_reply(
                    settings=settings,
                    messages=[
                        Message(role="user", content=transcript),
                    ],
                )
                await callbacks.on_thinking("responding")
                await self._speak(response["reply"])

            await self._cancel_pending()
            self._current_task = asyncio.create_task(_process())

    assistant = _Assistant()
    await assistant.run()


__all__ = ["run_agent", "AgentCallbacks", "LiveKitDependencyError"]
