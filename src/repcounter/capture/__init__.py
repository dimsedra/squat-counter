"""Capture seam: yields frames from a live webcam or a recorded file (ADR-0006).

Concrete adapters WebcamCapture and VideoFileCapture are implemented in M5.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Frame:
    image: object
    timestamp: float
