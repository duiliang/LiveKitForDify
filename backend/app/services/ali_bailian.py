"""Client wrappers around Alibaba Bailian speech APIs.

The actual Bailian APIs are HTTP endpoints that accept JSON payloads.  For the
sake of unit testing we perform all HTTP operations via :mod:`httpx`.  The
functions exposed here accept the already base64 encoded audio buffers and
return either the transcribed text or base64 audio depending on direction.
"""
from __future__ import annotations

import base64
import json
from typing import Any, Dict, Optional

import httpx

from ..config import Settings

STT_ENDPOINT = "services/audio/dashscope/speech_to_text"
TTS_ENDPOINT = "services/audio/dashscope/text_to_speech"


class BailianError(RuntimeError):
    """Raised whenever the Bailian API reports an error."""


def _build_headers(settings: Settings) -> Dict[str, str]:
    """Return HTTP headers required by Bailian.

    The Bailian APIs expect both the app key and an access token.  The token is
    usually short lived; refreshing it is outside the scope of this example but
    the interface keeps it explicit so a scheduled job can update it.
    """

    return {
        "X-DashScope-App-Key": settings.ali_app_key,
        "Authorization": f"Bearer {settings.ali_access_token}",
        "Content-Type": "application/json",
    }


async def transcribe_audio(
    *,
    settings: Settings,
    audio_base64: str,
    audio_format: str = "pcm",
    sample_rate: int = 16000,
    language: str = "zh-CN",
    timeout: Optional[float] = 30.0,
) -> str:
    """Send audio to Bailian STT and return the transcribed text.

    Args:
        settings: Shared settings containing Bailian credentials.
        audio_base64: Audio data encoded in base64.
        audio_format: Format accepted by the API, e.g. ``pcm`` or ``wav``.
        sample_rate: Sample rate in Hz.
        language: Spoken language for the recognition engine.
        timeout: Optional request timeout (seconds).
    """

    payload: Dict[str, Any] = {
        "input": {
            "audio": {
                "format": audio_format,
                "sample_rate": sample_rate,
                "encoding": "base64",
                "data": audio_base64,
            },
            "language": language,
        }
    }

    async with httpx.AsyncClient(base_url=str(settings.ali_api_base)) as client:
        response = await client.post(
            STT_ENDPOINT,
            content=json.dumps(payload),
            headers=_build_headers(settings),
            timeout=timeout,
        )
        data = response.json()

    if response.status_code != 200:
        raise BailianError(data.get("message", "Unknown Bailian STT error"))

    try:
        return data["output"]["text"]
    except KeyError as exc:  # pragma: no cover - defensive branch
        raise BailianError("Malformed Bailian STT response") from exc


async def synthesize_speech(
    *,
    settings: Settings,
    text: str,
    voice: Optional[str] = None,
    audio_format: str = "mp3",
    timeout: Optional[float] = 30.0,
) -> str:
    """Convert text to speech using the Bailian TTS service.

    Returns the resulting audio as a base64 encoded string.
    """

    payload: Dict[str, Any] = {
        "input": {
            "text": text,
            "format": audio_format,
        }
    }

    if voice:
        payload["input"]["voice"] = voice

    async with httpx.AsyncClient(base_url=str(settings.ali_api_base)) as client:
        response = await client.post(
            TTS_ENDPOINT,
            content=json.dumps(payload),
            headers=_build_headers(settings),
            timeout=timeout,
        )
        data = response.json()

    if response.status_code != 200:
        raise BailianError(data.get("message", "Unknown Bailian TTS error"))

    try:
        audio_data = data["output"]["audio"]["data"]
    except KeyError as exc:  # pragma: no cover - defensive branch
        raise BailianError("Malformed Bailian TTS response") from exc

    # Bailian sometimes returns binary audio; normalise the output so the
    # frontend can consume it directly without guessing the format.
    if not isinstance(audio_data, str):
        audio_data = base64.b64encode(audio_data).decode()

    return audio_data


__all__ = ["transcribe_audio", "synthesize_speech", "BailianError"]
