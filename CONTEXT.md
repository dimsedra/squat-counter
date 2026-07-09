# Squat Rep Counter

A real-time computer-vision system that tracks a person performing bodyweight squats
in front of a webcam and counts each repetition. Built on MediaPipe Tasks Vision
`PoseLandmarker`; mobile is a later target. v1 covers single-person counting under
varied real-world conditions.

## Language

**Athlete**
The single person being tracked and counted. v1 assumes exactly one athlete in frame.
_Avoid_: user, subject, patient

**Landmark**
One of the 33 body keypoints MediaPipe `PoseLandmarker` outputs per frame (e.g. hip,
knee, ankle), each with normalised x/y, depth z, and a visibility score.
_Avoid_: keypoint, point, joint (a joint is inferred from landmarks)

**Joint angle (interior angle)**
The interior angle formed by three landmarks at a joint — here the hip–knee–ankle
angle. Used as the squat signal because it is **scale- and distance-invariant** (a tall
person far from the camera and a short person close both read the same value).
_Avoid_: angle (too vague — always specify which three landmarks)

**Squat**
The tracked exercise: descending until the thighs reach at least parallel, then
ascending back to standing. Defined by the hip–knee–ankle angle cycle, not by pixels.

**Repetition (rep)**
One complete down→up squat cycle the system credits to the count. Precisely: a descent
that reaches min-depth, followed by a return to the standing range.
_Avoid_: repetition count (that is the running total, not one cycle)

**Depth**
How far a squat descends, measured as the **minimum interior hip–knee–ankle angle**
reached at the bottom of a rep. Larger angle = shallower squat.

**Parallel (depth)**
A squat whose bottom reaches an interior hip–knee–ankle angle of **≤ ~100°** (thighs
roughly parallel to the ground). The minimum depth required for a rep to count.
_Avoid_: half-squat (overloaded — see Partial rep)

**Below parallel (full depth)**
A squat whose bottom reaches an interior hip–knee–ankle angle of **< ~90°** (hip crease
below the knee). Treated as a "full" rep; stricter than parallel.

**Partial rep**
A descent that does **not** reach the min-depth threshold, then returns to standing.
Not credited to the count, but flagged in the UI so the miss is visible.
_Avoid_: incomplete rep (use Partial)

**Rep state**
The state the counting finite-state machine currently occupies:
`STANDING → DESCENDING → BOTTOM → ASCENDING → STANDING`. One full cycle = one rep.

**Hysteresis**
Two-threshold gating on the joint angle: enter `BOTTOM` only below a depth threshold,
and exit back to `STANDING` only above a standing threshold (with a margin between
them). Prevents jitter at the turnaround from double-counting a rep.

**Calibration**
Measuring the athlete's upright (standing) pose at session start so depth thresholds
are set **relative to that baseline** rather than hardcoded. Makes counting adapt to
camera height, framing, and body size.

**Viewpoint**
The camera's placement relative to the athlete. v1 targets a **diagonal ~45° view at
~1.8–2.0 m**; a pure **side view is a known-fail case** (near leg occludes far leg).
_Avoid_: angle (ambiguous — say viewpoint)

**Visibility**
MediaPipe's per-landmark score in [0,1] for how likely the landmark is visible and not
occluded. Used to gate features when a landmark is unreliable.

**Fixture**
A recorded video or image sequence used as a test input. The capture seam accepts files
(not just live webcam), so recorded sessions become reproducible test inputs.
_Avoid_: test video (too vague)
