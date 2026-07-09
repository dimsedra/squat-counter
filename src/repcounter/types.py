from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class RepState(Enum):
    STANDING = "standing"
    DESCENDING = "descending"
    BOTTOM = "bottom"
    ASCENDING = "ascending"


@dataclass
class Landmark:
    x: float
    y: float
    visibility: float


@dataclass
class PoseFrame:
    landmarks: dict[int, Landmark]
    timestamp: float
    world_landmarks: dict[int, Landmark] | None = None


@dataclass
class RepEvent:
    rep_index: int
    depth_angle: float
    is_full: bool


@dataclass
class CountStep:
    state: RepState
    rep_count: int
    rep_event: RepEvent | None
    partial: bool
    paused: bool
    uncalibrated: bool = False


@dataclass
class Features:
    angle: float | None
    visibility: float
