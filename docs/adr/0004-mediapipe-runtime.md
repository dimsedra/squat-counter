# Runtime: MediaPipe Tasks Vision PoseLandmarker

We use the **MediaPipe Tasks Vision `PoseLandmarker`** API (BlazePose GHUM 3D, 33
landmarks, `lite`/`full`/`heavy` `.task` models), not the legacy `mediapipe` Pose
solution.

**Why:** the mobile goal is explicit (webcam-first, mobile-later). Tasks Vision exposes an
**identical API across Python, Web (JS/WASM), Android, and iOS** (official Google AI Edge
docs), so the detect adapter written for webcam v1 ports to mobile with no algorithmic
change. The legacy Solutions API is "legacy" and would force a detect-layer rewrite for
mobile.

**Considered options:** Tasks Vision PoseLandmarker (chosen) · legacy `mediapipe` Pose
(simplest webcam, but mobile = rewrite) · custom TF/PyTorch pose model (overkill).

**Consequences:** detect layer is an adapter behind a seam; swapping to mobile is an
adapter change, not a rewrite. Landmarks available: hips (23/24), knees (25/26), ankles
(27/28) are the squat-critical ones.

See `docs/research/squat-rep-counting.md` §6.
