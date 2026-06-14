from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from headroom.server import app


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_health_endpoint(client):
    async with client as ac:
        response = await ac.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_chat_completion_no_messages(client):
    async with client as ac:
        with patch("headroom.server.proxy.forward_request", new_callable=AsyncMock) as mock_forward:
            mock_forward.return_value = {"id": "cmpl-test", "choices": []}
            response = await ac.post(
                "/v1/chat/completions",
                json={"model": "gpt-4"},
            )
    assert response.status_code == 200
    data = response.json()
    assert "_headroom" in data


@pytest.mark.asyncio
async def test_chat_completion_compresses_prompt(client):
    async with client as ac:
        with patch("headroom.server.proxy.forward_request", new_callable=AsyncMock) as mock_forward:
            mock_forward.return_value = {
                "id": "cmpl-test",
                "choices": [{"message": {"content": "response"}}],
            }
            response = await ac.post(
                "/v1/chat/completions",
                json={
                    "model": "gpt-4",
                    "messages": [
                        {
                            "role": "user",
                            "content": "As an AI language model, I must help you.\nKeep this line.",
                        }
                    ],
                },
            )
    assert response.status_code == 200
    data = response.json()
    headroom = data["_headroom"]
    assert headroom["original_chars"] > headroom["compressed_chars"]
    assert headroom["parse_overhead_ms"] < 15


@pytest.mark.asyncio
async def test_upstream_error_returns_502(client):
    async with client as ac:
        with patch("headroom.server.proxy.forward_request", new_callable=AsyncMock) as mock_forward:
            mock_forward.side_effect = Exception("Upstream timeout")
            response = await ac.post(
                "/v1/chat/completions",
                json={"model": "gpt-4", "messages": [{"role": "user", "content": "hi"}]},
            )
    assert response.status_code == 502
    assert "Upstream request failed" in response.json()["error"]
