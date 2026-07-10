"""Tests for the headless batch multi-video processor (scripts/batch.py core).

Pure/CSV tests always run. The end-to-end ``process_video`` test is
skip-guarded on the model + the source.mp4 fixture (like test_detect.py).
"""
from __future__ import annotations

import csv
import importlib.util
import math
import sys
from pathlib import Path

import pytest

from repcounter.batch import (
    SUMMARY_FIELDS,
    VideoResult,
    _count_frames,
    _status_for,
    discover_videos,
    process_video,
    run_batch,
    write_summary_csv,
)
from repcounter.capture import Frame
from repcounter.count import RepCounter
from repcounter.features import FeatureExtractor
from repcounter.types import Landmark, PoseFrame

FIXTURES = Path(__file__).parent / "fixtures"
SOURCE = FIXTURES / "source.mp4"
MODEL_PATH = Path(__file__).resolve().parent.parent / "models" / "pose_landmarker_full.task"
SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "batch.py"

has_model = MODEL_PATH.exists()
has_source = SOURCE.exists()


# ── Fake detector driving scripted joint angles (no model needed) ──────

def _leg(hip, knee, angle_deg, vis, idx_hip, idx_knee, idx_ankle, out):
    ux, uy = hip[0] - knee[0], hip[1] - knee[1]
    th = math.radians(angle_deg)
    vx = ux * math.cos(th) - uy * math.sin(th)
    vy = ux * math.sin(th) + uy * math.cos(th)
    ankle = (knee[0] + vx, knee[1] + vy)
    out[idx_hip] = Landmark(hip[0], hip[1], vis)
    out[idx_knee] = Landmark(knee[0], knee[1], vis)
    out[idx_ankle] = Landmark(ankle[0], ankle[1], vis)


def _pose(angle_deg, vis=1.0):
    lm: dict[int, Landmark] = {}
    _leg((0.5, 0.2), (0.5, 0.5), angle_deg, vis, 23, 25, 27, lm)
    _leg((0.5, 0.2), (0.5, 0.5), angle_deg, vis, 24, 26, 28, lm)
    return PoseFrame(landmarks=lm, timestamp=0.0, world_landmarks=None)


class _FakeDetector:
    """Returns pre-scripted poses (or None) regardless of the image."""

    def __init__(self, poses):
        self._poses = list(poses)
        self._i = 0

    def detect(self, image, timestamp=None):
        p = self._poses[self._i] if self._i < len(self._poses) else None
        self._i += 1
        return p

    def release(self):
        pass


def _frames(n):
    return [Frame(image=None, timestamp=float(i)) for i in range(n)]


def _run(angles):
    poses = [_pose(a) if a is not None else None for a in angles]
    det = _FakeDetector(poses)
    return _count_frames(_frames(len(poses)), det, FeatureExtractor(), RepCounter())


