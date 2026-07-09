"""Capture seam: yields frames from a live webcam or a recorded file (ADR-0006).

WebcamCapture and VideoFileCapture both implement the ``Capture`` Protocol.
"""
from __future__ import annotations

import queue
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Protocol, Self, runtime_checkable

# time.monotonic() is used for frame timestamps (not system clock) so that NTP
# adjustments or clock jumps cannot produce non-monotonic timestamps (M3).

import cv2
import numpy as np


@dataclass
class Frame:
    image: np.ndarray
    timestamp: float


@runtime_checkable
class Capture(Protocol):
    def __iter__(self) -> Iterator[Frame]: ...
    def __enter__(self) -> Self: ...
    def __exit__(self, *args: object) -> None: ...


class WebcamCapture:
    def __init__(self, source: int = 0, *, width: int = 1280, height: int = 720) -> None:
        self._cap = cv2.VideoCapture(source)
        if not self._cap.isOpened():
            raise ValueError(f"cannot open camera {source}")
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

    def __iter__(self) -> Iterator[Frame]:
        while True:
            ok, bgr = self._cap.read()
            if not ok:
                break
            yield Frame(image=bgr, timestamp=time.monotonic())

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> None:
        self.release()

    def release(self) -> None:
        self._cap.release()


class VideoFileCapture:
    """Yields frames from a video file.

    Some codecs (HEVC, certain iPhone recordings) can cause OpenCV's
    ``read()`` to block indefinitely on Windows. For those, pass
    ``read_timeout`` to enable a per-frame watchdog that aborts the
    read after *read_timeout* seconds. By default (None), reads are
    direct and blocking.
    """

    def __init__(self, path: str | Path, *, read_timeout: float | None = None) -> None:
        self._path = str(path)
        self._cap = cv2.VideoCapture(self._path)
        if not self._cap.isOpened():
            raise ValueError(f"cannot open video file: {self._path}")
        self._read_timeout = read_timeout

    def __iter__(self) -> Iterator[Frame]:
        while True:
            ok, bgr = self._read()
            if not ok:
                break
            yield Frame(image=bgr, timestamp=time.monotonic())

    def _read(self) -> tuple[bool, np.ndarray | None]:
        """Read one frame. If ``read_timeout`` is set, a watchdog thread
        aborts the read after the timeout."""
        if self._read_timeout is None:
            return self._cap.read()

        q: queue.Queue = queue.Queue()

        def _do_read() -> None:
            try:
                ok, bgr = self._cap.read()
                q.put((ok, bgr))
            except Exception:
                q.put((False, None))

        t = threading.Thread(target=_do_read, daemon=True)
        t.start()
        t.join(self._read_timeout)
        if t.is_alive():
            return False, None
        return q.get_nowait()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> None:
        self.release()

    @property
    def total_frames(self) -> int:
        return int(self._cap.get(cv2.CAP_PROP_FRAME_COUNT))

    @property
    def fps(self) -> float:
        return self._cap.get(cv2.CAP_PROP_FPS)

    def release(self) -> None:
        self._cap.release()


__all__ = ["Capture", "Frame", "WebcamCapture", "VideoFileCapture"]
