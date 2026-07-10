"""Headless batch processing: many videos -> one analysis-ready CSV.

Each video is decoded and run through the same pure counting chain used by the
web/upload paths (Detect -> Features -> Count) with no GUI, no streaming, and no
per-frame output. The result is a single summary row per video (keyed by file
name + path) written to one CSV meant to be consumed directly by downstream
analysis.

The frame-by-frame signal is an internal computation only; callers get the
aggregate. Optionally, ``--per-video`` (via the CLI) also writes the raw
per-frame/per-rep audit files through ``SessionRecorder``.
"""
from __future__ import annotations

import atexit
import logging
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable

from repcounter.capture import Frame, VideoFileCapture
from repcounter.count import RepCounter
from repcounter.detect import PoseLandmarkerDetector
from repcounter.features import FeatureExtractor
from repcounter.server.session import SessionRecorder
from repcounter.types import CountStep

logger = logging.getLogger(__name__)

VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv"}

# Stable column order for the aggregate dataset. ``video`` + ``path`` are the
# join keys for pairing with externally-labelled sheets.
SUMMARY_FIELDS = [
    "video", "path", "status",
    "frames", "pose_frames", "duration_sec", "fps", "calibration_angle",
    "total_reps", "full_reps", "partial_reps", "paused_frames",
    "mean_depth_angle", "min_depth_angle", "error",
]


@dataclass
class VideoResult:
    """One summary row for a processed video."""
    video: str
    path: str
    status: str  # ok | uncalibrated | no_pose | error
    frames: int = 0
    pose_frames: int = 0
    duration_sec: float = 0.0
    fps: float = 0.0
    calibration_angle: float | None = None
    total_reps: int = 0
    full_reps: int = 0
    partial_reps: int = 0
    paused_frames: int = 0
    mean_depth_angle: float | None = None
    min_depth_angle: float | None = None
    error: str = ""

    def as_row(self) -> dict[str, object]:
        def fmt(v: object) -> object:
            if v is None:
                return ""
            if isinstance(v, float):
                return round(v, 3)
            return v
        return {f: fmt(getattr(self, f)) for f in SUMMARY_FIELDS}


def discover_videos(
    inputs: Iterable[str | Path], *, recursive: bool = False
) -> list[Path]:
    """Expand *inputs* (files and/or directories) into a sorted list of videos.

    Directories are scanned for supported extensions; explicit files are kept
    as-is regardless of extension.
    """
    found: list[Path] = []
    seen: set[Path] = set()

    def _add(p: Path) -> None:
        rp = p.resolve()
        if rp not in seen:
            seen.add(rp)
            found.append(p)

    for raw in inputs:
        p = Path(raw)
        if p.is_dir():
            globber = p.rglob("*") if recursive else p.glob("*")
            for child in globber:
                if child.is_file() and child.suffix.lower() in VIDEO_EXTENSIONS:
                    _add(child)
        elif p.is_file():
            _add(p)
    return sorted(found, key=lambda x: str(x))


@dataclass
class _Aggregate:
    """Raw tallies from streaming a video's frames through the counting chain."""
    frames: int = 0
    pose_frames: int = 0
    paused_frames: int = 0
    total_reps: int = 0
    full_reps: int = 0
    partial_reps: int = 0
    calibration_angle: float | None = None
    uncalibrated: bool = True
    depths: list[float] = field(default_factory=list)


def _count_frames(
    frames: Iterable[Frame],
    detector: PoseLandmarkerDetector,
    fe: FeatureExtractor,
    counter: RepCounter,
    *,
    recorder: SessionRecorder | None = None,
) -> _Aggregate:
    """Stream frames through Detect -> Features -> Count, tallying an aggregate.

    Pure over the frame iterable + injected detector/extractor/counter, so it is
    testable with fakes (no model, no video file).
    """
    agg = _Aggregate()
    for frame in frames:
        agg.frames += 1
        pose = detector.detect(frame.image, timestamp=frame.timestamp)
        step: CountStep | None = None
        angle = None
        visibility = 0.0
        if pose is not None:
            agg.pose_frames += 1
            feat = fe.update(pose)
            step = counter.update(feat.angle, visibility=feat.visibility)
            angle = feat.angle
            visibility = feat.visibility
            if step.paused:
                agg.paused_frames += 1
            if step.rep_event is not None:
                agg.depths.append(step.rep_event.depth_angle)
                if step.rep_event.is_full:
                    agg.full_reps += 1
                if recorder is not None:
                    recorder.append_rep_event(step.rep_event, frame.timestamp)
        if recorder is not None:
            recorder.append_frame(
                agg.frames, frame.timestamp,
                angle=angle, visibility=visibility, step=step,
            )

    agg.total_reps = counter.rep_count
    agg.partial_reps = agg.total_reps - agg.full_reps
    agg.calibration_angle = counter.standing_angle
    agg.uncalibrated = counter.uncalibrated
    return agg


def _status_for(frames: int, pose_frames: int, uncalibrated: bool) -> str:
    """Classify a processed video (excludes ``error``, set by exception paths).

    ``frames == 0`` (opened but decoded nothing) is an ``error`` so a corrupt or
    empty container is never confused with a genuine no-pose video.
    """
    if frames == 0:
        return "error"
    if pose_frames == 0:
        return "no_pose"
    if uncalibrated:
        return "uncalibrated"
    return "ok"


