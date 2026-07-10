"""HTTP + WebSocket routes for the web dashboard.
"""
from __future__ import annotations

import asyncio
import json
import threading
import time
import uuid
from pathlib import Path

from fastapi import APIRouter, File, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse
from starlette.requests import Request

from repcounter.capture import VideoFileCapture
from repcounter.server.pipeline import PipelineState, run_pipeline
from repcounter.server.session import SessionRecorder, SESSIONS_DIR
from repcounter.server.templates import (
    render_index, render_sessions, render_watch, render_watch_webcam,
)
from repcounter.server.webcam import WebcamSession, process_landmarks

router = APIRouter()

MODEL_PATH = Path(__file__).resolve().parent.parent.parent.parent / "models" / "pose_landmarker_full.task"

# In-memory session store: session_id -> PipelineState (uploaded-video path)
_sessions: dict[str, PipelineState] = {}

# Browser-webcam sessions: session_id -> WebcamSession (ADR-0008). Created lazily
# on WebSocket connect and removed on explicit stop or by the idle reaper.
_webcam_sessions: dict[str, WebcamSession] = {}

# Reject WS messages larger than this (33*2 landmarks of JSON fit in a few KB).
MAX_WS_MSG_BYTES = 64 * 1024

# Idle-webcam-session reaper: stop + drop sessions with no live connection.
_REAP_IDLE_SEC = 120.0
_REAP_INTERVAL_SEC = 30.0
_reaper_started = False


def _ensure_reaper() -> None:
    """Start the idle-session reaper once, on the running event loop."""
    global _reaper_started
    if _reaper_started:
        return
    _reaper_started = True
    asyncio.create_task(_reaper_loop())


async def _reaper_loop() -> None:
    while True:
        await asyncio.sleep(_REAP_INTERVAL_SEC)
        now = time.monotonic()
        for sid, s in list(_webcam_sessions.items()):
            if s.active_conns <= 0 and now - s.last_activity > _REAP_IDLE_SEC:
                s.recorder.stop()
                _webcam_sessions.pop(sid, None)


def _start_pipeline(capture, session: SessionRecorder | None = None) -> tuple[str, PipelineState]:
    state = PipelineState()
    session_id = session.session_id if session else "webcam"
    if session:
        session.start()

    t = threading.Thread(
        target=run_pipeline,
        args=(capture, str(MODEL_PATH), state),
        kwargs={"session": session},
        daemon=True,
    )
    t.start()
    return session_id, state


# ── Pages ─────────────────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return render_index()


@router.get("/watch", response_class=HTMLResponse)
async def watch(request: Request, session: str | None = None, source: str | None = None):
    if source == "webcam":
        # Live webcam runs MediaPipe in the browser (ADR-0008); the server only
        # counts from landmarks. No server-side camera is opened, and no session
        # is created here — the session is created lazily when the WebSocket
        # connects (avoids leaking recorders for page loads that never stream).
        if not MODEL_PATH.exists():
            return HTMLResponse("Model not found. Run scripts/fetch_model.py first.", status_code=500)
        session_id = uuid.uuid4().hex[:12]
        return render_watch_webcam(session_id)

    if session and session in _sessions:
        return render_watch(session, source="recorded")

    return render_index()


@router.get("/model/pose_landmarker_full.task")
async def model_asset():
    if not MODEL_PATH.exists():
        return {"error": "model not found"}
    return FileResponse(
        str(MODEL_PATH),
        media_type="application/octet-stream",
        filename="pose_landmarker_full.task",
    )


@router.get("/sessions", response_class=HTMLResponse)
async def sessions_page(request: Request):
    entries = []
    if SESSIONS_DIR.exists():
        for d in sorted(SESSIONS_DIR.iterdir(), reverse=True):
            summary_path = d / "summary.json"
            if summary_path.exists():
                data = json.loads(summary_path.read_text())
                entries.append(data)
    return render_sessions(entries)


# ── API ───────────────────────────────────────────────────────────────

@router.post("/upload")
async def upload_video(file: UploadFile = File(...), label: str = ""):
    if not MODEL_PATH.exists():
        return {"error": "Model not found. Run scripts/fetch_model.py first."}

    upload_dir = Path(__file__).resolve().parent.parent.parent.parent / "uploads"
    upload_dir.mkdir(exist_ok=True)
    dst = upload_dir / file.filename
    with dst.open("wb") as f:
        f.write(await file.read())

    cap = VideoFileCapture(str(dst))
    rec = SessionRecorder(label=label or file.filename, source="upload")
    session_id, state = _start_pipeline(cap, session=rec)
    state.upload_path = str(dst)
    _sessions[session_id] = state
    return {"session_id": session_id}


