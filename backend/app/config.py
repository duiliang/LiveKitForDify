"""Application configuration helpers.

This module exposes ``Settings`` which reads environment variables for
connecting to Alibaba Bailian (for speech-to-text and text-to-speech), the local
Dify instance, and LiveKit.  The settings are shared across the FastAPI app and
agent background workers.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralised configuration pulled from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Alibaba Bailian credentials for speech services
    ali_app_key: str = Field(
        "",
        description="Alibaba Bailian application key used for STT/TTS",
    )
    ali_access_token: str = Field(
        "",
        description="Temporary access token for calling Bailian APIs",
    )
    ali_api_base: str = Field(
        "https://dashscope.aliyuncs.com/api/v1/",
        description="Base URL for the Bailian speech APIs",
    )

    # Dify LLM configuration
    dify_api_base: str = Field(
        "http://localhost:8000/v1/",
        description="Base URL of the self-hosted Dify API gateway",
    )
    dify_api_key: str = Field(
        "",
        description="API key issued by the local Dify deployment",
    )
    dify_app_id: str | None = Field(
        None,
        description=(
            "Optional Dify app identifier. If supplied we will include it as an "
            "X-Dify-App header so that the correct workflow is triggered."
        ),
    )

    # LiveKit configuration for WebRTC rooms
    livekit_api_key: str = Field("", description="LiveKit API key")
    livekit_api_secret: str = Field("", description="LiveKit API secret")
    livekit_host: str = Field(
        "https://livekit.example.com",
        description="URL of the LiveKit server that brokers WebRTC connections",
        validation_alias=AliasChoices("LIVEKIT_HOST", "LIVEKIT_URL"),
    )

    # Miscellaneous
    allow_origins: str = Field(
        "*",
        description="Comma separated list of origins allowed to call the API",
    )


@lru_cache()
def get_settings() -> Settings:
    """Return a cached instance of :class:`Settings`."""

    return Settings()


__all__ = ["Settings", "get_settings"]
