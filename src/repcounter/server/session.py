"""Session recorder: logs per-frame data + rep events to CSV/JSON on disk.

Output layout per session::

  sessions/{session_id}/
    summary.json       # metadata + aggregate stats
    frames.csv         # frame_idx, timestamp, angle, visibility, rep_state, rep_count, paused, partial
    events.csv         # rep_index, timestamp, depth_angle, is_full
"""
from __future__ import annotations

import csv
import json
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import IO

from repcounter.types import CountStep, RepState

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


class SessionRecorder:
    """Records one session (webcam run or uploaded video processing).

    Usage::

        rec = SessionRecorder(label="lighting_normal_cam_left")
        rec.start()
        for frame_data in pipeline:
            rec.append_frame(frame_data)
        rec.stop()
    """

    def __init__(self, *, label: str = "", source: str = "webcam") -> None:
        self.session_id = uuid.uuid4().hex[:12]
        self.label = label
        self.source = source
        self._frames: list[FrameRecord] = []
        self._events: list[RepEventRecord] = []
        self._started: float = 0.0
        self._stopped: float = 0.0
        self._calibration_angle: float | None = None
        self._fps_estimate: float = 0.0

    @property
    def dir(self) -> Path:
        return SESSIONS_DIR / self.session_id

    def start(self) -> None:
        import time
        self._started = time.monotonic()
        self.dir.mkdir(parents=True, exist_ok=True)

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
        self._frames.append(FrameRecord(
            frame_idx=frame_idx,
            timestamp=timestamp,
            angle=angle,
            visibility=visibility,
            rep_state=step.state.value if step else None,
            rep_count=step.rep_count if step else 0,
            paused=step.paused if step else False,
            partial=step.partial if step else False,
        ))

    def append_rep_event(self, event, timestamp: float) -> None:
        self._events.append(RepEventRecord(
            rep_index=event.rep_index,
            timestamp=timestamp,
            depth_angle=event.depth_angle,
            is_full=event.is_full,
        ))

    def stop(self) -> Path:
        import time
        self._stopped = time.monotonic()
        self._flush()
        return self.dir

    def _flush(self) -> None:
        d = self.dir
        duration = self._stopped - self._started
        total_reps = self._events[-1].rep_index if self._events else 0
        full_reps = sum(1 for e in self._events if e.is_full)
        partial_reps = total_reps - full_reps

        frames_csv = d / "frames.csv"
        with frames_csv.open("w", newline="") as f:
            self._write_frames_csv(f)

        events_csv = d / "events.csv"
        with events_csv.open("w", newline="") as f:
            self._write_events_csv(f)

        summary = {
            "id": self.session_id,
            "label": self.label,
            "source": self.source,
            "started_at": self._started,
            "duration_sec": round(duration, 3),
            "fps": round(self._fps_estimate, 2),
            "calibration_angle": self._calibration_angle,
            "total_frames": len(self._frames),
            "total_reps": total_reps,
            "full_reps": full_reps,
            "partial_reps": partial_reps,
            "paused_frames": sum(1 for f in self._frames if f.paused),
        }
        (d / "summary.json").write_text(
            json.dumps(summary, indent=2) + "\n"
        )

    def _write_frames_csv(self, buf: IO) -> None:
        fields = ["frame_idx", "timestamp", "angle", "visibility",
                   "rep_state", "rep_count", "paused", "partial"]
        writer = csv.DictWriter(buf, fieldnames=fields)
        writer.writeheader()
        for fr in self._frames:
            writer.writerow(asdict(fr))

    def _write_events_csv(self, buf: IO) -> None:
        fields = ["rep_index", "timestamp", "depth_angle", "is_full"]
        writer = csv.DictWriter(buf, fieldnames=fields)
        writer.writeheader()
        for ev in self._events:
            writer.writerow(asdict(ev))

    def summary(self) -> dict:
        total_reps = self._events[-1].rep_index if self._events else 0
        return {
            "id": self.session_id,
            "label": self.label,
            "source": self.source,
            "frames": len(self._frames),
            "reps": total_reps,
            "events": len(self._events),
            "dir": str(self.dir),
        }


__all__ = ["SessionRecorder", "FrameRecord", "RepEventRecord"]
