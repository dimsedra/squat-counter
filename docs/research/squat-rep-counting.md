# Squat Repetition Counting with MediaPipe PoseLandmarker — Research Findings

**Scope:** Single-person, real-time squat rep counting on webcam (later mobile), v1 = counting + environmental robustness; form feedback is a later phase.
**Method:** Sources prioritised by trust — peer-reviewed papers (IEEE/Springer/MDPI/ACM/Frontiers/PMC), arXiv preprints, and official MediaPipe/Tasks Vision documentation. Every claim is traced to a cited source.

---

## 1. Repetition-counting algorithms for exercise with pose estimation

The literature shows a clear split between **rule-based / signal-processing methods** (joint-angle threshold + finite state machine) and **learned sequence models** (LSTM/BiLSTM, HMM, TCN).

### 1.1 Joint-angle threshold + finite state machine (FSM) — the dominant, simplest approach
- **Pūioio (Sinclair, Kautai & Shahamiri, 2023, arXiv:2308.02420, https://doi.org/10.48550/arXiv.2308.02420)** builds a real-time smartphone counter from five components: (1) pose estimation, (2) **thresholding**, (3) optical flow, (4) **state machine**, (5) counter. It reports **98.89% accuracy in real-world tests** and **98.85% on the pre-recorded dataset** for squats, push-ups, pull-ups. The authors explicitly review the state of the art and conclude a threshold + FSM pipeline is sufficient and accurate for a uni-project real-time system.
- A 2020 preprint (arXiv:2005.03194, https://arxiv.org/pdf/2005.03194) computes joint angles from pose, smooths them, and counts via a peak/state logic. It reports class-wise **Squat F1 = 0.992, recall 0.989**, and a counting **error of ±1 rep** (Table 3, Table 4).
- Multiple open-source squat counters use the same pattern: compute hip–knee–ankle (or knee) angle, track "up"/"down" states, increment on a complete cycle (e.g. `omaarrx/pose_trainer`, `yakupzengin/fitness-trainer-pose-estimation`, `DanielGuarnizo/Pose-Estimation-for-Fitness-Exercise-Analysis`). `pose_trainer` explicitly uses "rep-counting finite state machines (FSMs), exponential moving average (EMA) smoothing, and rule-based checks."
- **Riccio (2024, arXiv:2411.11548, https://arxiv.org/abs/2411.11548)** describes angle-based repetition counting as "tracks specific body landmarks and calculates angles between joints to determine the exercise stage (e.g., 'up' or 'down' position)… counts a repetition when it detects a complete cycle of movement based on predefined angle thresholds." His system reached >99% exercise *classification* accuracy.

### 1.2 Hidden Markov Models / Markov-chain transition tracking
- The **JMIR mHealth 2026 study (Oliosi et al., 2026, doi:10.2196/82412)** uses a commercial pipeline whose repetition counter is a **"Markov-chain-based algorithm [that] tracks temporal transitions between states, triggering a repetition event when a predefined sequence (e.g., up–down–up) is detected."** This is functionally an FSM/HMM and is described as robust to intermittent keypoint noise.
- A classic HMM-Viterbi rep counter (cited in Sinclair et al. 2023 as prior art) reported **~90% accuracy**.

### 1.3 LSTM / BiLSTM / sequence models
- **Fitcam (Japhne, Janada, Theodorus & Chowanda, 2024, Journal of Big Data 11:101, https://doi.org/10.1186/s40537-024-00915-8)** uses OpenPose keypoints + **LSTM** and reports **>90% accuracy for squat, push-up, sit-up, plank**.
- **Riccio (2024)** uses a **BiLSTM** for *exercise classification* (not counting) and reports 99% test accuracy; counting is still angle-threshold-based.
- **Chae et al.** (cited in Oliosi Table 1 [34]) combine OpenPose + Temporal Conv1D + BiLSTM for squats and report **85% accuracy** (n=52).

### 1.4 TCN / TCN-LSTM / few-shot peak detection
- **TCN and TCN-LSTM** appear mainly for *joint-angle estimation* from IMU/sEMG (e.g. Choi et al. 2024, Sensors 24(12):3823, https://doi.org/10.3390/s24123823; TCN-BiLSTM outperforms LSTM/ANN/GRU for lower-limb angles). Direct TCN rep counting from video pose is rarer in the retrieved literature.
- **Lim & Lee (2024, arXiv:2410.00407, https://arxiv.org/abs/2410.00407)** frame counting as peak detection on the angle/acceleration signal with **false-peak rejection**; their few-shot IMU model counts 10+ reps accurately with **86.8% probability** across 28 exercises.

### 1.5 What to use
For a single-exercise, webcam-first uni project, the evidence strongly favours **joint-angle threshold + FSM with hysteresis** (Sections 1.1, 3). It is the simplest yet robust enough: Pūioio hits ~99% with it, the 2020 preprint hits F1 0.99 for squats, and it needs no training data or GPU. Learned models (LSTM/BiLSTM) add complexity and need labelled sequences for marginal gain on a single fixed exercise.

---

## 2. Squat depth / rep definition

### 2.1 Established biomechanics thresholds (knee flexion angle)
- **Escamilla (2001, Med. Sci. Sports Exerc. 33(1):127–141, https://journals.lww.com/acsm-msse/Fulltext/2001/01000/Knee_biomechanics_of_the_dynamic_squat_exercise.20.aspx; PubMed 11194098)** — the foundational review — defines:
  - **Parallel squat** = "thighs parallel to ground at maximum knee flexion," approximately **0–100° of knee flexion** (where 0° = straight standing leg).
  - **Half squat** ≈ 0–100° knee flexion; **deep squat** = maximal flexion.
  - The **functional range 0–50° knee flexion** minimises knee forces (rehab-relevant).
  - Conclusion: the parallel squat is **not injurious to the healthy knee** and is recommended over the deep squat for athletes/rehab.
- **A 2024 biomechanical review (IJSPT, https://ijspt.scholasticahq.com/article/94600)** operationally defines depth by knee-flexion angle: **partial/shallow = 0–90°, medium = 90–110° (thigh parallel), full/deep = 110–135°**.
- **Powerlifting standard** (e.g. ironsidetraining.com, IPF rules): depth is sufficient when the **hip crease passes below the top of the knee** ("below parallel"). In interior-angle terms this is roughly **knee angle < 90°** (deeper than parallel).
- A separate training study (PMCID PMC4064719, Eur. J. Appl. Physiol.) illustrates **above-parallel ≈ 95° knee flexion, parallel ≈ 125°, below-parallel ≈ 140°** — note these use a different (larger) "knee flexion" convention where standing is ~0° and parallel is ~125°. **Angle convention matters:** most code computes the *interior* hip–knee–ankle angle (≈180° standing, ≈90–100° at parallel, <90° below parallel).

### 2.2 Thresholds actually used by exercise-counting papers / projects
- `omaarrx/pose_trainer` rule: **"Good form: knee angle < 100° at the bottom"** (interior angle; <100° ⇒ at/ past parallel).
- Pūioio and the 2020 preprint define squats by a hip–knee–ankle angle crossing a threshold; thresholds are **exercise-specific "preselected parameters"** (arXiv:2005.03194 §4.2) rather than a universal value.
- **No single published squat-depth angle is canonical across papers** — they are tuned per system. The consistent pattern is: a rep counts when the knee/hip angle goes below a "down" threshold and returns above an "up" threshold (see §3).

### 2.3 Auto-calibration of the standing angle
- Explicit auto-calibration is **not prominent in the peer-reviewed counting literature**, but it is standard engineering practice in the open-source counters cited above (measure the user's standing pose at session start, then define depth as a fraction/offset of that baseline). The 2020 preprint notes counting depends on **"preselected parameters of the exercise"** (arXiv:2005.03194 §4.2), which is exactly what per-session calibration supplies. Given the literature's emphasis on viewpoint/body-size sensitivity (§4), auto-calibrating the standing angle per session is well-justified and low-cost.

---

## 3. Hysteresis / anti-double-count

Double counting at the turnaround is the central failure mode; the literature converges on **two-threshold (enter/exit) hysteresis inside an FSM**, plus optionally **velocity/direction sign**.

- **Pūioio (Sinclair et al. 2023, arXiv:2308.02420):** notes that angle signals "can have multiple peaks per repetition… causing variations in peak shape [that] may lead to inaccurate counting," and that **amplitude thresholding per exercise reduces inaccurate peaks from noise** (citing Das et al., who reached **99.4% valid-rep detection** with amplitude thresholding on accelerometer signals). The FSM only commits a rep after a full up→down→up (or down→up) cycle, inherently preventing one-turnaround = one-count errors.
- **JMIR 2026 (Oliosi et al., doi:10.2196/82412):** the Markov-chain counter "tracks temporal transitions between states, triggering a repetition event when a predefined sequence (e.g., up–down–up) is detected," explicitly to be **"robust against intermittent keypoint noise."**
- **Lim & Lee (2024, arXiv:2410.00407):** list **"false peak rejection"** as a core part of accurate counting.
- **General signal-processing principle (hysteresis):** a two-level threshold (ON at high, OFF only after dropping below low) prevents oscillation/chatter near a single threshold (Banner Engineering, "Hysteresis and Threshold" theory, https://info.bannerengineering.com/cs/groups/public/documents/literature/tt_threshold_hysteresis.pdf). Applied to reps: enter "down" state when knee angle < depth−band, exit/count only when angle returns > standing−band; the band is the hysteresis margin.
- **Velocity/direction sign** is used as a secondary confirm: the sign of d(angle)/dt flips at the bottom/top, confirming a genuine turnaround rather than noise.

**Conclusion:** use enter/exit thresholds (hysteresis) inside an FSM; optionally confirm with velocity sign. This is the de facto standard and is directly supported by the highest-accuracy systems (Pūioio ~99%, JMIR pipeline).

---

## 4. Environmental robustness

### 4.1 Camera viewpoint (the dominant factor)
- **Oliosi et al. (2026, JMIR mHealth, doi:10.2196/82412)** is the most directly relevant study: 44 participants, 12 smartphone configurations (front/diagonal/side × 90/180/200/360 cm), expert-labelled ground truth, MAE on rep count.
  - **Squats:** best from **diagonal view at 200 cm (95.5% detection, MAE 0.05 reps)** and front 200 cm (90%, MAE 0.40). **Worst: side view at 90 cm → 0% detection, MAE 5.0 reps.** Diagonal and front significantly outperformed side at all distances (p<.001). Side views are poor because the near leg occludes the far leg and the body is foreshortened.
  - **Push-ups:** diagonal 90–200 cm best (85.7% detection, MAE ~0.28); front 360 cm worst (20%, MAE 2.70).
  - **Recommendation from the paper:** place the camera **diagonal (~45°) or frontal at 180–200 cm**.
  - **Caveat:** lighting/temperature were *standardised* — this study did **not** vary lighting or clothing, so it isolates geometry only.
- **Dill et al. (2023, Current Directions in Biomedical Engineering 9(1):563–566, doi:10.1515/cdbme-2023-1141, https://doi.org/10.1515/cdbme-2023-1141):** evaluating **MediaPipe Pose** for physical exercises, they "find that the pose estimation is **highly dependent on the camera's viewing angle as well as the performed exercise**. While high accuracy can be achieved under optimal conditions, the accuracy quickly decreases when the conditions are less favourable." Exercises with self-occlusion degrade most.
- **Dill et al. (2024/2025, Sensors 24(23):7772, doi:10.3390/s24237772, PMID 39686309):** stereo-fusion reconstruction of squats (810 squat instances, 9 subjects, MoCap ground truth). Monocular 3D HPE has large error; their fusion cuts median RMSE substantially (they report median RMSE of ~30 mm vs higher monocular error, p<0.05) — i.e. **monocular MediaPipe depth/angle error is meaningful and viewpoint-sensitive**.

### 4.2 Lighting, clothing, occlusion
- **Direct peer-reviewed evidence on low-light / loose clothing is sparse.** Oliosi et al. (2026) explicitly list "variable environmental conditions (e.g., low-light and high-contrast conditions)" as **future work**; their pipeline was validated only in standardised lighting.
- **Self-occlusion** is repeatedly named as the top degradation cause (Dill 2023; Oliosi 2026 side-view result). Loose/long clothing is not quantified in the retrieved literature but is a known failure mode for silhouette/keypoint models generally.
- **Which landmarks degrade most:** extremities and occluded points — **feet/ankles, hands/wrists** (far-side limb hidden in side view). The **z/depth channel is the least reliable** (Dill et al. note monocular 3D error is large; the 2D image landmarks are far more accurate than the inferred 3D). For squat counting, knee and hip angles from 2D landmarks are the most robust features.
- **BlazePose vs OpenPose:** Baddour et al. ("Comparing the Quality of Human Pose Estimation with BlazePose or OpenPose," https://www.researchgate.net/profile/Natalie-Baddour/...) found BlazePose (the MediaPipe model) provides clinically comparable keypoints on a smartphone, supporting its fitness/rehab use.

### 4.3 Practical takeaways for v1 robustness
- Favour a **frontal or ~45° diagonal view at ~1.8–2.0 m** (Oliosi 2026).
- Count from **2D knee/hip angles**, not z-depth.
- Expect **side views and very close/far distances to fail**; guide the user to a good camera pose (an in-app setup check is worthwhile).
- Treat **low-light / loose-clothing** as known gaps to test empirically and document; the literature does not yet give quantified numbers.

---

## 5. Evaluation metrics & datasets

### 5.1 How papers evaluate rep counters
- **Rep-count error / MAE:** ±1 rep (arXiv:2005.03194; GymCam ±1.7 reps, 93.6% recognition — cited in Sinclair 2023); **MAE on rep count** is the primary metric in Oliosi et al. (2026), e.g. MAE 0.05–5.0 across configurations.
- **Binary exact-match accuracy:** predicted count == ground truth (Oliosi 2026, "detection rate").
- **F1 / precision / recall on rep events:** arXiv:2005.03194 Table 3 reports per-class F1 (Squat 0.990); Zhang et al. (MoveNet) report **average F1: angle-heuristic 0.85, pose-classification 0.94, optical-flow 0.79** for push-ups (in Oliosi Table 1 [36]).
- **Segmentation / phase accuracy:** few-shot work reports **85% segmentation accuracy** (Lim & Lee 2024).
- **Joint-angle RMSE vs MoCap (gold standard):** Dill et al. (2023/2024) and **Mercadal-Baudart et al.** (cited Oliosi [21]) report **RMSE <10° for most joints (shin, knee, hip, trunk, spine) vs VICON**, <15° for shoulder/ASIS — useful if we later add form feedback.
- **Classifier accuracy** (exercise type): 98–99% common (Riccio 2024; Fitcam >90%; Pūioio 98.4%).

**Recommended v1 metrics:** (a) **MAE and ±1-rep accuracy** on rep count vs expert labels; (b) **F1 on rep onset events** (tolerance window, e.g. ±0.5 s); (c) **per-configuration breakdown** by viewpoint/distance (following Oliosi 2026) to expose robustness gaps.

### 5.2 Public / learnable datasets
- **InfiniteRep** (synthetic avatar exercise videos) — used by Riccio (2024); good for synthesising fixtures.
- **Kaggle "Fitness Exercise Pose Classification" / "Workout" datasets** — real exercise videos (Riccio 2024; common in repos).
- **EJUST-SQUAT-21** (Youssef et al.) — squat dataset, BlazePose reported 94% (Oliosi Table 1 [32]).
- **MM-Fit** — multimodal fitness (IMU + video).
- **Penn Action Dataset** — poses incl. squats/push-ups (used by Hande et al., Chae et al.).
- **DotPose** — internal Dotmoovs fitness dataset (Oliosi 2026), not public but illustrates the needed scale.
- **Squat Dataset (Zenodo, Teng 2025, doi:10.5281/zenodo.17558630)** — side-view images labelled Good / Bad Back / Bad Heel; useful for form (later phase).
- **Kaggle "Push-up Exercise" dataset** — used by Zhang et al. for F1 benchmarking.
- **Dill et al. squats corpus** — 810 squat instances, 9 subjects, MoCap-labelled (Sensors 2024, doi:10.3390/s24237772); the closest to a labelled squat-counting benchmark with ground-truth angles.
- **MediaPipe / Tasks Vision ship no labelled squat dataset** — we must record our own (planned) and can learn fixtures from the above.

---

## 6. MediaPipe PoseLandmarker specifics (official docs)

Confirmed from official Google AI Edge documentation (https://ai.google.dev/edge/mediapipe/solutions/vision/pose_landmarker/index; legacy Solutions doc https://github.com/google-ai-edge/mediapipe/blob/master/docs/solutions/pose.md) and the BlazePose paper (Bazarevsky et al. 2020, arXiv:2006.10204, https://arxiv.org/abs/2006.10204):

- **33 landmarks** ("BlazePose GHUM 3D"): face/eyes/ears (0–10), shoulders/elbows/wrists (11–16), hands (17–22), hips/knees/ankles (23–28), feet/heels (29–32). The landmark model predicts 33 3D landmarks (legacy doc, Fig 4).
- **Output format per landmark:**
  - `x`, `y`: normalised to [0,1] by image width/height.
  - `z`: depth, origin at the **midpoint of the hips**; smaller = closer to camera; roughly same scale as `x` (legacy pose.md Output section).
  - `visibility`: [0,1] likelihood the landmark is visible and not occluded. (World landmarks additionally carry `presence`.)
  - **World landmarks** (`pose_world_landmarks`): real-world 3D coordinates in **metres**, origin at the centre between hips — more viewpoint-stable than image coords.
- **Available models (Tasks Vision `.task` bundles):** **`pose_landmarker_lite`**, **`pose_landmarker_full`**, **`pose_landmarker_heavy`** (confirmed via official npm/UNPKG README, e.g. `https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task`). The older "Solutions" API used `model_complexity` 0/1/2 = lite/full/heavy.
- **Cross-platform, same API:** official docs provide identical task guides for **Python, Web (JS/WASM), Android, and iOS** (ai.google.dev/edge/.../pose_landmarker/{python,web_js,android}). The legacy overview states BlazePose "achieves real-time performance on most modern mobile phones, desktops/laptops, in python and even on the web" (https://chuoling.github.io/mediapipe/solutions/pose.html). This directly satisfies the webcam-first → mobile-later plan.
- **Latency (legacy BlazePose):** Full ≈ 25 ms (Pixel 3 GPU) / 27 ms (MacBook); Heavy ≈ 53 ms / 38 ms — i.e. real-time at 30+ fps even on the heavy model (legacy pose.md Models section).

---

## Implications for our design

**Algorithm (Q1):** Use **joint-angle threshold + finite state machine with hysteresis** (not LSTM/TCN). Evidence: Pūioio ~99% with this exact pipeline (Sinclair 2023); Squat F1 0.99 / ±1 rep (arXiv:2005.03194); it needs no training data, runs real-time on CPU, and is the simplest robust choice for one fixed exercise. Reserve learned models for later multi-exercise expansion.

**Depth threshold & calibration (Q2):**
- Define a rep's "down" state by the **interior hip–knee–ankle angle**: count depth when angle **≤ ~100° (parallel)**, optionally require **< 90° (below parallel)** for "full" depth. This matches Escamilla's parallel-squat definition (0–100° knee flexion, Med Sci Sports Exerc 2001) and the operational review (partial 0–90°, medium 90–110°, deep 110–135°, IJSPT 2024).
- **Auto-calibrate the standing angle per session** (capture user's upright pose at start; set depth threshold relative to it). Justified by viewpoint/body-size sensitivity in §4 and is already the implicit "preselected parameters" practice (arXiv:2005.03194).

**Anti-double-count (Q3):** Implement **two-threshold hysteresis inside the FSM**: enter "down" only when angle < depth−margin, count a rep only after returning above standing−margin; optionally confirm with **velocity-sign flip** at turnaround. This is the documented standard (Pūioio amplitude thresholding + FSM; Oliosi 2026 Markov-chain up–down–up; false-peak rejection in Lim & Lee 2024).

**Robustness (Q4):** Assume a **frontal or ~45° diagonal camera at 1.8–2.0 m** (Oliosi 2026: diagonal 200 cm → 95.5% detection, MAE 0.05; side 90 cm → 0%). Count from **2D knee/hip angles**, not z-depth (monocular depth is the weakest channel, Dill 2023/2024). **Side views, very close/far distances, low light, and loose clothing are known failure modes** — instrument an in-app camera-setup check and treat lighting/clothing as empirical test gaps (literature gives no quantified numbers yet).

**Evaluation (Q5):** Report **MAE and ±1-rep accuracy** on rep count vs expert labels, **F1 on rep onset events** (±0.5 s tolerance), and a **per-viewpoint/distance breakdown** (mirroring Oliosi 2026) to expose robustness. Seed fixtures from **InfiniteRep, Kaggle Workout, EJUST-SQUAT-21, Penn Action**, and record our own labelled sessions (the planned real + synthetic data).

**MediaPipe fit (Q6):** PoseLandmarker gives **33 landmarks**, normalised `x/y`, depth `z`, and `visibility` (plus world landmarks in metres) — enough for knee/hip angle computation. The **lite/full/heavy `.task` models** and the **identical Python / Web / Android / iOS API** mean our webcam-first v1 ports to mobile with no algorithmic change.
