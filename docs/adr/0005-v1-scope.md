# v1 scope: single-person counting + robustness; form feedback deferred

v1 delivers **single-person squat counting under varied real-world conditions**
(low light, loose clothing, varied camera angle, paused/slow/fast reps, brief
frame-exit). **Form feedback is explicitly deferred to a later phase** (the feature/count
seams leave room for it). **Multi-person counting is out of scope** for now.

**Why:** keeps a solid, testable deliverable without scope creep. Environmental robustness
is the core v1 challenge and is served by angles + hysteresis + visibility gating + a
min-depth rule. Form feedback (depth grading, knee valgus, back angle, tempo) and
multi-person (per-track state machines + re-ID) are separable later additions.

**Consequences:** the counting layer is built for one track; multi-person later means
adding a tracking/re-ID layer that fans out per-track FSMs. Form-feedback later means a
new analysis module over the same extracted features.

See `docs/research/squat-rep-counting.md` §5 (evaluation) for how v1 is measured.
