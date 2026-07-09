# Camera viewpoint target: diagonal ~45° at ~2 m; side view is a fail-case

v1 targets a **diagonal (~45°) camera view at ~1.8–2.0 m** from the athlete. A pure
**side view is treated as a known-fail case to test, not a supported target**.

**Why (surprising):** intuitive squat form assumes a side view, but the literature shows
the opposite. Oliosi et al. 2026 (JMIR mHealth, 44 participants, doi:10.2196/82412)
found **side view at 90 cm → 0% detection (MAE 5.0 reps)**, while a **diagonal ~45°
view at 200 cm → 95.5% detection (MAE 0.05)**. Side views fail because the near leg
occludes the far leg and the body is foreshortened. Dill et al. (2023,
doi:10.1515/cdbme-2023-1141) confirm MediaPipe accuracy is highly viewpoint-dependent.

**Consequences:** the in-app setup check should guide the athlete to a diagonal view and
warn on pure side / very close / very far placement. Count from 2D knee/hip angles, not
the z-depth channel (monocular depth is the least reliable — Dill et al. 2024,
doi:10.3390/s24237772). Low-light and loose-clothing remain unquantified gaps to test
empirically.

See `docs/research/squat-rep-counting.md` §4.
