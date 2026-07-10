# Squat Rep Counter

Real-time squat repetition counter using [MediaPipe Tasks Vision
PoseLandmarker](https://ai.google.dev/edge/mediapipe/solutions/vision/pose_landmarker).
Built for research-grade exercise monitoring — records frame-by-frame data for offline
analysis.

**v0.1.0** · MIT License

---

## Features

- **Real-time webcam counting** — pose runs in the browser (MediaPipe JS); the server
  counts from landmarks over a WebSocket. Native camera permission prompt + device
  picker (works with DroidCam/OBS virtual cams). See ADR-0008.
- **Offline video processing** — upload a recorded video, decoded and processed
  server-side, and get session data
- **Research audit trail** — every session saves `frames.csv` (per-frame angle/visibility/state),
  `reps.csv` (rep events), and `summary.json`
- **Robust to real-world conditions** — hysteresis gating prevents double-counting,
  visibility gating pauses on dropout, automatic calibration from standing frames
- **Pure counting FSM** — fully tested, no frame dependencies, headless-testable

---

## Quickstart

### Zero-dependency — from a completely clean machine

```powershell
cd mediapipe-repcounter
irm https://astral.sh/uv/install.ps1 | iex
uv venv
uv pip install -r requirements.txt
uv run python scripts/fetch_model.py
uv run python scripts/fetch_web_assets.py
```

Or as a single line:

```powershell
cd mediapipe-repcounter; irm https://astral.sh/uv/install.ps1 | iex; uv venv; uv pip install -r requirements.txt; uv run python scripts/fetch_model.py; uv run python scripts/fetch_web_assets.py
```

> `fetch_web_assets.py` self-hosts the MediaPipe JS/WASM runtime used by the live-webcam
> page (browser-side pose). `scripts/install.py` runs this step automatically.

### If you already have Python

```powershell
python scripts/install.py
```

The install script detects what's already present and skips completed steps.
It prefers `uv` when available, otherwise falls back to `venv` + `pip`.

### Run

```powershell
uv run python scripts/serve.py
```

Or (if you used the stdlib fallback):

```powershell
.venv\Scripts\python scripts\serve.py
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000) to start counting.

---

## Batch processing (many videos → one CSV)

Process a whole folder of videos headless (no window, no streaming) into a
single analysis-ready CSV — **one summary row per video**:

```powershell
# Simplest: drop videos into the videos/ folder, then just run:
python scripts/batch.py                       # scans videos/ -> dataset.csv
python scripts/batch.py --workers 4           # same, in parallel
python scripts/batch.py --recursive --workers 4   # include subfolders

# Or point anywhere explicitly (overrides the default folder):
python scripts/batch.py --dir D:\dataset\squats --recursive --out dataset.csv --workers 4
python scripts/batch.py a.mp4 b.mp4 c.mp4 --out dataset.csv
```

With no arguments the tool scans the conventional `videos/` folder (created on
first run) and writes `dataset.csv`. `--dir`, globs, and explicit file lists
override it.

Options: `--workers N` (parallel processes, ~N× faster), `--per-video` (also
write raw `frames.csv`/`events.csv` per video), `--standing-angle X` (override
auto-calibration), `--recursive`.

Output columns (`video` + `path` are stable join keys for pairing with an
external label sheet):

```
video, path, status, frames, pose_frames, duration_sec, fps,
calibration_angle, total_reps, full_reps, partial_reps, paused_frames,
mean_depth_angle, min_depth_angle, error
```

`status` is one of `ok` / `uncalibrated` / `no_pose` / `error`, so rows that did
not calibrate, detected no pose, or failed to decode are flagged explicitly
(never a silent `0` reps). Filter to `status == ok` before computing accuracy.

`full_reps` = credited reps that went **below parallel** (`< ~90°`);
`partial_reps` = `total_reps − full_reps` (credited reps that reached parallel but
not below it). See `docs/adr/0009-batch-output-schema.md` for the full column
contract and the `status` state machine.

---

## Web Dashboard

| Page | Endpoint | Description |
|---|---|---|
| Home | `/` | Start webcam or upload video |
| Live watch | `/watch?source=webcam` | Browser-side pose + real-time rep/angle/state |
| Session watch | `/watch?session=<id>` | Watch a recorded session in progress |
| Sessions | `/sessions` | Browse/download past sessions |

Each session produces:
- `frames.csv` — one row per frame: timestamp, angle, visibility, state, rep_count, paused, partial, lost_track, uncalibrated
- `reps.csv` — one row per rep: rep_index, depth_angle, is_full, partial
- `summary.json` — session metadata (duration, FPS, total/full/partial reps)

### API Endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/upload` | Upload video for processing (multipart) |
| GET | `/video/{id}` | MJPEG stream for a session |
| WS | `/ws/{id}` | WebSocket — real-time frame data |
| POST | `/session/{id}/stop` | Stop session, save data |
| GET | `/session/{id}/download?format=csv\|json` | Download session data |

---

## Scripts

| Script | Description |
|---|---|
| `scripts/run.py` | Desktop app (OpenCV window) — webcam or video file |
| `scripts/batch.py` | Headless batch: many videos → one summary CSV (one row/video) |
| `scripts/serve.py` | Web dashboard (FastAPI + uvicorn) |
| `scripts/install.py` | One-shot installer — venv, deps, model download (idempotent) |
| `scripts/fetch_model.py` | Download `pose_landmarker_full.task` |
| `scripts/fetch_web_assets.py` | Self-host MediaPipe JS/WASM for the live-webcam page |
| `scripts/fetch_test_clip.py` | Download test fixture video |
| `scripts/extract_frames.py` | Extract frames from a video file |

---

## Architecture

```
Capture ──frames──▶ Detect ──landmarks──▶ Features ──angle──▶ Count ──events──▶ Present
(adapter)            (adapter)              (pure)                (pure, FSM)      (overlay)
```

- **Capture** — webcam or video file (`src/repcounter/capture/`)
- **Detect** — MediaPipe PoseLandmarker wrapper (`src/repcounter/detect/`)
- **Features** — hip–knee–ankle angle, leg averaging, EMA smoothing (`src/repcounter/features/`)
- **Count** — hysteresis FSM, visibility gating, auto-calibration (`src/repcounter/count/`)
- **Present** — OpenCV overlay with skeleton, count, state badges (`src/repcounter/present/`)
- **Server** — FastAPI dashboard with session recording (`src/repcounter/server/`)

Key design decisions are recorded in `docs/adr/` (7 ADRs) and the architecture is detailed in
`docs/design/architecture.md`.

---

## Tests

```bash
python -m pytest
```

92 tests, all pass. The counting FSM (`test_count.py`) has 19 tests covering:
hysteresis, dropout recovery, partial reps, auto-calibration, oscillation damping, and
boundary conditions. All modules are tested through their public interfaces.

---

## Data format

### frames.csv

```
timestamp,angle,visibility,state,rep_count,paused,partial,lost_track,uncalibrated
```
- `angle` — interior hip–knee–ankle angle (°), `NaN` when lost track
- `state` — one of `standing`, `descending`, `bottom`, `ascending`
- `paused` / `partial` / `lost_track` / `uncalibrated` — boolean flags

### summary.json

```json
{
  "id": "uuid",
  "label": "my_condition",
  "source": "webcam",
  "start_time": "2026-07-09T12:00:00",
  "duration_sec": 120.5,
  "fps": 29.7,
  "total_reps": 15,
  "full_reps": 13,
  "partial_reps": 2,
  "total_frames": 3570
}
```

---

## Research context

Built following evaluation methodology from Oliosi et al. 2026 (JMIR mHealth,
doi:10.2196/82412) and arXiv:2005.03194. See `docs/research/squat-rep-counting.md` for
the full survey and `docs/adr/` for architectural decisions.

---

## License

MIT © 2026 Dimas Edra Ar Rafi
