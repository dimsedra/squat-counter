"""One-shot project installer. Idempotent — safe to re-run.

Detects existing tools and skips completed steps. Uses only the stdlib.
Prefers `uv` when available (fast); falls back to `venv` + `pip`.

Usage:
    python scripts/install.py
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
REQUIREMENTS = PROJECT / "requirements.txt"
MODEL_SCRIPT = PROJECT / "scripts" / "fetch_model.py"
WEB_ASSETS_SCRIPT = PROJECT / "scripts" / "fetch_web_assets.py"
VENV_DIR = PROJECT / ".venv"


def _info(msg: str) -> None:
    print(f"  [..] {msg}")


def _warn(msg: str) -> None:
    print(f"  [!] {msg}")


def _ok(msg: str) -> None:
    print(f"  [OK] {msg}")


def _skip(msg: str) -> None:
    print(f"  [--] {msg}")


def _run(*args: str, cwd: str | None = None) -> bool:
    return subprocess.run(args, cwd=cwd or str(PROJECT)).returncode == 0


def _run_venv(*args: str) -> bool:
    if sys.platform == "win32":
        bin_dir = VENV_DIR / "Scripts"
    else:
        bin_dir = VENV_DIR / "bin"
    exe = bin_dir / args[0]
    return subprocess.run([str(exe), *args[1:]], cwd=str(PROJECT)).returncode == 0


# ── Step: Python version ──────────────────────────────────────────────────

def _check_python() -> str:
    v = sys.version_info
    if v.major < 3 or (v.major == 3 and v.minor < 10):
        print(f"  [FAIL] Python >= 3.10 required, found {v.major}.{v.minor}.{v.micro}")
        print("  [FAIL] Install Python 3.11+ and re-run.")
        sys.exit(1)
    return f"{v.major}.{v.minor}.{v.micro}"


# ── Step: uv availability ─────────────────────────────────────────────────

def _has_uv() -> bool:
    return shutil.which("uv") is not None


def _install_uv() -> bool:
    _info("installing uv (Rust-based Python package manager) ...")
    if sys.platform == "win32":
        # PowerShell one-liner to install uv
        ps = (
            '[Net.ServicePointManager]::SecurityProtocol = '
            "'Tls12,Tls11,Tls'; "
            "irm https://astral.sh/uv/install.ps1 | iex"
        )
        return subprocess.run(["powershell", "-Command", ps]).returncode == 0
    else:
        return _run("curl", "-LsSf", "https://astral.sh/uv/install.sh")


# ── Step: venv ────────────────────────────────────────────────────────────

_UV_VENV_EXISTS = VENV_DIR.exists() and (VENV_DIR / "pyvenv.cfg").exists()


def _ensure_venv_uv() -> None:
    if _UV_VENV_EXISTS:
        _skip("venv already exists (.venv/)")
        return
    if _run("uv", "venv"):
        _ok("venv created via uv (.venv/)")
    else:
        _warn("uv venv failed, falling back to stdlib venv ...")
        _ensure_venv_stdlib()


def _ensure_venv_stdlib() -> None:
    if _UV_VENV_EXISTS:
        _skip("venv already exists (.venv/)")
        return
    import venv

    venv.create(str(VENV_DIR), with_pip=True)
    _ok("venv created via stdlib (.venv/)")


def _ensure_venv() -> None:
    if not _has_uv():
        _ensure_venv_stdlib()
    else:
        _ensure_venv_uv()


# ── Step: install dependencies ────────────────────────────────────────────

def _install_deps_uv() -> bool:
    _info("installing dependencies (uv) ...")
    return _run("uv", "pip", "install", "-r", str(REQUIREMENTS))


def _install_deps_pip() -> bool:
    _info("installing dependencies (pip) ...")
    pip = str(VENV_DIR / "Scripts" / "pip.exe") if sys.platform == "win32" else str(VENV_DIR / "bin" / "pip")
    pip3 = str(VENV_DIR / "Scripts" / "pip3.exe") if sys.platform == "win32" else str(VENV_DIR / "bin" / "pip3")
    exe = pip if os.path.exists(pip) else pip3
    return subprocess.run([exe, "install", "-r", str(REQUIREMENTS)]).returncode == 0


def _install_deps() -> None:
    ok = _install_deps_uv() if _has_uv() else _install_deps_pip()
    if ok:
        _ok("dependencies installed")
    else:
        print("  [FAIL] Failed to install dependencies.")
        sys.exit(1)


# ── Step: download model ──────────────────────────────────────────────────

MODEL_FILE = PROJECT / "models" / "pose_landmarker_full.task"


def _download_model() -> None:
    if MODEL_FILE.exists():
        _skip("model already downloaded")
        return
    _info("downloading MediaPipe pose model (~11 MB) ...")
    if _has_uv():
        ok = _run("uv", "run", "python", str(MODEL_SCRIPT))
    else:
        ok = _run_venv("python", str(MODEL_SCRIPT))
    if ok:
        _ok("model downloaded")
    else:
        print("  [FAIL] Failed to download model.")
        sys.exit(1)


# ── Step: download web assets (MediaPipe JS/WASM, self-hosted) ─────────────

WEB_ASSET_MARKER = (
    PROJECT / "src" / "repcounter" / "server" / "static" / "vision" / "vision_bundle.mjs"
)


def _download_web_assets() -> None:
    if WEB_ASSET_MARKER.exists():
        _skip("web assets already downloaded")
        return
    _info("downloading MediaPipe web assets (JS + WASM, ~22 MB) ...")
    if _has_uv():
        ok = _run("uv", "run", "python", str(WEB_ASSETS_SCRIPT))
    else:
        ok = _run_venv("python", str(WEB_ASSETS_SCRIPT))
    if ok:
        _ok("web assets downloaded")
    else:
        _warn("failed to download web assets (live webcam page needs them)")


# ── Main ──────────────────────────────────────────────────────────────────

def main() -> None:
    print("========== Squat Rep Counter -- Install ==========")

    pyver = _check_python()
    _ok(f"Python {pyver}")

    if _has_uv():
        _ok("uv detected")
    else:
        _warn("uv not found -- will use stdlib venv + pip")
        _warn("recommended: install uv for faster future installs")
        if not _install_uv():
            _warn("uv install skipped or failed (continuing with stdlib)")

    _ensure_venv()
    _install_deps()
    _download_model()
    _download_web_assets()

    run_cmd = "uv run python scripts/serve.py" if _has_uv() else ".venv\\Scripts\\python scripts\\serve.py"
    print("\n==================== Done ====================")
    print(f"\n  Run the dashboard:\n")
    print(f"    cd {PROJECT.name}")
    print(f"    {run_cmd}")
    print(f"\n  Or run the desktop app:\n")
    print(f"    {run_cmd.replace('serve.py', 'run.py')}")


if __name__ == "__main__":
    main()
