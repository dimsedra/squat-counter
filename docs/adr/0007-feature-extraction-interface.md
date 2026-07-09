# Feature extraction & counting-interface decisions

The remaining interface seams for the pure `Features` and `Count` layers, resolved by
grilling (2026-07-09) and grounded in `docs/research/squat-rep-counting.md`.

**A. Angle source — 2D image landmarks.** The interior hip–knee–ankle angle is computed
from **image `landmark.x` / `landmark.y`** (normalized to the frame). The `z` (depth)
channel is **ignored** — it is the least reliable MediaPipe output (Dill et al. 2023/2024,
ADR-0002). World-landmark `x/y` was considered but adds conversion for no gain at our
diagonal-view target.

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
