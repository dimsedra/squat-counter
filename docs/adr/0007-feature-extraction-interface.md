# Feature extraction & counting-interface decisions

The remaining interface seams for the pure `Features` and `Count` layers, resolved by
grilling (2026-07-09) and grounded in `docs/research/squat-rep-counting.md`.

**A. Angle source — 2D coordinates, world-landmark `x/y` preferred.** The interior
hip–knee–ankle angle is computed from **2D coordinates, preferring MediaPipe
world-landmark `x/y`** (metric, viewpoint-stable — research §6, ADR-0004) and falling back
to image `x/y` when world landmarks are unavailable. The `z` (depth) channel is **ignored**
in both cases — it is the least reliable MediaPipe output (Dill et al. 2023/2024, ADR-0002).

**Correction (2026-07-09):** an earlier draft claimed image `x/y` had "no gain" over world
`x/y`. That *contradicted* the project's own research (world coordinates are more
viewpoint-stable) and the targeted diagonal ~45° view, where perspective foreshortening
biases image-2D angles and threatens the ~100° depth threshold (researcher audit #1/#7).
World `x/y` is now preferred precisely because it removes that bias; the fallback to image
`x/y` is retained only when world landmarks are absent.

**B. Leg selection.** Compute the angle **per leg (left and right)**; feed the FSM the
leg with the **higher `visibility`**, and **average the two when both are confidently
visible**. Survives one-leg occlusion at the diagonal view and leaves per-leg data free
for later form feedback.

**C. Dropout behavior.** When visibility drops below threshold or no pose is detected, the
FSM **pauses** (freezes current rep-state, feeds nothing, credits no count) and **resumes**
from the frozen state on return. It never resets an in-progress rep and never counts during
dropout. A "lost track" indicator is shown in the UI. Covers the brief frame-exit case
(ADR-0005).

**D. Smoothing & model.** Angles are **EMA-smoothed** before the FSM (tames jitter that
would trip hysteresis; pose_trainer uses this). Default detect model is
**`pose_landmarker_full`** (real-time ~25 ms, good accuracy); `lite`/`heavy` selectable via
config. Smoothing factor and model are tunable parameters, not hardcoded.

**Consequences:** the `Features` and `Count` interfaces are now fully specified and
testable headless — no camera, no `z`, no ambiguity about leg or dropout handling. These
are the seams the first pytest tests will target.
