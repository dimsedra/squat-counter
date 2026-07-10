"""Batch-process many videos into one analysis-ready CSV (one row per video).

Headless: no window, no streaming. Each video runs through the same
Detect -> Features -> Count chain; only the aggregate summary is written.

Usage:
    python scripts/batch.py --dir videos/ --out dataset.csv
    python scripts/batch.py --dir videos/ --recursive --out dataset.csv
    python scripts/batch.py a.mp4 b.mp4 c.mp4 --out dataset.csv --workers 4
    python scripts/batch.py --dir videos/ --per-video      # also write raw CSVs
    python scripts/batch.py --dir videos/ --standing-angle 170

Output columns (video + path are the join keys for external label sheets):
    video, path, status, frames, pose_frames, duration_sec, fps,
    calibration_angle, total_reps, full_reps, partial_reps, paused_frames,
    mean_depth_angle, min_depth_angle, error
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from repcounter.batch import (  # noqa: E402
    VIDEO_EXTENSIONS,
    VideoResult,
    discover_videos,
    run_batch,
    write_summary_csv,
)
from repcounter.count import RepCounter  # noqa: E402

MODEL = Path(__file__).resolve().parent.parent / "models" / "pose_landmarker_full.task"
# Convention: bare `python scripts/batch.py` scans this folder.
DEFAULT_INPUT_DIR = Path(__file__).resolve().parent.parent / "videos"


def _print_result(r: VideoResult, elapsed: float | None = None) -> None:
    extra = f" reps={r.total_reps}" if r.status in ("ok", "uncalibrated") else ""
    err = f" -- {r.error}" if r.error else ""
    t = f" ({elapsed:.1f}s)" if elapsed is not None else ""
    print(f"  [{r.status:>12}] {r.video}{extra}{t}{err}", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Batch squat-rep video processor")
    parser.add_argument("inputs", nargs="*", help="Video files (and/or use --dir)")
    parser.add_argument("--dir", action="append", default=[], help="Directory of videos (repeatable)")
    parser.add_argument("--recursive", action="store_true", help="Recurse into subdirectories of --dir")
    parser.add_argument("--out", default="dataset.csv", help="Output CSV path (default: dataset.csv)")
    parser.add_argument("--model", default=str(MODEL), help="Path to pose_landmarker_full.task")
    parser.add_argument(
        "--workers", type=int, default=1,
        help="Parallel worker processes (default: 1). Auto-capped to CPU cores "
             "and to the number of videos. Best value ~ physical core count; "
             "each worker loads its own model (more RAM), and MediaPipe is "
             "already multi-threaded so oversubscribing rarely helps.",
    )
    parser.add_argument("--per-video", action="store_true", help="Also write per-video frames.csv/events.csv")
    parser.add_argument("--standing-angle", type=float, default=None, help="Override auto-calibration standing angle")
    args = parser.parse_args()

    if not Path(args.model).exists():
        raise SystemExit(f"Model not found: {args.model}\nRun: python scripts/fetch_model.py")

    # Validate a global --standing-angle once, up front, so a config typo fails
    # loudly instead of turning every video into a status=error row.
    if args.standing_angle is not None:
        try:
            RepCounter(standing_angle=args.standing_angle)
        except ValueError as exc:
            raise SystemExit(f"Invalid --standing-angle {args.standing_angle}: {exc}")

    # Warn about explicitly-listed files with an unsupported extension (they will
    # still be attempted and reported as status=error, but flag the likely typo).
    for f in args.inputs:
        p = Path(f)
        if p.is_file() and p.suffix.lower() not in VIDEO_EXTENSIONS:
            print(f"  [warn] {p.name}: unsupported extension (supported: "
                  f"{', '.join(sorted(VIDEO_EXTENSIONS))})")

    sources = list(args.inputs) + list(args.dir)
    if not sources:
        # No explicit input: fall back to the conventional videos/ folder.
        DEFAULT_INPUT_DIR.mkdir(parents=True, exist_ok=True)
        sources = [DEFAULT_INPUT_DIR]
        print(f"No inputs given; scanning default folder: {DEFAULT_INPUT_DIR}")

    videos = discover_videos(sources, recursive=args.recursive)
    if not videos:
        raise SystemExit(
            "No videos found (supported: .mp4 .avi .mov .mkv).\n"
            f"Put video files in {DEFAULT_INPUT_DIR} (or use --dir DIR / list files), "
            "then re-run. Add --recursive to include subfolders."
        )

    # Clamp workers to something sane for this machine + workload.
    cpu = os.cpu_count() or 1
    workers = max(1, args.workers)
    if args.workers > cpu:
        print(
            f"  [warn] --workers {args.workers} exceeds {cpu} CPU core(s); "
            "MediaPipe is already multi-threaded, so extra workers oversubscribe "
            f"the CPU and rarely help. Capping to {cpu}."
        )
        workers = cpu
    # No benefit from more workers than videos.
    if workers > len(videos):
        print(f"  [info] only {len(videos)} video(s); using {len(videos)} worker(s).")
        workers = len(videos)

    print(f"Processing {len(videos)} video(s) with {workers} worker(s) ...")
    t_all = time.monotonic()

    results = run_batch(
        videos, args.model,
        workers=workers, per_video=args.per_video,
        standing_angle=args.standing_angle, on_result=_print_result,
    )

    out = write_summary_csv(results, args.out)

    ok = sum(1 for r in results if r.status == "ok")
    unc = sum(1 for r in results if r.status == "uncalibrated")
    nop = sum(1 for r in results if r.status == "no_pose")
    err = sum(1 for r in results if r.status == "error")
    print(
        f"\nDone in {time.monotonic() - t_all:.1f}s -> {out}\n"
        f"  ok={ok}  uncalibrated={unc}  no_pose={nop}  error={err}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
