"""Application configuration helpers.

This module exposes ``Settings`` which reads environment variables for
connecting to Alibaba Bailian (for speech-to-text and text-to-speech), the local
Dify instance, and LiveKit.  The settings are shared across the FastAPI app and
agent background workers.

The module is intentionally dependency-free so that the unit tests can stub the
configuration without relying on a real environment.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Optional

from pydantic import BaseSettings, Field, HttpUrl


class Settings(BaseSettings):
    """Centralised configuration pulled from environment variables.

    The defaults are intentionally verbose so that developers immediately know
    which environment variables need to be set for a production deployment.  In
    unit tests we override the values explicitly.
    """

    # Alibaba Bailian credentials for speech services
    ali_app_key: str = Field(
        "", description="Alibaba Bailian application key used for STT/TTS"
    )
    ali_access_token: str = Field(
        "", description="Temporary access token for calling Bailian APIs"
    )
    ali_api_base: HttpUrl = Field(
        "https://dashscope.aliyuncs.com/api/v1/",
        description="Base URL for the Bailian speech APIs",
    )

    # Dify LLM configuration
    dify_api_base: HttpUrl = Field(
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
    livekit_host: HttpUrl = Field(
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
    """Return a cached instance of :class:`Settings`.

    The cache keeps FastAPI dependency injection inexpensive, even when the
    configuration is requested for every incoming request.
    """

    return Settings()


__all__ = ["Settings", "get_settings"]
