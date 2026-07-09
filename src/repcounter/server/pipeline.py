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


def _log(msg: str) -> None:
    print(f"  [pipeline] {msg}", flush=True)


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
    complete: bool = False


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
    session_id = session.session_id[:8] if session else "?"
    cap_type = "file" if isinstance(capture, VideoFileCapture) else "webcam"
    _log(f"[{session_id}] pipeline starting (capture={cap_type})")

    try:
        _log(f"[{session_id}] loading model ...")
        det = PoseLandmarkerDetector(model_path)
        _log(f"[{session_id}] model loaded")

        fe = FeatureExtractor()
        counter = RepCounter()

        state.running = True
        state.session = session
        state.frame_count = 0
        fps_estimate = getattr(capture, "fps", 30.0)
        if session:
            session.set_fps(fps_estimate)

        is_file = isinstance(capture, VideoFileCapture)
        first_frame = True

        t0 = time.monotonic()
        for frame in capture:
            if not state.running:
                break

            fc = state.frame_count + 1

            if first_frame:
                _log(f"[{session_id}] first frame received ({frame.image.shape}), processing ...")
                first_frame = False
            elif fc == 4:
                _log(f"[{session_id}] frame 4 received, processing ...")

            t_start = time.monotonic()
            pose = det.detect(frame.image, timestamp=frame.timestamp)
            t_detect = time.monotonic() - t_start
            if t_detect > 2.0:
                _log(f"[{session_id}] frame {fc}: detect took {t_detect:.1f}s")

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
            data.fps = round(fc / elapsed, 1) if elapsed > 0 else 0.0

            t_encode = time.monotonic()
            _, jpg = cv2.imencode(".jpg", vis, [cv2.IMWRITE_JPEG_QUALITY, 85])
            state.frame_queue.put(jpg.tobytes())
            state.data_queue.put(data)
            state.frame_count = fc
            t_enqueue = time.monotonic() - t_encode
            if t_enqueue > 0.5:
                _log(f"[{session_id}] frame {fc}: blocked on enqueue for {t_enqueue:.1f}s")

            if fc <= 3 or fc % 30 == 0:
                _log(f"[{session_id}] frame {fc} done ({t_detect:.2f}s detect)")

            if session:
                try:
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
                except Exception as exc:
                    _log(f"[{session_id}] append_frame error: {exc}")

        # ── File playback ended — auto-finalise ──────────────────────────
        if is_file and session:
            _log(f"[{session_id}] video ended ({state.frame_count} frames)")
            state.completed = True
            session.stop()
            state.data_queue.put(FrameData(
                timestamp=time.monotonic(), fps=0.0,
                rep_count=counter.rep_count, complete=True,
            ))

    except Exception as exc:
        state.error = str(exc)
        _log(f"[{session_id}] ERROR: {exc}")
    finally:
        state.running = False
        # Push sentinels so blocking get() in async handlers can exit.
        # Always sentinel — regardless of completion/error — to unblock
        # webcam and uploaded-video handlers alike.
        state.frame_queue.put(None)
        state.data_queue.put(FrameData(
            timestamp=0, fps=0.0, complete=True,
        ))
        if session:
            session.stop()  # idempotent (no-op if already stopped)
            if state.completed and state.upload_path:
                try:
                    Path(state.upload_path).unlink(missing_ok=True)
                    _log(f"[{session_id}] cleaned up uploaded file")
                except Exception:
                    pass
        det.release()
        capture.release()
        _log(f"[{session_id}] pipeline done")
