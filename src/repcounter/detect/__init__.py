"""Detect seam: frame -> PoseFrame via MediaPipe Tasks Vision PoseLandmarker.

Implemented in M4 (ADR-0004): wraps pose_landmarker_full, 33 landmarks,
image x/y (+ visibility); z is ignored per ADR-0007-A.
"""
from __future__ import annotations

from repcounter.types import PoseFrame


def detect(frame) -> PoseFrame | None:
    raise NotImplementedError
