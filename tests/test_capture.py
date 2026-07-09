"""M5 tests for the Capture seam (WebcamCapture, VideoFileCapture).
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import cv2
import numpy as np
import pytest

from repcounter.capture import Frame, VideoFileCapture, WebcamCapture


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _mock_cap(read_returns: list[tuple[bool, object]], is_opened: bool = True) -> MagicMock:
    cap = MagicMock()
    cap.read.side_effect = read_returns + [(False, None)]
    cap.isOpened.return_value = is_opened
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
    cap = _mock_cap([])
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


def test_webcam_capture_timestamps_monotonic():
    cap = _mock_cap(
        [(True, _DUMMY_BGR), (True, _DUMMY_BGR), (True, _DUMMY_BGR)]
    )
    with patch("cv2.VideoCapture", return_value=cap):
        with patch("time.monotonic", side_effect=[1.0, 2.0, 3.0]):
            frames = list(WebcamCapture(0))
    timestamps = [f.timestamp for f in frames]
    assert all(t2 >= t1 for t1, t2 in zip(timestamps, timestamps[1:]))


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


def test_video_file_capture_unreadable_raises():
    cap = _mock_cap([], is_opened=False)
    with patch("cv2.VideoCapture", return_value=cap):
        with pytest.raises(ValueError, match="cannot open video file"):
            VideoFileCapture("bad.mp4")


def test_video_file_capture_timestamps_monotonic():
    cap = _mock_cap(
        [(True, _DUMMY_BGR), (True, _DUMMY_BGR), (True, _DUMMY_BGR)]
    )
    with patch("cv2.VideoCapture", return_value=cap):
        with patch("time.monotonic", side_effect=[10.0, 10.5, 11.0]):
            frames = list(VideoFileCapture("dummy.mp4"))
    timestamps = [f.timestamp for f in frames]
    assert all(t2 >= t1 for t1, t2 in zip(timestamps, timestamps[1:]))


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
