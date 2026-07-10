"""Session recorder: logs per-frame data + rep events to CSV/JSON on disk.

Output layout per session::

  sessions/{session_id}/
    summary.json       # metadata + aggregate stats
    frames.csv         # frame_idx, timestamp, angle, visibility, rep_state, rep_count, paused, partial
    events.csv         # rep_index, timestamp, depth_angle, is_full

Each frame is flushed to disk immediately (no in-memory buffer).
"""
from __future__ import annotations

import csv
import json
import threading
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import IO

from repcounter.types import CountStep

SESSIONS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "sessions"


@dataclass
class FrameRecord:
    frame_idx: int
    timestamp: float
    angle: float | None = None
    visibility: float = 0.0
    rep_state: str | None = None
    rep_count: int = 0
    paused: bool = False
    partial: bool = False


@dataclass
class RepEventRecord:
    rep_index: int
    timestamp: float
    depth_angle: float
    is_full: bool


_FRAME_FIELDS = [
    "frame_idx", "timestamp", "angle", "visibility",
    "rep_state", "rep_count", "paused", "partial",
]
_EVENT_FIELDS = ["rep_index", "timestamp", "depth_angle", "is_full"]


class SessionRecorder:
    """Records one session (webcam run or uploaded video processing).

    Frames are written to CSV immediately — safe for long recordings.
    Usage::

        rec = SessionRecorder(label="lighting_normal_cam_left")
        rec.start()
        for frame_data in pipeline:
            rec.append_frame(...)
        rec.stop()
    """

    def __init__(
        self,
        *,
        label: str = "",
        source: str = "webcam",
        session_id: str | None = None,
    ) -> None:
        self.session_id = session_id or uuid.uuid4().hex[:12]
        self.label = label
        self.source = source
        self._started: float = 0.0
        self._stopped: float = 0.0
        self._fps_estimate: float = 0.0
        self._calibration_angle: float | None = None
        self._frame_fh: IO | None = None
        self._event_fh: IO | None = None
        self._total_reps: int = 0
        self._full_reps: int = 0
        self._partial_reps: int = 0
        self._total_frames: int = 0
        self._paused_frames: int = 0
        # Guards append_frame / append_rep_event / stop against concurrent
        # access (WS worker thread writing while an HTTP stop closes files).
        self._lock = threading.Lock()
        self._closed = False

    @property
    def dir(self) -> Path:
        return SESSIONS_DIR / self.session_id

    def start(self) -> None:
        import time
        self._started = time.monotonic()
        d = self.dir
        d.mkdir(parents=True, exist_ok=True)

        self._frame_fh = (d / "frames.csv").open("w", newline="")
        w = csv.DictWriter(self._frame_fh, fieldnames=_FRAME_FIELDS)
        w.writeheader()

        self._event_fh = (d / "events.csv").open("w", newline="")
        w = csv.DictWriter(self._event_fh, fieldnames=_EVENT_FIELDS)
        w.writeheader()

    def set_calibration(self, angle: float) -> None:
        self._calibration_angle = angle

    def set_fps(self, fps: float) -> None:
        self._fps_estimate = fps

    def append_frame(
        self,
        frame_idx: int,
        timestamp: float,
        *,
        angle: float | None = None,
        visibility: float = 0.0,
        step: CountStep | None = None,
    ) -> None:
        rec = FrameRecord(
            frame_idx=frame_idx,
            timestamp=timestamp,
            angle=angle,
            visibility=visibility,
            rep_state=step.state.value if step else None,
            rep_count=step.rep_count if step else 0,
            paused=step.paused if step else False,
            partial=step.partial if step else False,
        )
        with self._lock:
            if self._closed:
                return
            if self._frame_fh:
                csv.DictWriter(self._frame_fh, fieldnames=_FRAME_FIELDS).writerow(asdict(rec))
                self._frame_fh.flush()
            self._total_frames += 1
            if rec.paused:
                self._paused_frames += 1

    def append_rep_event(self, event, timestamp: float) -> None:
        rec = RepEventRecord(
            rep_index=event.rep_index,
            timestamp=timestamp,
            depth_angle=event.depth_angle,
            is_full=event.is_full,
        )
        with self._lock:
            if self._closed:
                return
            if self._event_fh:
                csv.DictWriter(self._event_fh, fieldnames=_EVENT_FIELDS).writerow(asdict(rec))
                self._event_fh.flush()
            self._total_reps = event.rep_index
            if event.is_full:
                self._full_reps += 1
            else:
                self._partial_reps += 1

    def stop(self) -> Path:
        import time
        with self._lock:
            if self._closed:
                return self.dir
            self._closed = True
            self._stopped = time.monotonic()
            self._close_files()
            self._write_summary()
        return self.dir

    def _close_files(self) -> None:
        if self._frame_fh:
            self._frame_fh.close()
            self._frame_fh = None
        if self._event_fh:
            self._event_fh.close()
            self._event_fh = None

    def _write_summary(self) -> None:
        d = self.dir
        duration = self._stopped - self._started
        (d / "summary.json").write_text(
            json.dumps({
                "id": self.session_id,
                "label": self.label,
                "source": self.source,
                "started_at": self._started,
                "duration_sec": round(duration, 3),
                "fps": round(self._fps_estimate, 2),
                "calibration_angle": self._calibration_angle,
                "total_frames": self._total_frames,
                "total_reps": self._total_reps,
                "full_reps": self._full_reps,
                "partial_reps": self._partial_reps,
                "paused_frames": self._paused_frames,
            }, indent=2) + "\n"
        )

    def summary(self) -> dict:
        return {
            "id": self.session_id,
            "label": self.label,
            "source": self.source,
            "frames": self._total_frames,
            "reps": self._total_reps,
            "full": self._full_reps,
            "partial": self._partial_reps,
            "dir": str(self.dir),
        }

    def __enter__(self) -> SessionRecorder:
        self.start()
        return self

    def __exit__(self, *exc_info) -> None:
        self.stop()


__all__ = ["SessionRecorder", "FrameRecord", "RepEventRecord"]