@router.get("/video/{session_id}")
async def video_stream(session_id: str):
    state = _sessions.get(session_id)
    if not state:
        return {"error": "session not found"}

    async def generate():
        while True:
            jpg = await asyncio.to_thread(state.frame_queue.get)
            if jpg is None:
                break
            yield (b"--frame\r\n"
                   b"Content-Type: image/jpeg\r\n\r\n" + jpg + b"\r\n")
    return StreamingResponse(
        generate(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


@router.websocket("/ws/{session_id}")
async def websocket_endpoint(ws: WebSocket, session_id: str):
    state = _sessions.get(session_id)
    if not state:
        await ws.close(code=4004)
        return

    await ws.accept()

    # Already completed — send complete immediately, no reconnect.
    if state.completed:
        s = state.session
        reps = s.summary().get("reps", 0) if s else 0
        dur = s.summary().get("duration_sec", 0) if s else 0
        await ws.send_json({"complete": True, "rep_count": reps, "duration_sec": dur})
        await ws.close()
        return

    # Let the frontend know we are alive and processing.
    await ws.send_json({"status": "processing"})

    try:
        while True:
            data = await asyncio.to_thread(state.data_queue.get)
            if data.complete:
                s = state.session
                reps = s.summary().get("reps", 0) if s else 0
                dur = s.summary().get("duration_sec", 0) if s else 0
                await ws.send_json({
                    "complete": True,
                    "rep_count": reps,
                    "duration_sec": dur,
                })
                break
            await ws.send_json({
                "t": data.timestamp,
                "angle": data.angle,
                "visibility": data.visibility,
                "rep_count": data.rep_count,
                "rep_state": data.rep_state,
                "paused": data.paused,
                "partial": data.partial,
                "lost_track": data.lost_track,
                "uncalibrated": data.uncalibrated,
                "fps": data.fps,
            })
    except WebSocketDisconnect:
        pass


def _complete_payload(sess: WebcamSession) -> dict:
    summary = sess.recorder.summary()
    return {
        "complete": True,
        "rep_count": summary.get("reps", sess.counter.rep_count),
        "duration_sec": summary.get("duration_sec", 0),
    }


@router.websocket("/ws/webcam/{session_id}")
async def webcam_ws(ws: WebSocket, session_id: str):
    """Bidirectional WS for the browser-webcam path (ADR-0008).

    Receives per-frame landmark messages from the browser, drives the counting
    chain, and returns the count/state payload for display. The session is
    created lazily on first connect and reused across reconnects; it is finalised
    on an explicit ``{"stop": true}`` message or by the idle reaper. A transient
    disconnect does NOT stop the session, so the client can reconnect and resume.
    """
    await ws.accept()
    _ensure_reaper()

    sess = _webcam_sessions.get(session_id)
    if sess is None:
        rec = SessionRecorder(label="webcam_live", source="webcam", session_id=session_id)
        rec.start()
        sess = WebcamSession(rec)
        _webcam_sessions[session_id] = sess
    sess.active_conns += 1

    try:
        while True:
            try:
                raw = await ws.receive_text()
            except WebSocketDisconnect:
                break

            if len(raw) > MAX_WS_MSG_BYTES:
                await ws.send_json({"error": "message too large"})
                continue
            try:
                msg = json.loads(raw)
            except (json.JSONDecodeError, ValueError):
                await ws.send_json({"error": "invalid json"})
                continue
            if not isinstance(msg, dict):
                await ws.send_json({"error": "message must be an object"})
                continue

            if msg.get("stop"):
                sess.recorder.stop()
                _webcam_sessions.pop(session_id, None)
                await ws.send_json(_complete_payload(sess))
                break

            try:
                payload = await asyncio.to_thread(process_landmarks, sess, msg)
            except ValueError as exc:
                await ws.send_json({"error": str(exc)})
                continue
            await ws.send_json(payload)
    finally:
        sess.active_conns -= 1


@router.post("/session/{session_id}/stop")
async def stop_session(session_id: str):
    sess = _webcam_sessions.pop(session_id, None)
    if sess:
        out_dir = sess.recorder.stop()
        return {"dir": str(out_dir), "summary": sess.recorder.summary()}

    state = _sessions.get(session_id)
    if not state:
        return {"error": "session not found"}
    state.running = False
    out_dir = None
    if state.session:
        out_dir = state.session.stop()
        return {"dir": str(out_dir), "summary": state.session.summary()}
    return {"ok": True}


@router.get("/session/{session_id}/download")
async def download_session(session_id: str, format: str = "csv"):
    d = None
    state = _sessions.get(session_id)
    sess = _webcam_sessions.get(session_id)
    if state and state.session:
        d = state.session.dir
    elif sess:
        d = sess.recorder.dir
    else:
        candidate = SESSIONS_DIR / session_id
        if candidate.exists():
            d = candidate
    if not d:
        return {"error": "session not found"}

    if format == "json":
        p = d / "summary.json"
    else:
        p = d / "frames.csv"
    if not p.exists():
        return {"error": "file not found"}
    return FileResponse(str(p), filename=p.name)
