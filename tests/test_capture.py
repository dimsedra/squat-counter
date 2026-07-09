"""M5 tests for the Capture seam (WebcamCapture, VideoFileCapture).
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import cv2
import numpy as np
import pytest

from repcounter.capture import Frame, VideoFileCapture, WebcamCapture


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _mock_cap(read_returns: list[tuple[bool, object]]) -> MagicMock:
    """Build a ``cv2.VideoCapture`` mock that returns *read_returns* in order,
    then (False, None)."""
    cap = MagicMock()
    cap.read.side_effect = read_returns + [(False, None)]
    cap.get.return_value = 30.0
    return cap


_DUMMY_BGR = np.zeros((100, 100, 3), dtype=np.uint8)


# --------------------------------------------------------------------------- #
# WebcamCapture
# --------------------------------------------------------------------------- #
def test_webcam_capture_yields_frames():
    cap = _mock_cap([(True, _DUMMY_BGR), (True, _DUMMY_BGR)])
    with patch("cv2.VideoCapture", return_value=cap):
        frames = list(WebcamCapture(0))
    assert len(frames) == 2
    for f in frames:
        assert isinstance(f, Frame)
        assert isinstance(f.image, np.ndarray)
        assert f.image.shape == (100, 100, 3)
        assert isinstance(f.timestamp, float)


def test_webcam_capture_stops_when_read_fails():
    cap = _mock_cap([])  # immediately fails
    with patch("cv2.VideoCapture", return_value=cap):
        frames = list(WebcamCapture(0))
    assert frames == []


def test_webcam_capture_context_manager_releases():
    cap = _mock_cap([])
    with patch("cv2.VideoCapture", return_value=cap) as mock_cls:
        with WebcamCapture(0) as wc:
            assert isinstance(wc, WebcamCapture)
        mock_cls.return_value.release.assert_called_once()


def test_webcam_capture_sets_resolution():
    cap = _mock_cap([])
    with patch("cv2.VideoCapture", return_value=cap):
        WebcamCapture(1, width=1920, height=1080)
    cap.set.assert_any_call(cv2.CAP_PROP_FRAME_WIDTH, 1920)
    cap.set.assert_any_call(cv2.CAP_PROP_FRAME_HEIGHT, 1080)


def test_webcam_capture_preview_fps():
    cap = _mock_cap([])
    cap.get.return_value = 15.0
    with patch("cv2.VideoCapture", return_value=cap):
        wc = WebcamCapture(0)
    assert wc.preview_fps == 15.0


def test_webcam_capture_preview_fps_fallback():
    cap = _mock_cap([])
    cap.get.return_value = 0.0  # camera didn't report fps
    with patch("cv2.VideoCapture", return_value=cap):
        wc = WebcamCapture(0)
    assert wc.preview_fps == 30.0


# --------------------------------------------------------------------------- #
# VideoFileCapture
# --------------------------------------------------------------------------- #
def test_video_file_capture_yields_frames():
    cap = _mock_cap([(True, _DUMMY_BGR)])
    with patch("cv2.VideoCapture", return_value=cap):
        frames = list(VideoFileCapture("dummy.mp4"))
    assert len(frames) == 1
    assert isinstance(frames[0], Frame)


def test_video_file_capture_stops_when_read_fails():
    cap = _mock_cap([])
    with patch("cv2.VideoCapture", return_value=cap):
        frames = list(VideoFileCapture("dummy.mp4"))
    assert frames == []


def test_video_file_capture_context_manager_releases():
    cap = _mock_cap([])
    with patch("cv2.VideoCapture", return_value=cap) as mock_cls:
        with VideoFileCapture("dummy.mp4") as vf:
            assert isinstance(vf, VideoFileCapture)
        mock_cls.return_value.release.assert_called_once()


def test_video_file_capture_total_frames():
    cap = _mock_cap([])
    cap.get.side_effect = lambda prop: {cv2.CAP_PROP_FRAME_COUNT: 123}.get(prop, 30.0)
    with patch("cv2.VideoCapture", return_value=cap):
        vf = VideoFileCapture("dummy.mp4")
    assert vf.total_frames == 123


def test_video_file_capture_fps():
    cap = _mock_cap([])
    cap.get.return_value = 29.97
    with patch("cv2.VideoCapture", return_value=cap):
        vf = VideoFileCapture("dummy.mp4")
    assert vf.fps == 29.97


# --------------------------------------------------------------------------- #
# Protocol conformance (duck-typing check)
# --------------------------------------------------------------------------- #
def test_capture_protocol_webcam():
    cap = _mock_cap([])
    with patch("cv2.VideoCapture", return_value=cap):
        from repcounter.capture import Capture
        wc = WebcamCapture(0)
        assert isinstance(wc, Capture)


def test_capture_protocol_video():
    cap = _mock_cap([])
    with patch("cv2.VideoCapture", return_value=cap):
        from repcounter.capture import Capture
        vf = VideoFileCapture("dummy.mp4")
        assert isinstance(vf, Capture)
