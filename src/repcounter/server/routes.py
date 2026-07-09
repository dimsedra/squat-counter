"""HTTP + WebSocket routes for the web dashboard.
"""
from __future__ import annotations

import asyncio
import json
import threading
from pathlib import Path

from fastapi import APIRouter, File, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse
from starlette.requests import Request

from repcounter.capture import VideoFileCapture, WebcamCapture
from repcounter.server.pipeline import FrameData, PipelineState, run_pipeline
from repcounter.server.session import SessionRecorder, SESSIONS_DIR
from repcounter.server.templates import render_index, render_sessions, render_watch

router = APIRouter()

MODEL_PATH = Path(__file__).resolve().parent.parent.parent.parent / "models" / "pose_landmarker_full.task"

# In-memory session store: session_id -> PipelineState
_sessions: dict[str, PipelineState] = {}

# Global webcam session (singleton: one webcam at a time)
_webcam_state: PipelineState | None = None
_webcam_lock = threading.Lock()


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
        if not MODEL_PATH.exists():
            return HTMLResponse("Model not found. Run scripts/fetch_model.py first.", status_code=500)
        global _webcam_state
        with _webcam_lock:
            if _webcam_state and _webcam_state.running:
                _webcam_state.running = False
            rec = SessionRecorder(label="webcam_live", source="webcam")
            cap = WebcamCapture(0)
            session_id, state = _start_pipeline(cap, session=rec)
            _webcam_state = state
            _sessions[session_id] = state
        return render_watch(session_id, source="webcam")

    if session and session in _sessions:
        return render_watch(session, source="recorded")

    return render_index()


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


@router.post("/session/{session_id}/stop")
async def stop_session(session_id: str):
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
async def download_session(session_id: str, fmt: str = "csv"):
    d = None
    state = _sessions.get(session_id)
    if state and state.session:
        d = state.session.dir
    else:
        candidate = SESSIONS_DIR / session_id
        if candidate.exists():
            d = candidate
    if not d:
        return {"error": "session not found"}

    if fmt == "json":
        p = d / "summary.json"
    else:
        p = d / "frames.csv"
    if not p.exists():
        return {"error": "file not found"}
    return FileResponse(str(p), filename=p.name)
