import base64

import pytest
import pytest_asyncio
import respx
from httpx import ASGITransport, AsyncClient, Response

from backend.app.config import Settings
from backend.app.main import app


@pytest.fixture(autouse=True)
def override_settings(monkeypatch):
    from backend.app import main as main_module
    from backend.app.config import get_settings as config_get_settings

    settings = Settings(
        dashscope_api_key="dashscope-test-key",
        dashscope_api_base="https://dashscope.example/api/v1/",
        dashscope_default_voice="longxiaochun_v2",
        dify_api_base="http://dify.example/v1/",
        dify_api_key="dify-key",
        livekit_api_key="lk-key",
        livekit_api_secret="lk-secret",
        livekit_host="https://livekit.example.com",
        allow_origins="http://localhost",
    )
    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr("backend.app.config.get_settings", lambda: settings)
    app.dependency_overrides[config_get_settings] = lambda: settings
    app.dependency_overrides[main_module.get_settings] = lambda: settings
    yield
    app.dependency_overrides.clear()


# Async fixtures require pytest-asyncio helpers when running in strict mode.
@pytest_asyncio.fixture
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
    assert data["dify"].startswith("http://dify.example")


@pytest.mark.asyncio
async def test_chat_endpoint(client):
    with respx.mock(assert_all_called=True) as router:
        router.post("http://dify.example/v1/chat-messages").mock(
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
async def test_speech_to_text_endpoint(client, monkeypatch):
    async def fake_transcribe_audio(**kwargs):
        assert kwargs["audio_base64"]
        return "测试文本"

    monkeypatch.setattr("backend.app.main.transcribe_audio", fake_transcribe_audio)

    payload = {
        "audio_base64": base64.b64encode(b"demo").decode(),
        "format": "pcm",
        "sample_rate": 16000,
    }
    response = await client.post("/speech-to-text", json=payload)

    assert response.status_code == 200
    assert response.json() == {"text": "测试文本"}


@pytest.mark.asyncio
async def test_text_to_speech_endpoint(client, monkeypatch):
    fake_audio = base64.b64encode(b"audio").decode()

    async def fake_synthesize_speech(**kwargs):
        assert kwargs["text"] == "你好"
        return fake_audio

    monkeypatch.setattr("backend.app.main.synthesize_speech", fake_synthesize_speech)

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
