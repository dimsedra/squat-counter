from __future__ import annotations

import math
import statistics

from repcounter.types import CountStep, RepEvent, RepState


class RepCounter:
    _PROVISIONAL_STANDING_MIN = 120.0

    def __init__(
        self,
        *,
        standing_angle: float | None = None,
        depth_threshold: float = 100.0,
        full_threshold: float = 90.0,
        standing_margin: float = 10.0,
        entry_hysteresis: float = 5.0,
        bottom_hysteresis: float = 5.0,
        visibility_threshold: float = 0.5,
        visibility_hysteresis: float = 0.1,
        calibration_samples: int = 5,
        provisional_standing_min: float | None = None,
    ) -> None:
        self.depth_threshold = depth_threshold
        self.full_threshold = full_threshold
        self.standing_margin = standing_margin
        self.entry_hysteresis = entry_hysteresis
        self.bottom_hysteresis = bottom_hysteresis
        self.visibility_threshold = visibility_threshold
        self.visibility_hysteresis = visibility_hysteresis
        self.calibration_samples = calibration_samples
        self.provisional_standing_min = (
            provisional_standing_min
            if provisional_standing_min is not None
            else self.depth_threshold + self.standing_margin + 5.0
        )

        if standing_angle is not None:
            self._validate_standing(standing_angle)
        self._standing_angle = standing_angle

        self._state = RepState.STANDING
        self._rep_count = 0
        self._partial = False
        self._min_angle: float | None = None
        self._paused = False
        self._standing_samples: list[float] = []

    def _validate_standing(self, standing_angle: float) -> None:
        if not (self.depth_threshold + self.standing_margin < standing_angle <= 180.0):
            raise ValueError(
                f"standing_angle must be > depth_threshold+standing_margin "
                f"({self.depth_threshold + self.standing_margin}); got {standing_angle}"
            )

    def _is_valid_standing(self, angle: float) -> bool:
        return self.depth_threshold + self.standing_margin < angle <= 180.0

    @property
    def uncalibrated(self) -> bool:
        return self._standing_angle is None

    @property
    def _standing_exit(self) -> float:
        return self._standing_angle - self.standing_margin

    def calibrate(self, standing_angle: float) -> None:
        self._validate_standing(standing_angle)
        if self._state is not RepState.STANDING:
            return
        self._standing_angle = standing_angle
        self._min_angle = None
        self._standing_samples = []

    def _angle_valid(self, angle: float) -> bool:
        return math.isfinite(angle) and 0.0 <= angle <= 180.0

    def _ensure_calibrated(self, angle: float, visibility: float) -> bool:
        if self._standing_angle is not None:
            return True
        if (
            visibility >= self.visibility_threshold
            and self._is_valid_standing(angle)
            and angle >= self.provisional_standing_min
        ):
            self._standing_samples.append(angle)
            if len(self._standing_samples) >= self.calibration_samples:
                self._standing_angle = statistics.median(self._standing_samples)
        return self._standing_angle is not None

    def _should_pause(self, visibility: float) -> bool:
        if self._paused:
            if visibility >= self.visibility_threshold + self.visibility_hysteresis:
                self._paused = False
        else:
            if visibility <= self.visibility_threshold:
                self._paused = True
        return self._paused

    def _frozen_step(self, paused: bool) -> CountStep:
        return CountStep(
            state=self._state,
            rep_count=self._rep_count,
            rep_event=None,
            partial=self._partial,
            paused=paused,
            uncalibrated=self.uncalibrated,
        )

    def update(self, angle: float, visibility: float = 1.0) -> CountStep:
        if not self._angle_valid(angle):
            return self._frozen_step(paused=True)
        if not self._ensure_calibrated(angle, visibility):
            return CountStep(
                state=RepState.STANDING,
                rep_count=0,
                rep_event=None,
                partial=False,
                paused=False,
                uncalibrated=True,
            )
        if self._should_pause(visibility):
            return self._frozen_step(paused=True)

        if self._state is RepState.STANDING:
            if angle < self._standing_exit - self.entry_hysteresis:
                self._state = RepState.DESCENDING
                self._partial = False
        elif self._state is RepState.DESCENDING:
            if angle <= self.depth_threshold:
                self._state = RepState.BOTTOM
                self._min_angle = angle
            elif angle >= self._standing_exit:
                self._state = RepState.STANDING
                self._partial = True
        elif self._state is RepState.BOTTOM:
            if self._min_angle is None or angle < self._min_angle:
                self._min_angle = angle
            if angle >= self.depth_threshold + self.bottom_hysteresis:
                self._state = RepState.ASCENDING
        elif self._state is RepState.ASCENDING:
            if angle <= self.depth_threshold:
                self._state = RepState.BOTTOM
            elif angle >= self._standing_exit:
                self._rep_count += 1
                event = RepEvent(
                    rep_index=self._rep_count,
                    depth_angle=self._min_angle if self._min_angle is not None else 0.0,
                    is_full=(self._min_angle is not None and self._min_angle < self.full_threshold),
                )
                self._state = RepState.STANDING
                self._partial = False
                self._min_angle = None
                return CountStep(
                    state=self._state,
                    rep_count=self._rep_count,
                    rep_event=event,
                    partial=self._partial,
                    paused=False,
                    uncalibrated=False,
                )

        return CountStep(
            state=self._state,
            rep_count=self._rep_count,
            rep_event=None,
            partial=self._partial,
            paused=False,
            uncalibrated=False,
        )
