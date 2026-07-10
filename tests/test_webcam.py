"""Tests for the browser-webcam landmark-processing seam (ADR-0008).

The browser runs MediaPipe and sends landmarks; the server reconstructs a
PoseFrame and reuses FeatureExtractor -> RepCounter -> SessionRecorder. These
tests exercise that seam without any browser or WebSocket.
"""
from __future__ import annotations

import json
import math
import shutil

import pytest

from repcounter.server.session import SESSIONS_DIR, SessionRecorder
from repcounter.server.webcam import WebcamSession, process_landmarks


def _leg(hip, knee, angle_deg, vis, idx_hip, idx_knee, idx_ankle, out):
    ux, uy = hip[0] - knee[0], hip[1] - knee[1]
    th = math.radians(angle_deg)
    vx = ux * math.cos(th) - uy * math.sin(th)
    vy = ux * math.sin(th) + uy * math.cos(th)
    ankle = (knee[0] + vx, knee[1] + vy)
    out[idx_hip] = {"x": hip[0], "y": hip[1], "z": 0.0, "visibility": vis}
    out[idx_knee] = {"x": knee[0], "y": knee[1], "z": 0.0, "visibility": vis}
    out[idx_ankle] = {"x": ankle[0], "y": ankle[1], "z": 0.0, "visibility": vis}


def _msg(angle_deg, *, t=0.0, vis=1.0):
    """Build a browser landmark message for a symmetric squat at *angle_deg*."""
    lms = [{"x": 0.0, "y": 0.0, "z": 0.0, "visibility": 0.0} for _ in range(33)]
    _leg((0.5, 0.2), (0.5, 0.5), angle_deg, vis, 23, 25, 27, lms)
    _leg((0.5, 0.2), (0.5, 0.5), angle_deg, vis, 24, 26, 28, lms)
    return {"t": t, "landmarks": lms}


def _empty_msg(t=0.0):
    return {"t": t, "landmarks": []}


@pytest.fixture
def session(tmp_path):
    rec = SessionRecorder(label="test_webcam", source="webcam")
    rec.start()
    sess = WebcamSession(rec)
    yield sess
    rec.stop()
    shutil.rmtree(rec.dir, ignore_errors=True)


def test_process_returns_expected_shape(session):
    out = process_landmarks(session, _msg(170.0, t=0.0))
    for key in ("angle", "visibility", "rep_count", "rep_state",
                "paused", "partial", "lost_track", "uncalibrated", "fps"):
        assert key in out


def test_counts_one_full_rep(session):
    # A squat cycle: stand -> descend -> bottom -> ascend -> stand.
    angles = [170, 170, 170, 170, 170, 120, 80, 80, 120, 170, 170]
    last = None
    for i, a in enumerate(angles):
        last = process_landmarks(session, _msg(a, t=float(i)))
    assert last["rep_count"] == 1


def test_no_landmarks_reports_lost_track(session):
    out = process_landmarks(session, _empty_msg(t=0.0))
    assert out["lost_track"] is True


def test_frames_written_to_csv(session):
    for i, a in enumerate([170, 120, 80, 120, 170]):
        process_landmarks(session, _msg(a, t=float(i)))
    frames_csv = session.recorder.dir / "frames.csv"
    assert frames_csv.exists()
    lines = frames_csv.read_text().strip().splitlines()
    # header + 5 data rows
    assert len(lines) == 6


def test_rep_event_written_to_events_csv(session):
    # 5 leading standing frames satisfy RepCounter auto-calibration.
    for i, a in enumerate([170, 170, 170, 170, 170, 120, 80, 80, 120, 170, 170]):
        process_landmarks(session, _msg(a, t=float(i)))
    events_csv = session.recorder.dir / "events.csv"
    lines = events_csv.read_text().strip().splitlines()
    assert len(lines) >= 2  # header + >=1 event


def test_summary_records_fps_and_calibration(session):
    for i, a in enumerate([170, 170, 170, 170, 170, 170, 120, 80, 120, 170]):
        process_landmarks(session, _msg(a, t=float(i)))
    session.recorder.stop()
    summary = json.loads((session.recorder.dir / "summary.json").read_text())
    assert summary["fps"] > 0
    assert summary["calibration_angle"] is not None


# ── Input validation (H1) ──────────────────────────────────────────────

def test_non_numeric_coordinate_raises(session):
    bad = {"t": 0.0, "landmarks": [{"x": "oops", "y": 0.1, "visibility": 1.0}]}
    with pytest.raises(ValueError):
        process_landmarks(session, bad)


def test_non_numeric_timestamp_raises(session):
    with pytest.raises(ValueError):
        process_landmarks(session, {"t": None, "landmarks": []})


def test_oversized_landmark_array_raises(session):
    huge = {"t": 0.0, "landmarks": [{"x": 0.0, "y": 0.0, "visibility": 1.0}] * 34}
    with pytest.raises(ValueError):
        process_landmarks(session, huge)


def test_landmarks_not_a_list_raises(session):
    with pytest.raises(ValueError):
        process_landmarks(session, {"t": 0.0, "landmarks": {"x": 0.0}})


# ── WebSocket handler + session lifecycle ──────────────────────────────

def test_webcam_ws_counts_and_finalises():
    from fastapi.testclient import TestClient

    from repcounter.server import app, routes

    sid = "wswebcamtest1"
    client = TestClient(app)
    try:
        with client.websocket_connect(f"/ws/webcam/{sid}") as ws:
            angles = [170, 170, 170, 170, 170, 120, 80, 80, 120, 170, 170]
            last = None
            for i, a in enumerate(angles):
                ws.send_json(_msg(a, t=float(i)))
                last = ws.receive_json()
                assert "rep_count" in last
            assert last["rep_count"] == 1
            ws.send_json({"stop": True})
            final = ws.receive_json()
            assert final["complete"] is True
        # Session removed from the registry after an explicit stop (no leak).
        assert sid not in routes._webcam_sessions
    finally:
        shutil.rmtree(SESSIONS_DIR / sid, ignore_errors=True)


def test_webcam_ws_rejects_malformed_without_closing():
    from fastapi.testclient import TestClient

    from repcounter.server import app

    sid = "wsmalformed1"
    client = TestClient(app)
    try:
        with client.websocket_connect(f"/ws/webcam/{sid}") as ws:
            ws.send_json({"t": 0.0, "landmarks": [{"x": "bad", "y": 0.0}]})
            resp = ws.receive_json()
            assert "error" in resp
            # Connection still alive: a valid frame still gets a normal reply.
            ws.send_json(_msg(170.0, t=1.0))
            ok = ws.receive_json()
            assert "rep_count" in ok
            ws.send_json({"stop": True})
            ws.receive_json()
    finally:
        shutil.rmtree(SESSIONS_DIR / sid, ignore_errors=True)
