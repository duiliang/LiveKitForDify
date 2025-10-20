import base64

import pytest
import respx
from httpx import ASGITransport, AsyncClient, Response

from backend.app.config import Settings
from backend.app.main import app


class TestSettings(Settings):
    ali_app_key: str = "demo-app"
    ali_access_token: str = "demo-token"
    ali_api_base: str = "https://dashscope.test/api/v1/"
    dify_api_base: str = "http://dify.local/v1/"
    dify_api_key: str = "dify-key"
    livekit_api_key: str = "lk-key"
    livekit_api_secret: str = "lk-secret"
    livekit_host: str = "https://livekit.local"
    allow_origins: str = "http://localhost"


@pytest.fixture(autouse=True)
def override_settings(monkeypatch):
    from backend.app import main as main_module

    settings = TestSettings()
    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    app.dependency_overrides[main_module.get_settings] = lambda: settings
    yield
    app.dependency_overrides.clear()


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest.mark.asyncio
async def test_health_endpoint(client):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["dify"].startswith("http://dify.local")


@pytest.mark.asyncio
async def test_chat_endpoint(client):
    with respx.mock(assert_all_called=True) as router:
        router.post("http://dify.local/v1/chat-messages").mock(
            return_value=Response(200, json={"answer": "你好，我是助手"})
        )
        payload = {
            "messages": [
                {"role": "user", "content": "你好"},
            ]
        }
        response = await client.post("/chat", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["reply"].startswith("你好")
    assert isinstance(body["latency_ms"], int)


@pytest.mark.asyncio
async def test_speech_to_text_endpoint(client):
    with respx.mock(assert_all_called=True) as router:
        router.post("https://dashscope.test/api/v1/services/audio/dashscope/speech_to_text").mock(
            return_value=Response(200, json={"output": {"text": "测试文本"}})
        )
        payload = {
            "audio_base64": base64.b64encode(b"demo").decode(),
            "format": "pcm",
            "sample_rate": 16000,
        }
        response = await client.post("/speech-to-text", json=payload)

    assert response.status_code == 200
    assert response.json() == {"text": "测试文本"}


@pytest.mark.asyncio
async def test_text_to_speech_endpoint(client):
    fake_audio = base64.b64encode(b"audio").decode()
    with respx.mock(assert_all_called=True) as router:
        router.post("https://dashscope.test/api/v1/services/audio/dashscope/text_to_speech").mock(
            return_value=Response(200, json={"output": {"audio": {"data": fake_audio}}})
        )
        payload = {"text": "你好", "format": "mp3"}
        response = await client.post("/text-to-speech", json=payload)

    assert response.status_code == 200
    assert response.json()["audio_base64"] == fake_audio


@pytest.mark.asyncio
async def test_livekit_token_missing_dependency(client, monkeypatch):
    import builtins

    original_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name.startswith("livekit"):
            raise ImportError("livekit unavailable")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    payload = {"identity": "tester", "room": "demo"}
    response = await client.post("/livekit/token", json=payload)
    assert response.status_code == 500
    assert "LiveKit Python SDK" in response.json()["detail"]


@pytest.mark.asyncio
async def test_voice_agent_dependency_error():
    from backend.app.services.voice_agent import (
        LiveKitDependencyError,
        _ensure_livekit_modules,
    )

    with pytest.raises(LiveKitDependencyError):
        await _ensure_livekit_modules()
