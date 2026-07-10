"""Browser-webcam landmark processing (ADR-0008).

For the live-webcam path, MediaPipe runs in the browser. The browser sends
per-frame landmarks over the WebSocket; this module reconstructs a ``PoseFrame``
and drives the *same* counting chain used by the uploaded-video pipeline
(``FeatureExtractor`` -> ``RepCounter`` -> ``SessionRecorder``), keeping a single
source of truth for rep counting.

``process_landmarks`` is a pure, browser-free seam so counting can be tested
without a WebSocket or a camera. It validates untrusted input and raises
``ValueError`` on malformed messages so the transport layer can respond without
crashing the connection.
"""
from __future__ import annotations

import math
import time
from typing import Any

from repcounter.count import RepCounter
from repcounter.features import FeatureExtractor
from repcounter.server.session import SessionRecorder
from repcounter.types import CountStep, Landmark, PoseFrame

# MediaPipe Pose emits a fixed 33-landmark topology; reject anything larger to
# bound memory and reject obviously malformed input.
MAX_LANDMARKS = 33


class WebcamSession:
    """Per-connection state for a browser-webcam session."""

    def __init__(self, recorder: SessionRecorder) -> None:
        self.recorder = recorder
        self.fe = FeatureExtractor()
        self.counter = RepCounter()
        self.frame_count = 0
        self.active_conns = 0
        self.last_activity = time.monotonic()
        self._t0: float | None = None
        self._calibration_recorded = False


def _coerce_float(value: Any, name: str) -> float:
    """Coerce *value* to a finite float or raise ValueError."""
    try:
        out = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name} is not a number: {value!r}")
    if not math.isfinite(out):
        raise ValueError(f"{name} is not finite: {value!r}")
    return out


def _to_landmarks(raw: Any) -> dict[int, Landmark] | None:
    """Convert a browser landmark array into a ``{idx: Landmark}`` dict.

    Each entry is a MediaPipe NormalizedLandmark-like ``{x, y, visibility}``.
    Returns ``None`` when there are no landmarks (no pose detected). Raises
    ``ValueError`` on malformed / oversized input.
    """
    if raw is None:
        return None
    if not isinstance(raw, list):
        raise ValueError("landmarks must be a list")
    if not raw:
        return None
    if len(raw) > MAX_LANDMARKS:
        raise ValueError(f"too many landmarks: {len(raw)} > {MAX_LANDMARKS}")
    out: dict[int, Landmark] = {}
    for idx, lm in enumerate(raw):
        if not isinstance(lm, dict):
            raise ValueError(f"landmark {idx} is not an object")
        vis_raw = lm.get("visibility", 1.0)
        vis = _coerce_float(vis_raw if vis_raw is not None else 1.0, f"landmark[{idx}].visibility")
        out[idx] = Landmark(
            x=_coerce_float(lm.get("x", 0.0), f"landmark[{idx}].x"),
            y=_coerce_float(lm.get("y", 0.0), f"landmark[{idx}].y"),
            visibility=max(0.0, min(1.0, vis)),
        )
    return out


def process_landmarks(session: WebcamSession, msg: dict[str, Any]) -> dict[str, Any]:
    """Process one browser landmark message; return the data payload to send back.

    *msg* shape: ``{"t": <seconds>, "landmarks": [...], "world": [...]}``. The
    ``world`` key is optional; ``FeatureExtractor`` falls back to image landmarks
    when world landmarks are absent. Raises ``ValueError`` on malformed input.
    """
    if not isinstance(msg, dict):
        raise ValueError("message must be an object")

    timestamp = _coerce_float(msg.get("t", 0.0), "t")
    session.last_activity = time.monotonic()
    # fps is derived from the browser capture timestamps (seconds), which reflect
    # the real camera frame rate — not server processing time.
    if session._t0 is None:
        session._t0 = timestamp

    landmarks = _to_landmarks(msg.get("landmarks"))
    world = _to_landmarks(msg.get("world"))

    session.frame_count += 1
    fc = session.frame_count

    payload: dict[str, Any] = {
        "t": timestamp,
        "angle": None,
        "visibility": 0.0,
        "rep_count": session.counter.rep_count,
        "rep_state": None,
        "paused": session.counter.paused,
        "partial": session.counter.partial,
        "lost_track": False,
        "uncalibrated": session.counter.uncalibrated,
        "fps": 0.0,
    }

    step: CountStep | None = None
    if landmarks is None:
        payload["lost_track"] = True
    else:
        pose = PoseFrame(
            landmarks=landmarks,
            timestamp=timestamp,
            world_landmarks=world,
        )
        feat = session.fe.update(pose)
        step = session.counter.update(feat.angle, visibility=feat.visibility)
        payload["angle"] = feat.angle
        payload["visibility"] = feat.visibility
        payload["rep_count"] = step.rep_count
        payload["rep_state"] = step.state.value if step.state else None
        payload["paused"] = step.paused
        payload["partial"] = step.partial
        payload["uncalibrated"] = step.uncalibrated

        if step.rep_event:
            session.recorder.append_rep_event(step.rep_event, timestamp)

        # Record the auto-calibrated standing angle into the session summary
        # once the counter calibrates (parity with the upload pipeline).
        if not session._calibration_recorded and not step.uncalibrated:
            standing = session.counter.standing_angle
            if standing is not None:
                session.recorder.set_calibration(standing)
                session._calibration_recorded = True

    elapsed = timestamp - session._t0
    fps = round(fc / elapsed, 1) if elapsed > 0 else 0.0
    payload["fps"] = fps
    if fps > 0:
        session.recorder.set_fps(fps)

    session.recorder.append_frame(
        fc,
        timestamp,
        angle=payload["angle"],
        visibility=payload["visibility"],
        step=step,
    )
    return payload


__all__ = ["WebcamSession", "process_landmarks", "MAX_LANDMARKS"]
