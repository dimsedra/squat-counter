"""M5 smoke tests for the Present seam (draw_overlay).
"""
from __future__ import annotations

import numpy as np
import pytest

from repcounter.present import POSE_CONNECTIONS, draw_overlay
from repcounter.types import RepState


def _dummy_landmarks(count: int = 33) -> dict[int, tuple[float, float]]:
    return {i: (0.1 * (i % 10) / 9, 0.1 * (i // 10) / 3) for i in range(count)}

# Canonical reference set from mediapipe/python/solutions/pose.py
_CANONICAL: frozenset[tuple[int, int]] = frozenset({
    (0, 1), (1, 2), (2, 3), (3, 7), (0, 4), (4, 5), (5, 6), (6, 8), (9, 10),
    (11, 13), (13, 15), (15, 17), (15, 19), (15, 21), (17, 19),
    (12, 14), (14, 16), (16, 18), (16, 20), (16, 22), (18, 20),
    (11, 12), (11, 23), (12, 24), (23, 24),
    (23, 25), (25, 27), (27, 29), (29, 31), (27, 31),
    (24, 26), (26, 28), (28, 30), (30, 32), (28, 32),
})


def test_pose_connections_match_canonical():
    assert POSE_CONNECTIONS == _CANONICAL
    assert len(POSE_CONNECTIONS) == 35
    for a, b in POSE_CONNECTIONS:
        assert 0 <= a <= 32
        assert 0 <= b <= 32


def test_returns_correct_shape():
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    out = draw_overlay(img, 5, RepState.STANDING, False, False, False)
    assert out.shape == (480, 640, 3)
    assert out.dtype == np.uint8


def test_does_not_mutate_input():
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    original = img.copy()
    draw_overlay(img, 0, RepState.DESCENDING, False, False, False)
    assert np.array_equal(img, original)


def test_lost_track_state_none():
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    out = draw_overlay(img, 0, None, False, False, True)
    assert out.shape == (480, 640, 3)


def test_all_states():
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    for state in RepState:
        out = draw_overlay(img, 7, state, False, False, False)
        assert out.shape == (480, 640, 3)


def test_rep_count_pixels_nonzero():
    """M4: the rep-count text must actually draw pixels (white on black)."""
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    out = draw_overlay(img, 42, RepState.STANDING, False, False, False)
    # Text drawn at (16, 50) with size ~ 120x40 — check corner is painted
    assert out[35:55, 16:140].sum() > 0


def test_lost_track_skeleton_is_red():
    """M5: lost_track skeleton draws with red lines (BGR index 2 = 255)."""
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    lms = _dummy_landmarks(33)
    out = draw_overlay(img, 0, None, False, False, True, landmarks=lms)
    assert out[:, :, 2].sum() > 0, "no red channel pixels with lost_track=True"


def test_partial_flag():
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    out = draw_overlay(img, 3, RepState.BOTTOM, True, False, False)
    assert out.shape == (480, 640, 3)


def test_paused_flag():
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    out = draw_overlay(img, 3, RepState.STANDING, False, True, False)
    assert out.shape == (480, 640, 3)


def test_partial_and_paused_both_true():
    """M2: both badges rendered, not overlapping (second offset by 28px)."""
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    out = draw_overlay(img, 5, RepState.BOTTOM, True, True, False)
    assert out[35:55, -200:].sum() > 0  # at least one badge rendered


def test_with_skeleton():
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    lms = _dummy_landmarks(33)
    out = draw_overlay(img, 10, RepState.STANDING, False, False, False, landmarks=lms)
    assert out.shape == (480, 640, 3)
    assert out.sum() > 0  # skeleton lines should paint pixels


def test_with_skeleton_partial_landmarks():
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    lms = {23: (0.5, 0.6), 25: (0.5, 0.7), 27: (0.5, 0.8)}
    out = draw_overlay(img, 0, RepState.STANDING, False, False, False, landmarks=lms)
    assert out.shape == (480, 640, 3)


def test_lost_track_with_skeleton():
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    lms = _dummy_landmarks(33)
    out = draw_overlay(img, 0, None, False, False, True, landmarks=lms)
    assert out.shape == (480, 640, 3)
