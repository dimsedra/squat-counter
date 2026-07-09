# Squat depth definition and per-session calibration

A rep counts only when the descent reaches a **minimum depth of interior hip–knee–ankle
angle ≤ ~100° ("parallel")**. A stricter **< ~90° ("below parallel / full")** labels a
rep as full. Partial reps (don't reach min depth) are **not counted but flagged** in the
UI. The standing angle is **auto-calibrated per session**; thresholds are set relative to
it. Anti-double-count uses **two-threshold hysteresis** inside the FSM (enter `BOTTOM`
only below depth−margin; count only after returning above standing−margin), optionally
confirmed by velocity-sign flip at the turnaround.

**Why:** Escamilla (2001, Med Sci Sports Exerc 33(1):127–141) defines the parallel squat
as ~0–100° knee flexion; an IJSPT 2024 review operationalises depth as partial 0–90°,
medium 90–110° (parallel), deep 110–135°. `pose_trainer` uses "<100° at the bottom" as
the good-form rule. Auto-calibration is justified by the viewpoint/body-size sensitivity
documented in `docs/research/squat-rep-counting.md` §4 and is already the implicit
"preselected parameters" practice (arXiv:2005.03194 §4.2).

**Considered options:** fixed threshold vs auto-calibrated (chose auto-calibrated) ·
min-depth ≤100° (parallel) vs <90° (below parallel) as the count gate (chose ≤100°, with
<90° as a "full" label).

See `docs/research/squat-rep-counting.md` §2, §3.
