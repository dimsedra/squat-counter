"""M5 smoke tests for the Present seam (draw_overlay).
"""
from __future__ import annotations

import numpy as np
import pytest

from repcounter.present import POSE_CONNECTIONS, draw_overlay
from repcounter.types import RepState


def _dummy_landmarks(count: int = 33) -> dict[int, tuple[float, float]]:
    return {i: (0.1 * (i % 10) / 9, 0.1 * (i // 10) / 3) for i in range(count)}


def test_returns_correct_shape():
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    out = draw_overlay(img, 5, RepState.STANDING, False, False, False)
    assert out.shape == (480, 640, 3)
    assert out.dtype == np.uint8


def test_does_not_mutate_input():
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    original = img.copy()
    draw_overlay(img, 0, RepState.DESCENDING, False, False, False)
    assert np.array_equal(img, original), "input image was mutated"


def test_lost_track_state_none():
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    out = draw_overlay(img, 0, None, False, False, True)
    assert out.shape == (480, 640, 3)


def test_all_states():
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    for state in RepState:
        out = draw_overlay(img, 7, state, False, False, False)
        assert out.shape == (480, 640, 3)


def test_partial_flag():
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    out = draw_overlay(img, 3, RepState.BOTTOM, True, False, False)
    assert out.shape == (480, 640, 3)


def test_paused_flag():
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    out = draw_overlay(img, 3, RepState.STANDING, False, True, False)
    assert out.shape == (480, 640, 3)


def test_with_skeleton():
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    lms = _dummy_landmarks(33)
    out = draw_overlay(img, 10, RepState.STANDING, False, False, False, landmarks=lms)
    assert out.shape == (480, 640, 3)


def test_with_skeleton_partial_landmarks():
    """Should not crash with fewer than 33 landmarks."""
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    lms = {23: (0.5, 0.6), 25: (0.5, 0.7), 27: (0.5, 0.8)}
    out = draw_overlay(img, 0, RepState.STANDING, False, False, False, landmarks=lms)
    assert out.shape == (480, 640, 3)


def test_lost_track_with_skeleton():
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    lms = _dummy_landmarks(33)
    out = draw_overlay(img, 0, None, False, False, True, landmarks=lms)
    assert out.shape == (480, 640, 3)


def test_pose_connections_are_valid():
    # Standard 33-landmark Pose model defines 35 connections
    assert len(POSE_CONNECTIONS) == 35
    # All indices are in range 0..32
    for a, b in POSE_CONNECTIONS:
        assert 0 <= a <= 32
        assert 0 <= b <= 32
