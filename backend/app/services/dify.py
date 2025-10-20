"""Helper for interacting with a self-hosted Dify deployment."""
from __future__ import annotations

import json
import time
from typing import Any, Dict, Iterable, Optional

import httpx

from ..config import Settings
from ..schemas import Message

CHAT_COMPLETIONS_ENDPOINT = "chat-messages"


def _build_headers(settings: Settings) -> Dict[str, str]:
    headers = {
        "Authorization": f"Bearer {settings.dify_api_key}",
        "Content-Type": "application/json",
    }
    if settings.dify_app_id:
        headers["X-Dify-App"] = settings.dify_app_id
    return headers


async def generate_reply(
    *,
    settings: Settings,
    messages: Iterable[Message],
    timeout: Optional[float] = 30.0,
) -> Dict[str, Any]:
    """Send the conversation to Dify and return the response payload.

    The function returns both the generated text and metadata such as latency so
    the HTTP API can report progress back to the browser.
    """

    payload: Dict[str, Any] = {
        "inputs": {},
        "response_mode": "blocking",
        "query": messages[-1].content if messages else "",
        "user": "livekit-web-assistant",
        "conversation_id": None,
        "messages": [message.dict() for message in messages],
    }

    start = time.monotonic()
    async with httpx.AsyncClient(base_url=str(settings.dify_api_base)) as client:
        response = await client.post(
            CHAT_COMPLETIONS_ENDPOINT,
            content=json.dumps(payload),
            headers=_build_headers(settings),
            timeout=timeout,
        )
        latency = int((time.monotonic() - start) * 1000)
        response.raise_for_status()
        data = response.json()

    return {"reply": data.get("answer", ""), "latency_ms": latency}


__all__ = ["generate_reply"]
