"""Start the Squat Rep Counter web dashboard.

Usage::

    python scripts/serve.py
    python scripts/serve.py --port 8080 --host 0.0.0.0
    python scripts/serve.py --reload  (development, auto-restart on changes)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import uvicorn

MODEL_PATH = Path(__file__).resolve().parent.parent / "models" / "pose_landmarker_full.task"


def main() -> None:
    parser = argparse.ArgumentParser(description="Squat Rep Counter — Web Dashboard")
    parser.add_argument("--host", default="127.0.0.1", help="Bind address (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Port (default: 8000)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    args = parser.parse_args()

    if not MODEL_PATH.exists():
        print(f"Model not found at {MODEL_PATH}")
        print("Run: python scripts/fetch_model.py")
        sys.exit(1)

    print(f"  Dashboard:  http://{args.host}:{args.port}")
    print(f"  Model:      {MODEL_PATH}")
    print("  Press Ctrl+C to stop.")

    uvicorn.run(
        "repcounter.server:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