def process_video(
    path: str | Path,
    model_path: str | Path,
    *,
    standing_angle: float | None = None,
    detector: PoseLandmarkerDetector | None = None,
    per_video: bool = False,
) -> VideoResult:
    """Process a single video and return its summary row.

    Never raises for per-video failures: any error (bad file, decode failure,
    invalid recorder dir, etc.) is captured as ``status="error"`` so a batch run
    continues. Pass an existing *detector* to reuse a loaded model across many
    videos; otherwise one is created and released here. With *per_video*, raw
    per-frame/per-rep audit files are also written via ``SessionRecorder``.
    """
    path = Path(path)
    result = VideoResult(video=path.name, path=str(path), status="ok")

    own_detector = detector is None
    det: PoseLandmarkerDetector | None = None
    capture: VideoFileCapture | None = None
    recorder: SessionRecorder | None = None
    try:
        capture = VideoFileCapture(str(path))
        det = detector or PoseLandmarkerDetector(str(model_path))
        fe = FeatureExtractor()
        counter = RepCounter(standing_angle=standing_angle) if standing_angle else RepCounter()

        fps = float(getattr(capture, "fps", 0.0) or 0.0)
        total = int(getattr(capture, "total_frames", 0) or 0)
        result.fps = fps
        if per_video:
            recorder = SessionRecorder(label=path.stem, source="batch")
            recorder.start()
            recorder.set_fps(fps)

        agg = _count_frames(capture, det, fe, counter, recorder=recorder)

        # Duration from container metadata, falling back to the real decoded
        # frame count when metadata is missing/implausible (e.g. some HEVC).
        effective_total = total if (total > 0 and total >= agg.frames) else agg.frames
        result.duration_sec = (effective_total / fps) if fps > 0 else 0.0
        result.frames = agg.frames
        result.pose_frames = agg.pose_frames
        result.paused_frames = agg.paused_frames
        result.total_reps = agg.total_reps
        result.calibration_angle = agg.calibration_angle
        if agg.depths:
            result.full_reps = agg.full_reps
            result.partial_reps = agg.partial_reps
            result.mean_depth_angle = sum(agg.depths) / len(agg.depths)
            result.min_depth_angle = min(agg.depths)
        if recorder is not None and agg.calibration_angle is not None:
            recorder.set_calibration(agg.calibration_angle)

        result.status = _status_for(agg.frames, agg.pose_frames, agg.uncalibrated)
        if result.status == "error":
            result.error = "no frames decoded (empty or unreadable video)"
    except Exception as exc:  # noqa: BLE001
        result.status = "error"
        result.error = str(exc)
        logger.debug("process_video failed for %s", path, exc_info=True)
    finally:
        if own_detector and det is not None:
            det.release()
        if capture is not None:
            capture.release()
        if recorder is not None:
            recorder.stop()

    return result


# ── Parallel execution ─────────────────────────────────────────────────
# Worker plumbing lives in the package (not the CLI script) so it is importable
# by name in spawned child processes — robust pickling on Windows — and testable.

_WORKER_DET: PoseLandmarkerDetector | None = None
_WORKER_MODEL: str = ""


def _release_worker() -> None:
    global _WORKER_DET
    if _WORKER_DET is not None:
        try:
            _WORKER_DET.release()
        except Exception:
            pass
        _WORKER_DET = None


def _init_worker(model_str: str) -> None:
    """ProcessPool initializer: load one detector per worker, reused per task."""
    global _WORKER_DET, _WORKER_MODEL
    _WORKER_MODEL = model_str
    _WORKER_DET = PoseLandmarkerDetector(model_str)
    atexit.register(_release_worker)


def _process_task(args: tuple[str, float | None, bool]) -> VideoResult:
    path_str, standing_angle, per_video = args
    return process_video(
        path_str, _WORKER_MODEL,
        standing_angle=standing_angle, detector=_WORKER_DET, per_video=per_video,
    )


def run_batch(
    videos: Iterable[str | Path],
    model_path: str | Path,
    *,
    workers: int = 1,
    per_video: bool = False,
    standing_angle: float | None = None,
    on_result: Callable[[VideoResult, float | None], None] | None = None,
) -> list[VideoResult]:
    """Process *videos* into ``VideoResult`` rows, serially or across processes.

    Row order always matches input order. *on_result* (if given) is called as
    each result completes with ``(result, elapsed_seconds_or_None)`` for progress
    reporting (elapsed is None on the parallel path).
    """
    videos = list(videos)
    results: list[VideoResult] = []

    if workers <= 1:
        det = PoseLandmarkerDetector(str(model_path))
        try:
            for v in videos:
                t0 = time.monotonic()
                r = process_video(
                    v, model_path,
                    standing_angle=standing_angle, detector=det, per_video=per_video,
                )
                results.append(r)
                if on_result is not None:
                    on_result(r, time.monotonic() - t0)
        finally:
            det.release()
    else:
        tasks = [(str(v), standing_angle, per_video) for v in videos]
        with ProcessPoolExecutor(
            max_workers=workers, initializer=_init_worker, initargs=(str(model_path),)
        ) as pool:
            for r in pool.map(_process_task, tasks):
                results.append(r)
                if on_result is not None:
                    on_result(r, None)
    return results


def write_summary_csv(results: Iterable[VideoResult], out_path: str | Path) -> Path:
    """Write one summary row per result to *out_path* (created/overwritten)."""
    import csv

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    # utf-8-sig: BOM keeps Excel happy and non-ASCII paths never crash the write.
    with out.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=SUMMARY_FIELDS)
        writer.writeheader()
        for r in results:
            writer.writerow(r.as_row())
    return out


__all__ = [
    "VideoResult",
    "SUMMARY_FIELDS",
    "VIDEO_EXTENSIONS",
    "discover_videos",
    "process_video",
    "run_batch",
    "write_summary_csv",
]
