# Live webcam capture moves to the browser; server counts from landmarks

For the **live webcam** path, pose detection runs **in the browser** via MediaPipe
Tasks Vision (JS/WASM). The browser captures the camera with `getUserMedia`, runs
`PoseLandmarker` per frame, and sends the **landmarks** (not video frames) to the
server over the existing WebSocket. The server reconstructs a `PoseFrame` and reuses
the unchanged `FeatureExtractor` → `RepCounter` → `SessionRecorder` chain.

This amends ADR-0006's assumption that the live path opens the camera **server-side**
(`cv2.VideoCapture`). The **uploaded-video** path is unchanged: it still decodes and
runs MediaPipe server-side (`run_pipeline`, MJPEG, `draw_overlay`).

**Why:**
- Server-side `cv2.VideoCapture(0)` opens the camera on the *host* running the server,
  never shows a browser permission prompt, and cannot see browser-visible devices
  (e.g. DroidCam) reliably on Windows — it failed with `cannot open camera 0`.
- Browser `getUserMedia` gives the native permission popup and device picker, so any
  browser-visible camera (built-in, DroidCam, OBS virtual cam) works.
- Sending landmarks (~1–2 KB/frame) instead of JPEG frames (~350 KB/frame) removes the
  round-trip bandwidth/latency of streaming video both ways.
- The counting logic (`FeatureExtractor`, `RepCounter`) is already a **pure function of
  landmark coordinates** (no image, no cv2, no mediapipe). MediaPipe JS emits the same
  33-landmark topology, so the server keeps a **single source of truth** for counting —
  no duplicated rep logic in JS. This directly leverages ADR-0004 (identical Tasks
  Vision API across Python and Web).

**Considered options:**
- Browser sends landmarks, server counts (chosen) — single counting source, tiny payload.
- Browser sends frames, server runs MediaPipe — heavy bandwidth/latency, double
  encode/decode.
- MediaPipe **and** counting both in JS — fastest, but forks the rep logic into a second
  language (divergence risk); rejected.
- Keep server-side capture, auto-detect camera index — no browser popup, host-bound.

**Consequences:**
- The WebSocket for the live path becomes **bidirectional** (client→server landmarks,
  server→client counts). The upload path's WS stays server→client only.
- MediaPipe JS + WASM + the `.task` model are **self-hosted** (served as static assets),
  keeping the app offline-capable and consistent with the model-fetch install flow.
- `POSE_CONNECTIONS` (skeleton topology) is **duplicated** in JS for the client-side
  overlay. It is static data (35 edges); low divergence risk, noted here deliberately.
- `WebcamCapture` (OpenCV) remains in `capture/` for CLI/tests but is not used by the web
  live path.
- **Scoped to localhost.** `getUserMedia` requires a secure context, which localhost
  satisfies without TLS. **LAN/mobile access is a deferred extension point:** it needs
  only (1) HTTPS (self-signed cert or a reverse proxy) and (2) binding `0.0.0.0`. No
  application-logic change — the frontend already selects `wss://` under HTTPS and uses
  relative paths for all assets/sockets.

**Session lifecycle & robustness (from code review):**
- A `SessionRecorder` is created **lazily on WebSocket connect**, not on the `GET /watch`
  page load — a page load that never streams leaves no recorder or open files.
- Sessions survive a **transient WS disconnect** (the client auto-reconnects and resumes
  counting); they are finalised on an explicit `{"stop": true}` message/`POST /stop`, or
  by an **idle reaper** that stops + drops sessions with no live connection after a
  timeout. This bounds memory/file-descriptor growth.
- `SessionRecorder` writes are **thread-safe** (a lock guards `append_frame`/
  `append_rep_event`/`stop`), and `stop()` is idempotent — the WS worker thread and an
  HTTP stop can race safely without corrupting the CSV.
- Landmark messages are **validated** (finite floats; at most 33 landmarks) and **size-
  capped**; malformed input yields an error reply, not a dropped connection.
- Webcam sessions record `fps` (from browser capture timestamps) and the auto-calibrated
  `standing_angle` into `summary.json`, matching the upload pipeline's audit trail.

See ADR-0004 (Tasks Vision cross-platform API) and ADR-0006 (capture seam).
