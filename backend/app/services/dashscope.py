"""DashScope (Model Studio) speech helpers.

This module exposes lightweight async wrappers around the DashScope real-time
speech recognition WebSocket and CosyVoice text-to-speech HTTP endpoints.  The
functions are deliberately self-contained so that unit tests can monkeypatch the
network layer without depending on third-party SDKs.
"""
from __future__ import annotations

import asyncio
import base64
import json
from typing import Dict, List, Optional

import httpx
import websockets
from websockets.exceptions import WebSocketException

from ..config import Settings

STT_WS_URL = "wss://dashscope.aliyuncs.com/api-ws/v1/inference"
TTS_ENDPOINT = "services/audio/v1/tts"


class DashScopeError(RuntimeError):
    """Raised whenever the DashScope speech APIs report an error."""


def _auth_headers(settings: Settings) -> Dict[str, str]:
    """Return the shared authorization headers for DashScope requests."""

    if not settings.dashscope_api_key:
        raise DashScopeError("DashScope API key is not configured")
    return {
        "Authorization": f"bearer {settings.dashscope_api_key}",
        "Content-Type": "application/json",
    }


async def _collect_ws_transcript(ws) -> str:
    """Consume messages from the DashScope recognition stream."""

    fragments: List[str] = []
    try:
        async for message in ws:
            data = json.loads(message)
            output = data.get("output") or {}
            if isinstance(output, dict) and "text" in output:
                fragments.append(output["text"])
            if data.get("status") in {"completed", "finished"} or data.get("type") in {
                "completed",
                "result",
                "finish",
            }:
                break
    except WebSocketException as exc:  # pragma: no cover - network failure guard
        raise DashScopeError("WebSocket error while receiving transcription") from exc

    if not fragments:
        raise DashScopeError("DashScope STT returned no transcription")
    return "".join(fragments).strip()


async def transcribe_audio(
    *,
    settings: Settings,
    audio_base64: str,
    audio_format: str = "pcm",
    sample_rate: int = 16000,
    language: str = "zh-CN",
    timeout: Optional[float] = 30.0,
) -> str:
    """Send audio to DashScope real-time STT and return the transcript."""

    payload = {
        "model": settings.dashscope_stt_model,
        "input": {
            "format": audio_format,
            "sample_rate": sample_rate,
            "encoding": "base64",
            "language": language,
        },
    }

    try:
        base64.b64decode(audio_base64)
    except Exception as exc:  # pragma: no cover - defensive check
        raise DashScopeError("Audio must be base64 encoded") from exc

    headers = {"Authorization": f"bearer {settings.dashscope_api_key}"}
    try:
        async with websockets.connect(
            STT_WS_URL,
            extra_headers=headers,
            ping_interval=None,
            open_timeout=timeout,
        ) as ws:
            await ws.send(json.dumps({"type": "start", **payload}))
            await ws.send(
                json.dumps({"type": "audio", "format": audio_format, "data": audio_base64})
            )
            await ws.send(json.dumps({"type": "end"}))
            transcript = await asyncio.wait_for(_collect_ws_transcript(ws), timeout=timeout)
    except asyncio.TimeoutError as exc:
        raise DashScopeError("DashScope STT timed out") from exc
    except WebSocketException as exc:
        raise DashScopeError("Failed to establish DashScope STT WebSocket") from exc

    return transcript


async def synthesize_speech(
    *,
    settings: Settings,
    text: str,
    voice: Optional[str] = None,
    audio_format: str = "mp3",
    timeout: Optional[float] = 30.0,
) -> str:
    """Convert text to speech using CosyVoice via DashScope HTTP."""

    params_voice = voice or settings.dashscope_default_voice
    payload = {
        "model": settings.dashscope_tts_model,
        "input": {
            "text": text,
        },
        "parameters": {
            "format": audio_format,
        },
    }
    if params_voice:
        payload["parameters"]["voice"] = params_voice

    headers = _auth_headers(settings)
    async with httpx.AsyncClient(base_url=str(settings.dashscope_api_base)) as client:
        response = await client.post(
            TTS_ENDPOINT,
            content=json.dumps(payload),
            headers=headers,
            timeout=timeout,
        )
        data = response.json()

    if response.status_code != 200:
        message = data.get("message") if isinstance(data, dict) else "Unknown error"
        raise DashScopeError(f"DashScope TTS error: {message}")

    try:
        audio_data = data["output"]["audio"]["data"]
    except (TypeError, KeyError) as exc:  # pragma: no cover - defensive branch
        raise DashScopeError("Malformed DashScope TTS response") from exc

    if not isinstance(audio_data, str):
        audio_data = base64.b64encode(audio_data).decode()

    return audio_data


__all__ = ["transcribe_audio", "synthesize_speech", "DashScopeError"]
