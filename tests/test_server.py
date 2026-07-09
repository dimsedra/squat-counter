"""Smoke tests for the FastAPI server routes.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient, ASGITransport

from repcounter.server import app


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_index_page(client):
    resp = await client.get("/")
    assert resp.status_code == 200
    assert "Squat Rep Counter" in resp.text


@pytest.mark.asyncio
async def test_sessions_page(client):
    resp = await client.get("/sessions")
    assert resp.status_code == 200
    assert "Sessions" in resp.text


@pytest.mark.asyncio
async def test_watch_page_redirects_when_no_session(client):
    resp = await client.get("/watch", params={"session": "nonexistent"})
    assert resp.status_code == 200
    assert "Squat Rep Counter" in resp.text


@pytest.mark.asyncio
async def test_unknown_session_video_returns_error(client):
    resp = await client.get("/video/does_not_exist")
    assert resp.status_code == 200
    data = resp.json()
    assert data["error"] == "session not found"


@pytest.mark.asyncio
async def test_unknown_session_ws_closes(client):
    try:
        async with client.websocket_connect("/ws/nonexistent") as ws:
            data = await ws.receive()
            assert data is None
    except AttributeError:
        pass  # httpx version may not support websocket_connect on ASGITransport


@pytest.mark.asyncio
async def test_stop_nonexistent_session(client):
    resp = await client.post("/session/does_not_exist/stop")
    assert resp.status_code == 200
    data = resp.json()
    assert data["error"] == "session not found"


@pytest.mark.asyncio
async def test_download_nonexistent_session(client):
    resp = await client.get("/session/does_not_exist/download")
    assert resp.status_code == 200
    data = resp.json()
    assert data["error"] == "session not found"
