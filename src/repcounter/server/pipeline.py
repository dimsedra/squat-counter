"""Pipeline runner: wraps Capture -> Detect -> Features -> Count -> Present
in a background thread, pushing annotated frames + real-time data to shared
queues for the server to stream.

For uploaded video files the pipeline auto-stops and finalises the session
when the video ends. Live webcam stays open until the user clicks Stop.
"""
from __future__ import annotations

import time
import threading
from dataclasses import dataclass, field
from pathlib import Path
from queue import Queue

import cv2

from repcounter.capture import Frame, VideoFileCapture, WebcamCapture
from repcounter.count import RepCounter
from repcounter.detect import PoseLandmarkerDetector
from repcounter.features import FeatureExtractor
from repcounter.present import draw_overlay
from repcounter.server.session import SessionRecorder
from repcounter.types import CountStep


@dataclass
class FrameData:
    """Snapshotted per-frame data pushed via WebSocket."""
    timestamp: float
    angle: float | None = None
    visibility: float = 0.0
    rep_count: int = 0
    rep_state: str | None = None
    paused: bool = False
    partial: bool = False
    lost_track: bool = False
    uncalibrated: bool = False
    fps: float = 0.0


@dataclass
class PipelineState:
    """Shared state between pipeline thread and server routes."""
    frame_queue: Queue = field(default_factory=lambda: Queue(maxsize=8))
    data_queue: Queue = field(default_factory=Queue)
    running: bool = False
    completed: bool = False
    session: SessionRecorder | None = None
    frame_count: int = 0
    error: str | None = None
    upload_path: str | None = None


def run_pipeline(
    capture: WebcamCapture | VideoFileCapture,
    model_path: str | Path,
    state: PipelineState,
    *,
    session: SessionRecorder | None = None,
) -> None:
    """Run the full pipeline in a thread. Pushes (jpg_bytes, FrameData) into
    *state.frame_queue* and *state.data_queue* respectively.

    For ``VideoFileCapture`` the session is auto-finalised when the video ends.
    For ``WebcamCapture`` the caller must stop via ``state.running = False``.
    """
    try:
        det = PoseLandmarkerDetector(model_path)
        fe = FeatureExtractor()
        counter = RepCounter()

        state.running = True
        state.session = session
        state.frame_count = 0
        fps_estimate = getattr(capture, "fps", 30.0)
        if session:
            session.set_fps(fps_estimate)

        is_file = isinstance(capture, VideoFileCapture)

        t0 = time.monotonic()
        for frame in capture:
            if not state.running:
                break

            pose = det.detect(frame.image, timestamp=frame.timestamp)
            landmarks = (
                {k: (v.x, v.y) for k, v in pose.landmarks.items()}
                if pose else None
            )

            data = FrameData(timestamp=frame.timestamp)

            if pose is None:
                vis = draw_overlay(
                    frame.image, counter.rep_count, None,
                    counter.partial, counter.paused,
                    lost_track=True, landmarks=None,
                )
                data.lost_track = True
                data.paused = counter.paused
            else:
                feat = fe.update(pose)
                step = counter.update(feat.angle, visibility=feat.visibility)
                data.angle = feat.angle
                data.visibility = feat.visibility
                data.rep_count = step.rep_count
                data.rep_state = step.state.value if step.state else None
                data.paused = step.paused
                data.partial = step.partial
                data.uncalibrated = step.uncalibrated

                if session and step.rep_event:
                    session.append_rep_event(step.rep_event, frame.timestamp)

                vis = draw_overlay(
                    frame.image, step.rep_count, step.state,
                    step.partial, step.paused,
                    lost_track=False, landmarks=landmarks,
                )

            elapsed = time.monotonic() - t0
            data.fps = round(state.frame_count / elapsed, 1) if elapsed > 0 else 0.0

            _, jpg = cv2.imencode(".jpg", vis, [cv2.IMWRITE_JPEG_QUALITY, 85])
            state.frame_queue.put(jpg.tobytes())
            state.data_queue.put(data)
            state.frame_count += 1

            if session:
                session.append_frame(
                    state.frame_count, frame.timestamp,
                    angle=data.angle, visibility=data.visibility,
                    step=CountStep(
                        state=counter.state,
                        rep_count=counter.rep_count,
                        rep_event=None,
                        partial=counter.partial,
                        paused=counter.paused,
                        uncalibrated=counter.uncalibrated,
                    ) if pose else None,
                )

        # ── File playback ended — auto-finalise ──────────────────────────
        if is_file and session:
            state.completed = True
            session.stop()
            # Push a sentinel so the WebSocket knows processing is done.
            data_sentinel = FrameData(
                timestamp=time.monotonic(),
                fps=0.0,
            )
            data_sentinel.rep_count = counter.rep_count
            state.data_queue.put(data_sentinel)

    except Exception as exc:
        state.error = str(exc)
    finally:
        state.running = False
        # Auto-finalise on completion (file) or error; webcam stays open.
        if session and (state.completed or state.error):
            session.stop()
            # Remove the uploaded file to avoid accumulating garbage.
            if state.completed and state.upload_path:
                try:
                    Path(state.upload_path).unlink(missing_ok=True)
                except Exception:
                    pass
        det.release()
        capture.release()
