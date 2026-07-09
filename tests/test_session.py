"""Unit tests for SessionRecorder.
"""
from __future__ import annotations

import csv
import io
import json
import shutil
from pathlib import Path

import pytest

from repcounter.server.session import SessionRecorder
from repcounter.types import CountStep, RepEvent, RepState


def test_session_id_is_generated():
    rec = SessionRecorder()
    assert len(rec.session_id) == 12
    assert isinstance(rec.session_id, str)


def test_start_creates_directory():
    rec = SessionRecorder(label="test_session")
    rec.start()
    assert rec.dir.exists()
    rec.stop()  # closes CSV file handles
    shutil.rmtree(rec.dir)


def test_append_frame():
    rec = SessionRecorder()
    rec.start()
    step = CountStep(state=RepState.DESCENDING, rep_count=1, rep_event=None, partial=False, paused=False)
    rec.append_frame(0, 1.0, angle=150.0, visibility=0.9, step=step)
    out_dir = rec.stop()

    rows = list(csv.DictReader((out_dir / "frames.csv").read_text().splitlines()))
    assert len(rows) == 1
    assert rows[0]["frame_idx"] == "0"
    assert rows[0]["angle"] == "150.0"
    assert rows[0]["rep_state"] == "descending"
    shutil.rmtree(out_dir)


def test_append_frame_without_step():
    rec = SessionRecorder()
    rec.start()
    rec.append_frame(5, 2.0, angle=None, visibility=0.0)
    out_dir = rec.stop()

    rows = list(csv.DictReader((out_dir / "frames.csv").read_text().splitlines()))
    assert len(rows) == 1
    assert rows[0]["rep_count"] == "0"
    assert rows[0]["paused"] == "False"
    shutil.rmtree(out_dir)


def test_append_rep_event():
    rec = SessionRecorder()
    rec.start()
    event = RepEvent(rep_index=1, depth_angle=87.3, is_full=True)
    rec.append_rep_event(event, 12.5)
    out_dir = rec.stop()

    rows = list(csv.DictReader((out_dir / "events.csv").read_text().splitlines()))
    assert len(rows) == 1
    assert rows[0]["rep_index"] == "1"
    assert rows[0]["depth_angle"] == "87.3"
    shutil.rmtree(out_dir)


def test_stop_flushes_files():
    rec = SessionRecorder(label="flush_test", source="upload")
    rec.start()
    step = CountStep(state=RepState.STANDING, rep_count=0, rep_event=None, partial=False, paused=False)
    rec.append_frame(0, 0.0, angle=170.0, visibility=1.0, step=step)

    event = RepEvent(rep_index=1, depth_angle=90.0, is_full=True)
    rec.append_rep_event(event, 1.0)
    rec.set_calibration(165.0)
    rec.set_fps(30.0)

    out_dir = rec.stop()

    assert (out_dir / "summary.json").exists()
    assert (out_dir / "frames.csv").exists()
    assert (out_dir / "events.csv").exists()

    summary = json.loads((out_dir / "summary.json").read_text())
    assert summary["label"] == "flush_test"
    assert summary["source"] == "upload"
    assert summary["total_frames"] == 1
    assert summary["total_reps"] == 1
    assert summary["full_reps"] == 1
    assert summary["calibration_angle"] == 165.0
    assert summary["fps"] == 30.0

    frames_csv = (out_dir / "frames.csv").read_text()
    assert "frame_idx,timestamp,angle" in frames_csv
    assert "0,0.0,170.0" in frames_csv

    events_csv = (out_dir / "events.csv").read_text()
    assert "rep_index,timestamp,depth_angle" in events_csv
    assert "1,1.0,90.0,True" in events_csv

    shutil.rmtree(out_dir)


def test_empty_session_has_zero_reps():
    rec = SessionRecorder()
    rec.start()
    out_dir = rec.stop()
    summary = json.loads((out_dir / "summary.json").read_text())
    assert summary["total_reps"] == 0
    assert summary["full_reps"] == 0
    assert summary["total_frames"] == 0
    shutil.rmtree(out_dir)