def _load_cli():
    spec = importlib.util.spec_from_file_location("_batch_cli_test", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ── discover_videos ────────────────────────────────────────────────────

def test_discover_videos_finds_supported_extensions(tmp_path):
    (tmp_path / "a.mp4").write_bytes(b"x")
    (tmp_path / "b.MOV").write_bytes(b"x")
    (tmp_path / "c.avi").write_bytes(b"x")
    (tmp_path / "d.txt").write_bytes(b"x")
    (tmp_path / "notes.md").write_bytes(b"x")

    found = {p.name for p in discover_videos([tmp_path])}
    assert found == {"a.mp4", "b.MOV", "c.avi"}


def test_discover_videos_recursive(tmp_path):
    sub = tmp_path / "sub"
    sub.mkdir()
    (tmp_path / "a.mp4").write_bytes(b"x")
    (sub / "b.mp4").write_bytes(b"x")

    non_rec = {p.name for p in discover_videos([tmp_path], recursive=False)}
    rec = {p.name for p in discover_videos([tmp_path], recursive=True)}
    assert non_rec == {"a.mp4"}
    assert rec == {"a.mp4", "b.mp4"}


def test_discover_videos_accepts_explicit_files(tmp_path):
    f = tmp_path / "clip.mp4"
    f.write_bytes(b"x")
    found = [p.name for p in discover_videos([f])]
    assert found == ["clip.mp4"]


# ── write_summary_csv ──────────────────────────────────────────────────

def _sample_result(**over):
    base = dict(
        video="a.mp4", path="videos/a.mp4", status="ok",
        frames=100, pose_frames=95, duration_sec=4.0, fps=25.0,
        calibration_angle=170.0, total_reps=5, full_reps=3, partial_reps=1,
        paused_frames=2, mean_depth_angle=88.0, min_depth_angle=80.0, error="",
    )
    base.update(over)
    return VideoResult(**base)


def test_write_summary_csv_header_and_rows(tmp_path):
    out = tmp_path / "dataset.csv"
    write_summary_csv([_sample_result(), _sample_result(video="b.mp4")], out)

    rows = list(csv.DictReader(out.open(encoding="utf-8-sig", newline="")))
    header = out.read_text(encoding="utf-8-sig").splitlines()[0].split(",")
    assert header == SUMMARY_FIELDS
    assert len(rows) == 2
    assert rows[0]["video"] == "a.mp4"
    assert rows[0]["total_reps"] == "5"


def test_write_summary_csv_blank_depth_when_no_reps(tmp_path):
    out = tmp_path / "dataset.csv"
    r = _sample_result(
        total_reps=0, full_reps=0, partial_reps=0,
        mean_depth_angle=None, min_depth_angle=None,
    )
    write_summary_csv([r], out)
    row = next(csv.DictReader(out.open(encoding="utf-8-sig", newline="")))
    assert row["mean_depth_angle"] == ""
    assert row["min_depth_angle"] == ""


# ── process_video error handling (no model needed) ─────────────────────

def test_process_video_invalid_path_returns_error(tmp_path):
    missing = tmp_path / "nope.mp4"
    result = process_video(missing, MODEL_PATH)
    assert result.status == "error"
    assert result.error
    assert result.video == "nope.mp4"


# ── Schema contract ────────────────────────────────────────────────────

def test_summary_fields_frozen():
    """Guard the public dataset schema against accidental reorder/rename."""
    assert SUMMARY_FIELDS == [
        "video", "path", "status",
        "frames", "pose_frames", "duration_sec", "fps", "calibration_angle",
        "total_reps", "full_reps", "partial_reps", "paused_frames",
        "mean_depth_angle", "min_depth_angle", "error",
    ]


# ── Status classification (pure) ───────────────────────────────────────

def test_status_zero_frames_is_error_not_no_pose():
    assert _status_for(0, 0, True) == "error"


def test_status_branches():
    assert _status_for(10, 0, True) == "no_pose"
    assert _status_for(10, 5, True) == "uncalibrated"
    assert _status_for(10, 5, False) == "ok"


# ── Aggregation via fake detector (no model) ───────────────────────────

def test_count_frames_full_and_partial_split():
    # 6 standing frames calibrate; rep1 reaches 80 (full), rep2 reaches 95
    # (credited, parallel but not below-parallel -> not full).
    angles = (
        [170] * 6
        + [120, 80, 80, 120, 170, 170]
        + [120, 95, 95, 120, 170, 170]
    )
    agg = _run(angles)
    assert agg.total_reps == 2
    assert agg.full_reps == 1
    assert agg.partial_reps == 1
    assert len(agg.depths) == 2
    assert min(agg.depths) < 90.0   # the full rep
    assert max(agg.depths) >= 90.0  # the parallel-only rep


def test_count_frames_no_pose():
    agg = _run([None] * 10)
    assert agg.pose_frames == 0
    assert agg.total_reps == 0


def test_count_frames_uncalibrated_when_never_stands():
    agg = _run([80] * 12)  # only deep angles; never a standing baseline
    assert agg.pose_frames == 12
    assert agg.uncalibrated is True
    assert agg.total_reps == 0


# ── UTF-8 output ───────────────────────────────────────────────────────

def test_write_summary_csv_handles_non_ascii_path(tmp_path):
    out = tmp_path / "d.csv"
    write_summary_csv([_sample_result(video="squat_日本.mp4", path="videos/squat_日本.mp4")], out)
    rows = list(csv.DictReader(out.open(encoding="utf-8-sig", newline="")))
    assert rows[0]["video"] == "squat_日本.mp4"


# ── CLI --standing-angle validation (needs model to reach the check) ───

@pytest.mark.skipif(not has_model, reason="model not downloaded")
def test_cli_rejects_invalid_standing_angle(monkeypatch):
    cli = _load_cli()
    monkeypatch.setattr(sys, "argv", ["batch.py", "--standing-angle", "100", "--dir", "."])
    with pytest.raises(SystemExit) as ei:
        cli.main()
    assert "standing-angle" in str(ei.value).lower()


# ── process_video end-to-end (needs model + fixture) ───────────────────

@pytest.mark.skipif(not has_model, reason="pose_landmarker_full.task not downloaded")
@pytest.mark.skipif(not has_source, reason="tests/fixtures/source.mp4 not present")
def test_process_video_counts_reps_on_source():
    result = process_video(SOURCE, MODEL_PATH)
    assert result.status == "ok"
    assert result.total_reps == 5
    assert result.pose_frames > 0
    assert result.min_depth_angle is not None
    assert result.min_depth_angle <= 100.0
    assert result.fps > 0


@pytest.mark.skipif(not has_model, reason="pose_landmarker_full.task not downloaded")
@pytest.mark.skipif(not has_source, reason="tests/fixtures/source.mp4 not present")
def test_run_batch_parallel_preserves_order(tmp_path):
    """Exercises the real ProcessPool path: spawn, initializer, pickling, order."""
    import shutil

    a = tmp_path / "a.mp4"
    b = tmp_path / "b.mp4"
    shutil.copy(SOURCE, a)
    shutil.copy(SOURCE, b)

    results = run_batch([a, b], MODEL_PATH, workers=2)
    assert [r.video for r in results] == ["a.mp4", "b.mp4"]
    assert all(r.status == "ok" for r in results)
    assert all(r.total_reps == 5 for r in results)
