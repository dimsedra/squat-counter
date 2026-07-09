from __future__ import annotations

import math

from repcounter.types import Features, Landmark, PoseFrame

LEFT_LEG = (23, 25, 27)
RIGHT_LEG = (24, 26, 28)


def interior_angle(a: Landmark, b: Landmark, c: Landmark) -> float | None:
    ux, uy = a.x - b.x, a.y - b.y
    vx, vy = c.x - b.x, c.y - b.y
    mag_u = math.hypot(ux, uy)
    mag_v = math.hypot(vx, vy)
    if mag_u == 0.0 or mag_v == 0.0:
        return None
    cos = (ux * vx + uy * vy) / (mag_u * mag_v)
    cos = max(-1.0, min(1.0, cos))
    return math.degrees(math.acos(cos))


class FeatureExtractor:
    """Extracts the squat signal (interior hip-knee-ankle angle + visibility) from a PoseFrame.

    Design (ADR-0007 A/B/D):
    - Angle is computed from 2D coordinates, PREFERING MediaPipe world-landmark x/y
      (metric, viewpoint-stable -- research sec.6, ADR-0004) and falling back to image
      x/y when world landmarks are absent. The z (depth) channel is always ignored.
    - Per leg: use the higher-visibility leg; average the two only when BOTH are usable
      AND their angles agree (variance reduction, gated to avoid fusing a misdetect).
    - EMA smoothing kills small jitter; large real movements pass through unchanged so a
      brief squat bottom is not smoothed past the depth threshold (anti-undercount).
    - If neither leg is usable, angle=None and visibility=0 (Count then pauses).

    Tunables (ema_alpha, jitter_threshold, visibility thresholds, leg-agreement/switch
    margins) are empirically-tuned HEURISTICS -- calibrate them against MoCap-labelled
    squats (Dill et al., research sec.5.2) before claiming viewpoint-robustness.
    """

    def __init__(
        self,
        *,
        ema_alpha: float = 0.5,
        confident_visibility: float = 0.5,
        min_landmark_visibility: float = 0.5,
        jitter_threshold: float = 10.0,
        max_leg_disagreement: float = 25.0,
        leg_switch_margin: float = 0.15,
    ) -> None:
        self.ema_alpha = ema_alpha
        self.confident_visibility = confident_visibility
        self.min_landmark_visibility = min_landmark_visibility
        self.jitter_threshold = jitter_threshold
        self.max_leg_disagreement = max_leg_disagreement
        self.leg_switch_margin = leg_switch_margin
        self._smoothed: float | None = None
        self._last_leg: str | None = None

    def reset(self) -> None:
        self._smoothed = None
        self._last_leg = None

    def _landmark(self, pose: PoseFrame, idx: int) -> Landmark | None:
        world = pose.world_landmarks
        if world is not None and idx in world:
            return world[idx]
        return pose.landmarks.get(idx)

    def _leg_angle(self, pose: PoseFrame, leg: tuple[int, int, int]) -> tuple[float | None, float]:
        hip_idx, knee_idx, ankle_idx = leg
        hip = self._landmark(pose, hip_idx)
        knee = self._landmark(pose, knee_idx)
        ankle = self._landmark(pose, ankle_idx)
        if hip is None or knee is None or ankle is None:
            return None, 0.0
        if (
            hip.visibility < self.min_landmark_visibility
            or knee.visibility < self.min_landmark_visibility
            or ankle.visibility < self.min_landmark_visibility
        ):
            return None, 0.0
        angle = interior_angle(hip, knee, ankle)
        if angle is None:
            return None, 0.0
        return angle, min(hip.visibility, knee.visibility, ankle.visibility)

    def _select(self, left: tuple[float | None, float], right: tuple[float | None, float]):
        usable = []
        if left[0] is not None:
            usable.append((left[0], left[1], "L"))
        if right[0] is not None:
            usable.append((right[0], right[1], "R"))
        if not usable:
            return None, 0.0, None
        if len(usable) == 2:
            a1, v1, s1 = usable[0]
            a2, v2, s2 = usable[1]
            if abs(a1 - a2) <= self.max_leg_disagreement:
                return (a1 + a2) / 2.0, (v1 + v2) / 2.0, None
            best = max(usable, key=lambda u: u[1])
        else:
            best = usable[0]
        if self._last_leg is not None:
            last = next((u for u in usable if u[2] == self._last_leg), None)
            if last is not None and last[1] >= best[1] - self.leg_switch_margin:
                best = last
        return best[0], best[1], best[2]

    def update(self, pose: PoseFrame) -> Features:
        left = self._leg_angle(pose, LEFT_LEG)
        right = self._leg_angle(pose, RIGHT_LEG)
        angle, visibility, side = self._select(left, right)
        if angle is None:
            self._smoothed = None
            self._last_leg = None
            return Features(angle=None, visibility=0.0)
        if self._smoothed is None or abs(angle - self._smoothed) > self.jitter_threshold:
            smoothed = angle
        else:
            smoothed = self.ema_alpha * angle + (1.0 - self.ema_alpha) * self._smoothed
        self._smoothed = smoothed
        self._last_leg = side
        return Features(angle=smoothed, visibility=visibility)
