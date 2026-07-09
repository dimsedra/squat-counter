from __future__ import annotations

import math

from repcounter.types import Features, Landmark, PoseFrame

LEFT_LEG = (23, 25, 27)
RIGHT_LEG = (24, 26, 28)


def interior_angle(a: Landmark, b: Landmark, c: Landmark) -> float:
    ux, uy = a.x - b.x, a.y - b.y
    vx, vy = c.x - b.x, c.y - b.y
    mag_u = math.hypot(ux, uy)
    mag_v = math.hypot(vx, vy)
    if mag_u == 0.0 or mag_v == 0.0:
        return 0.0
    cos = (ux * vx + uy * vy) / (mag_u * mag_v)
    cos = max(-1.0, min(1.0, cos))
    return math.degrees(math.acos(cos))


class FeatureExtractor:
    def __init__(
        self,
        *,
        ema_alpha: float = 0.5,
        confident_visibility: float = 0.5,
        min_landmark_visibility: float = 0.1,
    ) -> None:
        self.ema_alpha = ema_alpha
        self.confident_visibility = confident_visibility
        self.min_landmark_visibility = min_landmark_visibility
        self._smoothed: float | None = None

    def reset(self) -> None:
        self._smoothed = None

    def _leg_angle(self, pose: PoseFrame, leg: tuple[int, int, int]) -> tuple[float | None, float]:
        hip_idx, knee_idx, ankle_idx = leg
        hip = pose.landmarks.get(hip_idx)
        knee = pose.landmarks.get(knee_idx)
        ankle = pose.landmarks.get(ankle_idx)
        if hip is None or knee is None or ankle is None:
            return None, 0.0
        if (
            hip.visibility < self.min_landmark_visibility
            or knee.visibility < self.min_landmark_visibility
            or ankle.visibility < self.min_landmark_visibility
        ):
            return None, 0.0
        return interior_angle(hip, knee, ankle), min(hip.visibility, knee.visibility, ankle.visibility)

    def update(self, pose: PoseFrame) -> Features:
        angle_left, vis_left = self._leg_angle(pose, LEFT_LEG)
        angle_right, vis_right = self._leg_angle(pose, RIGHT_LEG)

        usable = [pair for pair in ((angle_left, vis_left), (angle_right, vis_right)) if pair[0] is not None]
        if not usable:
            self._smoothed = None
            return Features(angle=None, visibility=0.0)

        if len(usable) == 2 and vis_left >= self.confident_visibility and vis_right >= self.confident_visibility:
            angle = (angle_left + angle_right) / 2.0
            visibility = (vis_left + vis_right) / 2.0
        else:
            angle, visibility = max(usable, key=lambda pair: pair[1])

        if self._smoothed is None:
            self._smoothed = angle
        else:
            self._smoothed = self.ema_alpha * angle + (1.0 - self.ema_alpha) * self._smoothed
        return Features(angle=self._smoothed, visibility=visibility)
