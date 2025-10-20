"""FastAPI application exposing REST endpoints used by the web client."""
from __future__ import annotations

import base64
import logging
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import Settings, get_settings
from .schemas import (
    ChatRequest,
    ChatResponse,
    STTRequest,
    STTResponse,
    TTSRequest,
    TTSResponse,
    TokenRequest,
    TokenResponse,
)
from .services.ali_bailian import BailianError, synthesize_speech, transcribe_audio
from .services.dify import generate_reply

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="LiveKit Voice Assistant for Dify", version="1.0.0")


@app.on_event("startup")
def _startup_banner() -> None:
    settings = get_settings()
    logger.info("FastAPI application started with Dify base %s", settings.dify_api_base)


@app.on_event("shutdown")
def _shutdown_banner() -> None:
    logger.info("FastAPI application shutting down")


SettingsDep = Annotated[Settings, Depends(get_settings)]


_origins = [
    origin.strip()
    for origin in get_settings().allow_origins.split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", summary="Health check")
async def health(settings: SettingsDep) -> JSONResponse:
    """Simple health check used by the readiness probe."""

    return JSONResponse({
        "status": "ok",
        "dify": str(settings.dify_api_base),
        "livekit": str(settings.livekit_host),
    })


@app.post("/chat", response_model=ChatResponse, summary="Send conversation to Dify")
async def chat(request: ChatRequest, settings: SettingsDep) -> ChatResponse:
    result = await generate_reply(settings=settings, messages=request.messages)
    return ChatResponse(**result)


@app.post("/speech-to-text", response_model=STTResponse, summary="Convert audio to text")
async def speech_to_text(request: STTRequest, settings: SettingsDep) -> STTResponse:
    try:
        text = await transcribe_audio(
            settings=settings,
            audio_base64=request.audio_base64,
            audio_format=request.format,
            sample_rate=request.sample_rate,
        )
    except BailianError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return STTResponse(text=text)


@app.post("/text-to-speech", response_model=TTSResponse, summary="Convert text to audio")
async def text_to_speech(request: TTSRequest, settings: SettingsDep) -> TTSResponse:
    try:
        audio_base64 = await synthesize_speech(
            settings=settings,
            text=request.text,
            voice=request.voice,
            audio_format=request.format,
        )
    except BailianError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # The frontend expects a valid base64 string.  Perform a quick sanity check to
    # avoid propagating backend errors to the browser where they would be harder
    # to debug.
    try:
        base64.b64decode(audio_base64.encode(), validate=True)
    except Exception as exc:  # pragma: no cover - defensive guard
        raise HTTPException(status_code=500, detail="Invalid audio payload returned by TTS") from exc

    return TTSResponse(audio_base64=audio_base64)


@app.post("/livekit/token", response_model=TokenResponse, summary="Create LiveKit access token")
async def livekit_token(request: TokenRequest, settings: SettingsDep) -> TokenResponse:
    try:
        from livekit import rtc
    except Exception as exc:  # pragma: no cover - optional dependency
        raise HTTPException(
            status_code=500,
            detail="LiveKit Python SDK is not installed. Install 'livekit' to enable token generation.",
        ) from exc

    grant = rtc.VideoGrant(room=request.room, room_join=True, can_publish=True, can_subscribe=True)
    token = rtc.AccessToken(settings.livekit_api_key, settings.livekit_api_secret)
    token.add_grant(grant)
    token.identity = request.identity
    jwt = token.to_jwt()
    return TokenResponse(token=jwt)


# Serve the static frontend assets.  They live in ``frontend`` at the project root.
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")


__all__ = ["app"]
