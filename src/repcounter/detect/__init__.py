"""Detect seam: frame -> PoseFrame via MediaPipe Tasks Vision PoseLandmarker.

Implemented in M4 (ADR-0004): wraps pose_landmarker_full, 33 landmarks,
image x/y (+ visibility); world-landmark x/y is also populated (z ignored,
ADR-0007-A). Runs in IMAGE mode (per-frame, no temporal smoothing).

The `Detector` Protocol is the seam's test surface: swap in a mock or a
different backend without touching Features/Count.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

import numpy as np

from repcounter.detect.pose_landmarker import PoseLandmarkerDetector
from repcounter.types import PoseFrame

__all__ = ["Detector", "PoseLandmarkerDetector"]


@runtime_checkable
class Detector(Protocol):
    """A frame-to-landmarks adapter.

    Implementations take an OpenCV BGR frame (HxWx3 uint8) and return a
    PoseFrame, or None when no person is detected.
    """

    def detect(self, image: np.ndarray, timestamp: float | None = None) -> PoseFrame | None: ...
