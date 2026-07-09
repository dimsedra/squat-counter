"""Extract frames from a local video file into tests/fixtures/clip/.

Usage:
    python scripts/extract_frames.py path/to/squat.mp4 [--ground-truth N] [--step N]

Output:
    tests/fixtures/clip/*.png  (every *step*-th frame)
    tests/fixtures/manifest.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2

FIXTURES = Path(__file__).resolve().parent.parent / "tests" / "fixtures"
CLIP_DIR = FIXTURES / "clip"


def extract(
    video_path: str | Path,
    *,
    step: int = 1,
    ground_truth: int | None = None,
) -> None:
    if step < 1:
        raise ValueError(f"--step must be >= 1, got {step}")

    video_path = Path(video_path)
    if not video_path.exists():
        raise FileNotFoundError(f"{video_path} not found")

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise ValueError(f"cannot open video file: {video_path}")

    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_to_save = (frame_count + step - 1) // step if frame_count > 0 else 0

    saved = 0
    idx = 0
    while True:
        ok, bgr = cap.read()
        if not ok:
            break
        if idx % step == 0:
            saved += 1
        idx += 1

    cap.release()

    if saved == 0:
        raise ValueError("no frames extracted — check the source video is not empty")

    # Remove old frames only after confirming new extraction will succeed
    CLIP_DIR.mkdir(parents=True, exist_ok=True)
    for old in CLIP_DIR.glob("*.png"):
        old.unlink()

    # Second pass: write frames
    cap = cv2.VideoCapture(str(video_path))
    idx = 0
    while True:
        ok, bgr = cap.read()
        if not ok:
            break
        if idx % step == 0:
            out_path = CLIP_DIR / f"frame_{idx:06d}.png"
            cv2.imwrite(str(out_path), bgr)
        idx += 1
    cap.release()

    manifest = {
        "source": str(video_path.resolve()),
        "total_frames": frame_count,
        "extracted_frames": saved,
        "step": step,
        "fps": fps,
    }
    if ground_truth is not None:
        manifest["ground_truth_count"] = ground_truth

    (FIXTURES / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n"
    )
    print(f"Extracted {saved}/{frame_count} frames  ->  {CLIP_DIR}")
    print(f"Manifest written  ->  {FIXTURES / 'manifest.json'}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract frames from a squat video for test fixtures")
    parser.add_argument("video", help="Path to the source video file")
    parser.add_argument("--ground-truth", type=int, default=None, help="Known rep count (optional)")
    parser.add_argument("--step", type=int, default=1, help="Extract every N-th frame (default: 1)")
    args = parser.parse_args()

    if args.step < 1:
        raise SystemExit(f"--step must be >= 1, got {args.step}")

    extract(args.video, step=args.step, ground_truth=args.ground_truth)


if __name__ == "__main__":
    main()
