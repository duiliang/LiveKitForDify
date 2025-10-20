"""Application configuration helpers."""
from __future__ import annotations

from functools import lru_cache
from typing import Optional

from pydantic import AnyHttpUrl, BaseSettings, Field


class Settings(BaseSettings):
    """Centralised configuration pulled from environment variables."""

    # DashScope credentials for speech services
    dashscope_api_key: str = Field(
        "", description="DashScope API key used for STT/TTS calls"
    )
    dashscope_api_base: AnyHttpUrl = Field(
        "https://dashscope.aliyuncs.com/api/v1/",
        description="Base URL for DashScope HTTP APIs",
    )
    dashscope_stt_model: str = Field(
        "paraformer-realtime-v2",
        description="DashScope real-time recognition model name",
    )
    dashscope_tts_model: str = Field(
        "cosyvoice-v2",
        description="DashScope CosyVoice model used for synthesis",
    )
    dashscope_default_voice: Optional[str] = Field(
        None,
        description="Optional default CosyVoice speaker identifier (e.g. longxiaochun_v2)",
    )

    # Dify LLM configuration
    dify_api_base: AnyHttpUrl = Field(
        "http://localhost:8000/v1/",
        description="Base URL of the self-hosted Dify API gateway",
    )
    dify_api_key: str = Field(
        "", description="API key issued by the local Dify deployment"
    )
    dify_app_id: Optional[str] = Field(
        None,
        description=(
            "Optional Dify app identifier. If supplied we will include it as an"
            " X-Dify-App header so that the correct workflow is triggered."
        ),
    )

    # LiveKit configuration for WebRTC rooms
    livekit_api_key: str = Field("", description="LiveKit API key")
    livekit_api_secret: str = Field("", description="LiveKit API secret")
    livekit_host: AnyHttpUrl = Field(
        "https://livekit.example.com",
        description="URL of the LiveKit server that brokers WebRTC connections",
    )

    # Miscellaneous
    allow_origins: str = Field(
        "*",
        description="Comma separated list of origins allowed to call the API",
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Return a cached instance of :class:`Settings`."""

    return Settings()


__all__ = ["Settings", "get_settings"]
