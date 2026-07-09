"""MediaPipe Tasks Vision PoseLandmarker adapter (ADR-0004).

Wraps ``pose_landmarker_full`` in IMAGE running mode: each frame is processed
independently (no temporal state in the detector; M4 decision). Converts an
OpenCV BGR frame into a ``PoseFrame`` with 33 image landmarks (x, y,
visibility) plus world landmarks (x, y; z ignored per ADR-0007-A). Returns
``None`` when no person is detected.
"""
from __future__ import annotations

import time
from pathlib import Path

import mediapipe as mp
import numpy as np

from repcounter.types import Landmark, PoseFrame

_MP_VISION = mp.tasks.vision
_RunningMode = _MP_VISION.RunningMode
_BaseOptions = mp.tasks.BaseOptions


class PoseLandmarkerDetector:
    def __init__(self, model_path: str | Path, *, num_poses: int = 1) -> None:
        self._model_path = str(model_path)
        options = _MP_VISION.PoseLandmarkerOptions(
            base_options=_BaseOptions(model_asset_path=self._model_path),
            running_mode=_RunningMode.IMAGE,
            num_poses=num_poses,
        )
        self._detector = _MP_VISION.PoseLandmarker.create_from_options(options)

    @staticmethod
    def _to_pose_frame(result, timestamp: float = 0.0) -> PoseFrame | None:
        if not result.pose_landmarks or not result.pose_landmarks[0]:
            return None
        landmarks: dict[int, Landmark] = {}
        for idx, lm in enumerate(result.pose_landmarks[0]):
            landmarks[idx] = Landmark(
                x=float(lm.x),
                y=float(lm.y),
                visibility=max(0.0, min(1.0, float(lm.visibility or 0.0))),
            )
        world_landmarks: dict[int, Landmark] | None = None
        if result.pose_world_landmarks and result.pose_world_landmarks[0]:
            world_landmarks = {}
            for idx, lm in enumerate(result.pose_world_landmarks[0]):
                vis = lm.visibility if lm.visibility is not None else lm.presence
                world_landmarks[idx] = Landmark(
                    x=float(lm.x),
                    y=float(lm.y),
                    visibility=max(0.0, min(1.0, float(vis))) if vis is not None else 1.0,
                )
        return PoseFrame(
            landmarks=landmarks,
            timestamp=timestamp,
            world_landmarks=world_landmarks,
        )

    def detect(self, image: np.ndarray, timestamp: float | None = None) -> PoseFrame | None:
        if image is None or image.size == 0:
            return None
        if image.ndim != 3 or image.shape[2] != 3:
            raise ValueError(
                f"expected HxWx3 BGR uint8, got shape {image.shape}"
            )
        try:
            rgb = np.ascontiguousarray(image[:, :, ::-1])
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            result = self._detector.detect(mp_image)
        except Exception:
            return None
        t = timestamp if timestamp is not None else time.time()
        return self._to_pose_frame(result, timestamp=t)
