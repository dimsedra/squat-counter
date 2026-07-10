# Batch output schema is a stable dataset contract

The headless batch processor (`scripts/batch.py` + `repcounter.batch`) emits **one
summary row per video** into a single CSV. Because downstream analysis (and the
team's external label sheets) join against this file, its **columns, types, and
`status` values are a public contract** — treated as a decision, not an
implementation detail.

## Columns (`SUMMARY_FIELDS`, fixed order)

| Column | Type | Notes |
|---|---|---|
| `video` | str | File name (e.g. `a.mp4`). Join key. |
| `path` | str | Path as given/discovered. Join key (disambiguates same-named files). |
| `status` | enum | `ok` \| `uncalibrated` \| `no_pose` \| `error` (see state machine). |
| `frames` | int | Frames actually decoded. |
| `pose_frames` | int | Frames with a detected pose. |
| `duration_sec` | float | From container metadata; falls back to `frames / fps` when metadata is missing/implausible. |
| `fps` | float | Container frame rate. |
| `calibration_angle` | float\|blank | Auto-calibrated standing angle (blank if never calibrated). |
| `total_reps` | int | Credited reps. |
| `full_reps` | int | Credited reps whose min depth was **below parallel** (`< ~90°`, `RepEvent.is_full`). |
| `partial_reps` | int | `total_reps - full_reps`: credited reps that reached parallel (`≤ ~100°`) but **not** below parallel. |
| `paused_frames` | int | Frames where counting was paused (low visibility). |
| `mean_depth_angle` | float\|blank | Mean of credited-rep min angles (blank if 0 reps). |
| `min_depth_angle` | float\|blank | Deepest (smallest) credited-rep min angle (blank if 0 reps). |
| `error` | str | Message when `status == error`, else blank. |

**Formatting rules:** floats rounded to 3 decimals; `None` → empty string; file
written UTF-8 (with BOM, `utf-8-sig`) so Excel and non-ASCII paths are safe.

### Terminology note (`partial_reps`)

This mirrors `SessionRecorder`'s split (`is_full` true/false among **credited**
reps). It is **not** the CONTEXT.md sense of "Partial rep" (an *uncredited*
descent that never reached parallel). In this CSV, `partial_reps` = credited reps
that reached parallel but not below-parallel. Uncredited shallow descents are not
represented as a column here.

## `status` state machine (per video)

```
open video ── fails ──────────────────────────► error   (error = exception message)
   │
   ├─ decoded 0 frames ───────────────────────► error   (empty/unreadable container)
   │
   ├─ frames > 0, but 0 pose frames ──────────► no_pose
   │
   ├─ pose frames > 0, never calibrated ──────► uncalibrated
   │
   └─ pose frames > 0, calibrated ────────────► ok
```

`error` is set on any exception path **or** a zero-frame decode, so a corrupt or
empty file is never silently classified as `no_pose`. Any per-video failure is
captured as an `error` row — a batch run never aborts on one bad file.

## Consequences

- Adding/removing/reordering columns is a **breaking change** to consumers; a
  regression test (`test_summary_fields_frozen`) pins the exact order.
- Consumers should filter to `status == "ok"` before computing accuracy against
  labelled ground truth; `uncalibrated`/`no_pose`/`error` rows are flagged, never
  silent `0`-rep rows.
- `duration_sec`/`fps` derive from container metadata (with a decoded-frame
  fallback), so they are advisory, not frame-exact.

See `docs/adr/0001-counting-algorithm.md` and `docs/adr/0003-squat-depth-definition.md`
for the rep/depth semantics behind these columns.
