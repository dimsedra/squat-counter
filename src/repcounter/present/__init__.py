"""Present seam: draw count / rep-state / warnings overlay on a frame (OpenCV).

UI-only; implemented in M5.
"""
from __future__ import annotations


def draw_overlay(image, rep_count: int, state, partial: bool, paused: bool, lost_track: bool):
    raise NotImplementedError
