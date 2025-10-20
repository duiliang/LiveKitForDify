"""Pydantic schemas used by the HTTP API."""
from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class Message(BaseModel):
    """Represents a single chat message in a conversation."""

    role: Literal["user", "assistant", "system"]
    content: str = Field(..., description="Plain text content of the message")


class ChatRequest(BaseModel):
    """Payload sent by the client when requesting a new LLM turn."""

    messages: List[Message] = Field(
        ..., description="Conversation history to send to the Dify LLM"
    )


class ChatResponse(BaseModel):
    """Response wrapper containing the generated assistant text."""

    reply: str = Field(..., description="Assistant response returned by Dify")
    latency_ms: int = Field(
        ..., description="Measured round-trip time from the Dify API in ms"
    )


class STTRequest(BaseModel):
    """Metadata describing an uploaded audio buffer for transcription."""

    audio_base64: str = Field(
        ..., description="Base64 encoded audio (16kHz PCM) recorded by the browser"
    )
    format: str = Field(
        "pcm", description="Audio container format supported by DashScope STT"
    )
    sample_rate: int = Field(
        16000,
        description="Sampling rate of the audio buffer. DashScope expects 16kHz by default",
    )


class STTResponse(BaseModel):
    text: str = Field(..., description="Transcribed text")


class TTSRequest(BaseModel):
    text: str = Field(..., description="Assistant reply that should be spoken")
    voice: Optional[str] = Field(
        None,
        description="Optional DashScope CosyVoice speaker identifier for synthesis",
    )
    format: str = Field(
        "mp3", description="Desired audio format for the synthesized speech"
    )


class TTSResponse(BaseModel):
    audio_base64: str = Field(..., description="Base64 encoded synthesized audio")


class TokenRequest(BaseModel):
    """Request body for creating LiveKit access tokens."""

    identity: str = Field(..., description="Unique identifier for the connecting user")
    room: str = Field(..., description="LiveKit room name")


class TokenResponse(BaseModel):
    token: str = Field(..., description="JWT token allowing the browser to join LiveKit")


__all__ = [
    "Message",
    "ChatRequest",
    "ChatResponse",
    "STTRequest",
    "STTResponse",
    "TTSRequest",
    "TTSResponse",
    "TokenRequest",
    "TokenResponse",
]
