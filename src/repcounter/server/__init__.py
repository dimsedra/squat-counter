"""Web dashboard server (FastAPI) — M6.

Provides real-time squat monitoring via MJPEG stream + WebSocket,
plus session recording for research auditability.

Usage::

    uvicorn repcounter.server:app --reload
    # or
    python scripts/serve.py
"""
from __future__ import annotations

from fastapi import FastAPI

from repcounter.server.routes import router

app = FastAPI(title="Squat Rep Counter", version="0.2.0")
app.include_router(router)

__all__ = ["app"]
