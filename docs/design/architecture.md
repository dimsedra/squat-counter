# Architecture & Evaluation (design reference)

Maps the runtime to clean seams and records how v1 is evaluated. All decisions are
grounded in `docs/research/squat-rep-counting.md` and the ADRs.

## Seams (deep modules)

```
Capture ──frames──▶ Detect ──landmarks──▶ Features ──angles/metrics──▶ Count ──rep events──▶ Present
 (adapter)          (adapter)              (pure)                     (pure, FSM)            (OpenCV overlay)
```

- **Capture** — frames from webcam OR recorded file (ADR-0006). Adapter.
- **Detect** — frame → 33 landmarks via Tasks Vision `PoseLandmarker` (ADR-0004). Adapter.
- **Features** — landmarks → **interior hip–knee–ankle angle from 2D coordinates,
  preferring world-landmark `x/y` (z ignored, ADR-0007-A)**, computed **per leg**, using
  the higher-visibility leg or the average when both agree (ADR-0007-B); **EMA-smoothed
  with large-movement passthrough** (ADR-0007-D); also derives visibility. **Pure.**
- **Count** — smoothed angle + hysteresis FSM → rep count + rep-state + partial flag
  (ADR-0001, ADR-0003). **Pauses on dropout, resumes without reset** (ADR-0007-C). **Pure,
  fully testable headless.** This is where tests live.
- **Present** — overlay landmarks, count, rep-state, partial / setup / "lost track"
  warnings on the frame.

Detect uses **`pose_landmarker_full`** by default (ADR-0007-D), selectable via config.

Capture and Detect are the only swappable adapters; mobile later swaps both. Features and
Count are pure and carry the test weight.

## Evaluation metrics (v1)

Following Oliosi et al. 2026 (JMIR mHealth, doi:10.2196/82412) and arXiv:2005.03194:

- **MAE** and **±1-rep accuracy** on total rep count vs expert labels.
- **F1 on rep-onset events** with a ±0.5 s tolerance window.
- **Per-viewpoint / distance breakdown** to expose robustness gaps (diagonal ~45° @ ~2 m
  vs side vs close/far), per ADR-0002.

## Fixtures & datasets

Seed fixtures from recorded team sessions plus public datasets: InfiniteRep, Kaggle
Workout, EJUST-SQUAT-21, Penn Action, Dill et al. squats corpus (MoCap-labelled angles).
Record our own labelled sessions (planned). Low-light / loose-clothing remain empirical
test gaps (literature gives no quantified numbers yet).

## Open calibration tasks (heuristics in `Features`)

The `Features` tunables — EMA `alpha`, `jitter_threshold`, visibility thresholds
(`min_landmark_visibility` / `confident_visibility`, kept aligned with `RepCounter`'s
pause gate), and the leg-averaging agreement / leg-switch margins — are **empirically-tuned
heuristics**, not literature-derived. Calibrate them against MoCap-labelled squats (Dill
et al., research §5.2) and the team's recorded sessions before claiming viewpoint-robustness.
