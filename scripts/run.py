"""Real-time squat repetition counter.

Usage:
    python scripts/run.py                         # live webcam
    python scripts/run.py --source path/to/vid.mp4 # recorded video
    python scripts/run.py --source 1               # second camera
"""
from __future__ import annotations

import argparse
from pathlib import Path

import cv2

from repcounter.capture import VideoFileCapture, WebcamCapture
from repcounter.count import RepCounter
from repcounter.detect import PoseLandmarkerDetector
from repcounter.features import FeatureExtractor
from repcounter.present import draw_overlay

MODEL = Path(__file__).resolve().parent.parent / "models" / "pose_landmarker_full.task"


def _make_capture(source: str) -> WebcamCapture | VideoFileCapture:
    if Path(source).exists():
        try:
            return VideoFileCapture(source)
        except ValueError as exc:
            raise SystemExit(str(exc))
    try:
        cam_id = int(source)
    except ValueError:
        raise SystemExit(f"invalid source: {source!r} (expected camera index or file path)")
    return WebcamCapture(cam_id)


def main() -> None:
    parser = argparse.ArgumentParser(description="Real-time squat repetition counter")
    parser.add_argument("--source", default="0", help="Camera index or video file path")
    parser.add_argument("--model", default=str(MODEL), help="Path to pose_landmarker_full.task")
    args = parser.parse_args()

    if not Path(args.model).exists():
        raise SystemExit(f"Model not found: {args.model}\nRun: python scripts/fetch_model.py")

    window = "Squat Rep Counter"
    cv2.namedWindow(window, cv2.WINDOW_NORMAL)

    with _make_capture(args.source) as cap, PoseLandmarkerDetector(args.model) as det:
        fe = FeatureExtractor()
        counter = RepCounter()

        try:
            for frame in cap:
                pose = det.detect(frame.image, timestamp=frame.timestamp)
                landmarks = (
                    {k: (v.x, v.y) for k, v in pose.landmarks.items()}
                    if pose else None
                )

                if pose is None:
                    vis = draw_overlay(
                        frame.image, counter.rep_count, None,
                        counter.partial, counter.paused,
                        lost_track=True, landmarks=None,
                    )
                else:
                    feat = fe.update(pose)
                    step = counter.update(feat.angle, visibility=feat.visibility)
                    vis = draw_overlay(
                        frame.image, step.rep_count, step.state,
                        step.partial, step.paused,
                        lost_track=False, landmarks=landmarks,
                    )

                cv2.imshow(window, vis)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
        except KeyboardInterrupt:
            pass

        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
