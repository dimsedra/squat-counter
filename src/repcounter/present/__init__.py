"""Present seam: draw count / rep-state / warnings / skeleton overlay on a frame.

UI-only; tested by smoke tests that verify shape and no-crash.
"""
from __future__ import annotations

import cv2
import numpy as np

from repcounter.types import RepState

# 33-landmark pose connections for the MediaPipe Pose model.
# These are normally in ``mp.solutions.pose.POSE_CONNECTIONS`` but that API
# was removed in MediaPipe Tasks Vision (0.10.35).
POSE_CONNECTIONS: set[tuple[int, int]] = {
    # Face
    (0, 1), (1, 2), (2, 3), (3, 7),
    (0, 4), (4, 5), (5, 6), (6, 8),
    (9, 10),
    # Arms
    (11, 13), (13, 15), (15, 17), (15, 19), (15, 21), (17, 19),
    (12, 14), (14, 16), (16, 18), (16, 20), (16, 22), (18, 20),
    # Torso
    (11, 12), (11, 23), (12, 24), (23, 24),
    # Legs
    (23, 25), (25, 27), (27, 29), (29, 31), (27, 31),
    (24, 26), (26, 28), (28, 30), (30, 32), (28, 32),
}

_COLOR_LIME = (0, 255, 128)
_COLOR_WHITE = (255, 255, 255)
_COLOR_RED = (0, 0, 255)
_COLOR_YELLOW = (0, 255, 255)
_COLOR_GRAY = (128, 128, 128)
_LANDMARK_RADIUS = 3
_LINE_THICKNESS = 2


def _draw_skeleton(
    image: np.ndarray,
    landmarks: dict[int, tuple[float, float]],
    *,
    color: tuple[int, int, int] = _COLOR_LIME,
) -> None:
    h, w = image.shape[:2]
    for idx_a, idx_b in POSE_CONNECTIONS:
        if idx_a not in landmarks or idx_b not in landmarks:
            continue
        x1, y1 = int(landmarks[idx_a][0] * w), int(landmarks[idx_a][1] * h)
        x2, y2 = int(landmarks[idx_b][0] * w), int(landmarks[idx_b][1] * h)
        cv2.line(image, (x1, y1), (x2, y2), color, _LINE_THICKNESS)
    for (x, y) in landmarks.values():
        cx, cy = int(x * w), int(y * h)
        cv2.circle(image, (cx, cy), _LANDMARK_RADIUS, _COLOR_WHITE, -1)
        cv2.circle(image, (cx, cy), _LANDMARK_RADIUS, color, 1)


def draw_overlay(
    image: np.ndarray,
    rep_count: int,
    state: RepState | None,
    partial: bool,
    paused: bool,
    lost_track: bool,
    *,
    landmarks: dict[int, tuple[float, float]] | None = None,
) -> np.ndarray:
    """Return an annotated copy of *image* with overlay graphics.

    Parameters
    ----------
    image : np.ndarray
        Input BGR frame (modified copy).
    rep_count : int
        Current repetition count.
    state : RepState | None
        Current FSM state (None when lost_track).
    partial : bool
        Whether the last descent was a partial rep.
    paused : bool
        Whether the counter is paused (dropout).
    lost_track : bool
        Whether no person is currently detected.
    landmarks : dict[int, tuple[float, float]] | None
        Image-space (x, y) pairs for the 33 landmarks, normalised [0, 1].
        When provided, a skeleton is drawn.
    """
    vis = image.copy()

    if landmarks:
        color = _COLOR_RED if lost_track else _COLOR_LIME
        _draw_skeleton(vis, landmarks, color=color)

    # --- Text overlays ---
    font = cv2.FONT_HERSHEY_SIMPLEX
    h, w = vis.shape[:2]

    # Rep count (top-left, large)
    cv2.putText(vis, f"Reps: {rep_count}", (16, 50), font, 1.5, _COLOR_WHITE, 3)

    # State label (below rep count)
    state_name = state.value if state else "—"
    cv2.putText(vis, state_name, (16, 85), font, 0.8, _COLOR_LIME, 2)

    # Partial badge
    if partial:
        label, color = "PARTIAL", _COLOR_YELLOW
        (tw, _), _ = cv2.getTextSize(label, font, 0.7, 2)
        x = w - tw - 16
        cv2.putText(vis, label, (x, 50), font, 0.7, color, 2)

    # Paused badge
    if paused:
        label, color = "PAUSED", _COLOR_YELLOW
        (tw, _), _ = cv2.getTextSize(label, font, 0.7, 2)
        x = w - tw - 16
        cv2.putText(vis, label, (x, 50), font, 0.7, color, 2)

    # Lost-track banner (centred, large)
    if lost_track:
        label = "LOST TRACK"
        (tw, th), _ = cv2.getTextSize(label, font, 1.2, 3)
        x = (w - tw) // 2
        y = h // 2 + th // 2
        cv2.putText(vis, label, (x, y), font, 1.2, _COLOR_RED, 3)

    return vis


__all__ = ["draw_overlay", "POSE_CONNECTIONS"]
