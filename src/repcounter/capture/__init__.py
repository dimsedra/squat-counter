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
    """Yields frames from a video file, with a per-frame decode timeout.

    Some codecs (HEVC, certain iPhone recordings) can cause OpenCV's
    ``read()`` to block indefinitely on Windows. A background thread with a
    timeout ensures the pipeline never hangs.
    """

    _READ_TIMEOUT: float = 5.0

    def __init__(self, path: str | Path, *, read_timeout: float | None = None) -> None:
        self._path = str(path)
        self._cap = cv2.VideoCapture(self._path)
        if not self._cap.isOpened():
            raise ValueError(f"cannot open video file: {self._path}")
        if read_timeout is not None:
            self._READ_TIMEOUT = read_timeout

    def __iter__(self) -> Iterator[Frame]:
        while True:
            ok, bgr = self._read_or_timeout()
            if not ok:
                break
            yield Frame(image=bgr, timestamp=time.monotonic())

    def _read_or_timeout(self) -> tuple[bool, np.ndarray | None]:
        """Call ``self._cap.read()`` on a separate thread with a timeout.

        Returns ``(True, frame)`` on success, ``(False, None)`` on EOF or
        when the underlying ``read()`` blocks longer than ``_READ_TIMEOUT``
        seconds (indicating a corrupt or unsupported frame).
        """
        q: queue.Queue = queue.Queue()

        def _read() -> None:
            try:
                ok, bgr = self._cap.read()
                q.put((ok, bgr))
            except Exception as exc:
                q.put((False, None))

        t = threading.Thread(target=_read, daemon=True)
        t.start()
        t.join(self._READ_TIMEOUT)

        if t.is_alive():
            # Decode hung — abandon this and subsequent frames.
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
