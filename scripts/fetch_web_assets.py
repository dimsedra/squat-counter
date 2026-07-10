"""Download self-hosted MediaPipe Tasks Vision web assets (ADR-0008).

Fetches the ``@mediapipe/tasks-vision`` ESM bundle + WASM runtime from jsDelivr
into ``src/repcounter/server/static/vision/`` so the live-webcam page runs fully
offline (no CDN at runtime). Idempotent and stdlib-only.
"""
from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

VERSION = "0.10.35"
BASE = f"https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@{VERSION}"

# Relative paths within the package to mirror locally.
ASSETS = [
    "vision_bundle.mjs",
    "wasm/vision_wasm_internal.js",
    "wasm/vision_wasm_internal.wasm",
    "wasm/vision_wasm_nosimd_internal.js",
    "wasm/vision_wasm_nosimd_internal.wasm",
]

TARGET_DIR = (
    Path(__file__).resolve().parent.parent
    / "src" / "repcounter" / "server" / "static" / "vision"
)


def _download(rel: str) -> bool:
    url = f"{BASE}/{rel}"
    dst = TARGET_DIR / rel
    if dst.exists() and dst.stat().st_size > 0:
        print(f"[fetch_web_assets] already present: {rel}")
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    print(f"[fetch_web_assets] downloading {rel}")
    urllib.request.urlretrieve(url, dst)
    print(f"[fetch_web_assets]   -> {dst} ({dst.stat().st_size // 1024} KB)")
    return True


def main() -> int:
    print(f"[fetch_web_assets] @mediapipe/tasks-vision@{VERSION}")
    try:
        for rel in ASSETS:
            _download(rel)
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(f"[fetch_web_assets] ERROR: {exc}\n")
        return 1
    print("[fetch_web_assets] done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
