"""Web dashboard server (FastAPI) — M6.

Provides real-time squat monitoring via MJPEG stream + WebSocket,
plus session recording for research auditability.

Usage::

    uvicorn repcounter.server:app --reload
    # or
    python scripts/serve.py
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from repcounter.server.routes import router

app = FastAPI(title="Squat Rep Counter", version="0.2.0")
app.include_router(router)

# Self-hosted MediaPipe JS/WASM assets for the browser-webcam path (ADR-0008).
_STATIC_DIR = Path(__file__).resolve().parent / "static"
if _STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")

__all__ = ["app"]
