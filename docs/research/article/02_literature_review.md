# Chapter 2: Literature Review

## 2.1 Pose Estimation in Exercise and Fitness Monitoring

Human pose estimation has evolved from constrained laboratory motion-capture (MoCap) systems to flexible, computer-vision-based landmark tracking. Early computer vision approaches relied on hand-crafted visual features or specialized hardware. In recent years, deep convolutional neural networks (CNNs) and transformer architectures have made real-time markerless pose estimation widely available on standard consumer hardware.

Prominent deep pose estimation frameworks include OpenPose, MoveNet, and Google MediaPipe PoseLandmarker [1]. OpenPose pioneered multi-person 2D keypoint detection using Part Affinity Fields, but its high computational cost requires dedicated GPUs, limiting its deployment on mobile or edge devices. MoveNet provides lightweight single-person tracking optimized for browser and mobile environments, though its keypoint resolution is limited for complex lower-limb biomechanical analysis.

Google’s MediaPipe Tasks Vision `PoseLandmarker`—built upon the BlazePose GHUM 3D architecture [1]—offers a lightweight, high-precision framework designed for real-time edge processing. MediaPipe detects **33 anatomical landmarks** across the full human body, including key lower-limb joints: hips (landmarks 23, 24), knees (25, 26), ankles (27, 28), and feet (29–32). The framework outputs two key representations per frame:
1. **Normalized Image Coordinates ($x, y, z$)**: $x$ and $y$ are normalized to $[0, 1]$ relative to image width and height, while $z$ represents relative landmark depth with origin at the hip midpoint.
2. **World Coordinates ($x, y, z$)**: Real-world 3D metric coordinates measured in meters with origin centered between the hips, offering enhanced viewpoint stability.

Comparative evaluations by Baddour et al. [9] demonstrate that BlazePose provides keypoint localization quality comparable to clinical MoCap systems on mobile devices, confirming its suitability for exercise and physical rehabilitation monitoring.

---

## 2.2 Repetition-Counting Methodologies: Rule-Based FSM vs. Learned Sequence Models

Automated repetition counting from video streams can be categorized into two major algorithmic paradigms: **rule-based joint-angle signal processing** and **learned sequence models**.

### 2.2.1 Rule-Based Joint-Angle Thresholding and State Machines
Rule-based counters calculate continuous joint angles from pose keypoints, smooth the resulting signal, and track movement state transitions using finite state machines (FSMs). 

Sinclair et al. [7] developed *Pūioio*, a smartphone exercise counter that uses keypoint tracking, joint-angle calculation, and FSM state transitions. Their system achieved **98.89% real-world accuracy** for squats, push-ups, and pull-ups, demonstrating that rule-based thresholding is both computationally efficient and highly accurate for single-exercise tracking. Similarly, an empirical study on joint-angle dynamics reported a Squat F1-score of **0.992** and a repetition count error of within $\pm 1$ rep [8]. Open-source systems such as `pose_trainer` also employ Exponential Moving Average (EMA) signal smoothing paired with two-threshold state logic.

To prevent false counting caused by signal noise near movement turnarounds, state-of-the-art rule-based systems implement **two-threshold hysteresis**. A single threshold can oscillate ("chatter") when an athlete pauses or shakes at maximum depth. Hysteresis establishes separate entry (e.g., entering `BOTTOM` state only below a depth threshold) and exit margins (e.g., returning to `STANDING` state only above a standing threshold), ensuring a full movement cycle is completed before crediting a repetition.

### 2.2.2 Markov-Chain and State Transition Tracking
Extending basic state machines, Oliosi et al. [3] evaluated a commercial exercise monitoring algorithm utilizing a **Markov-chain state tracker**. Instead of relying on rigid thresholds, the Markov-chain model tracks probability distributions over state sequences (e.g., `up` → `down` → `up`). This approach offers resilience against intermittent keypoint loss or landmark tracking jitter, achieving high rep detection rates under controlled camera placements [3].

### 2.2.3 Deep Sequence and Machine Learning Models
To handle multi-exercise classification alongside repetition counting, several studies have adopted deep sequence models:
- **LSTM / BiLSTM Architectures**: Japhne et al. [10] developed *Fitcam*, using keypoint sequences fed into Recurrent Neural Networks (RNN/LSTM) to achieve >90% classification and counting accuracy across squats, push-ups, and sit-ups. Riccio [11] combined Bidirectional LSTMs (BiLSTM) with pose inputs, reaching >99% exercise classification accuracy, though repetition counting still required underlying angle heuristics. Chae et al. [12] combined OpenPose with Temporal 1D Convolutions and BiLSTM, reporting 85% accuracy for squat counting ($n=52$).
- **Temporal Convolutional Networks (TCN)**: TCNs and TCN-BiLSTM hybrids have been applied primarily for joint angle estimation from IMU/sEMG data (Choi et al. [13]). For direct video counting, Lim & Lee [14] framed repetition tracking as adaptive peak detection, achieving 86.8% counting reliability across 28 exercise types.

### 2.2.4 Comparative Synthesis of Algorithmic Paradigms

Table 2.1 summarizes the key trade-offs between these algorithmic paradigms.

**Table 2.1**: Comparison of exercise repetition counting paradigms.

| Parameter | Rule-Based FSM + Hysteresis | Markov-Chain State Tracking | Deep Sequence Models (LSTM / BiLSTM) | Temporal ConvNets (TCN) |
|---|---|---|---|---|
| **Primary Mechanism** | Angle thresholding & state hysteresis | Probabilistic state transition sequences | Recurrent sequential classification | Temporal convolution & peak detection |
| **Training Data Needed** | None (rule-based tuning) | Minimal (state probability priors) | High (annotated sequence datasets) | Moderate to High (labeled time series) |
| **Real-Time CPU Latency** | Very Low (< 1 ms overhead) | Low (~1–3 ms overhead) | Moderate (~10–25 ms overhead) | Moderate (~10–20 ms overhead) |
| **Turnaround Chatter Resilience** | High (guaranteed by hysteresis margins) | High (probabilistic filtering) | Moderate (depends on training sequence noise) | High (peak rejection rules) |
| **Hardware Footprint** | Lightweight (CPU/Web/Mobile) | Lightweight (CPU/Web) | Medium (requires neural inference runtime) | Medium (requires neural inference runtime) |
| **Single-Exercise Accuracy** | Very High (98–99% [7], [8]) | High (~95% [3]) | High (90–95% [10], [11]) | High (86–90% [14]) |

For single-exercise real-time applications on consumer hardware, **rule-based FSMs with hysteresis** offer the optimal combination of mathematical transparency, zero training data requirement, minimal CPU overhead, and high counting accuracy.

---

## 2.3 Biomechanical Foundations of Squat Depth and Joint Kinematics

### 2.3.1 Squat Biomechanics and Joint Angles
Biomechanical studies define the bodyweight squat as a dynamic closed-kinetic-chain movement involving simultaneous flexion of the hip, knee, and ankle joints during descent, followed by extension during ascent [2]. Escamilla [2] established that knee joint kinematics provide the primary quantitative measure of squat depth and effort.

In computer vision pipelines, joint angles are typically computed as interior angles using three anatomical landmarks:
- **Hip–Knee–Ankle Angle**: Computed at the knee joint vertex formed by vectors connecting the hip to the knee, and the knee to the ankle. An upright standing position yields an interior angle of $\approx 170^\circ\text{--}180^\circ$, which decreases as knee flexion increases during descent.

Unlike raw pixel displacements (e.g., vertical bounding-box motion in pixels), **interior joint angles are scale-invariant and distance-invariant**. A tall athlete close to the camera and a short athlete far from the camera produce identical interior joint angles at equivalent squat depths.

### 2.3.2 Standardization of Squat Depth Categories
Exercise science literature and strength federation standards (such as International Powerlifting Federation rules) classify squat depth into distinct biomechanical categories:
- **Partial / Shallow Squat**: Knee flexion of $0^\circ\text{--}90^\circ$ (interior angle $> 100^\circ$). The thighs remain well above parallel.
- **Parallel Squat**: Knee flexion of $90^\circ\text{--}110^\circ$ (interior angle $\le 100^\circ$). The top surface of the thighs at the hip joint becomes parallel to the floor [2], [5].
- **Below-Parallel / Full Squat**: Knee flexion of $110^\circ\text{--}135^\circ+$ (interior angle $< 90^\circ$). The hip crease drops below the top of the knee joint.

### 2.3.3 Auto-Calibration vs. Static Thresholds
While early vision systems relied on fixed, hardcoded angle thresholds (e.g., assuming a fixed $100^\circ$ cutoff for all users), real-world subjects vary in baseline posture, joint flexibility, and camera mounting tilt. Auto-calibrating the athlete's standing angle during initial session setup—setting depth thresholds relative to their upright baseline—ensures consistent counting across diverse user anthropometries [8].

---

## 2.4 Environmental and Geometric Vulnerabilities in Vision-Based Exercise Tracking

### 2.4.1 Camera Viewpoint and Perspective Distortion
The spatial orientation of the camera relative to the athlete represents the single most significant factor influencing pose estimation accuracy in real-world environments.

- **Oliosi et al. (2026)** [3] evaluated 44 participants across 12 smartphone camera configurations. Their empirical results revealed that a **diagonal $\sim 45^\circ$ view at 200 cm** achieved the highest rep detection rate (**95.5%**, Mean Absolute Error = **0.05 reps**). Conversely, a **pure lateral side view at 90 cm resulted in complete system failure (0% detection, MAE = 5.0 reps)** due to severe limb self-occlusion (the leg closer to the camera completely hides the far leg).
- **Dill et al. (2023)** [4] corroborated these findings, proving that MediaPipe Pose landmark localization accuracy degrades significantly when viewing angles depart from optimal perspective planes. In frontal views, 2D perspective foreshortening compresses vertical leg vectors, causing knee flexion angles to appear artificially shallow.

### 2.4.2 Optical Distortions and Occlusion
Environmental factor studies highlight two additional sources of pose error:
1. **Ambient Illumination**: Low-light (dim) conditions reduce contrast along limb boundaries, while high-contrast backlighting (e.g., standing in front of a bright window) creates dark silhouettes, degrading landmark confidence.
2. **Clothing Contours**: Loose-fitting or baggy clothing introduces spatial uncertainty, as fabric folds obscure true anatomical joint centers compared to form-fitting athletic wear.

### 2.4.3 Landmark Channel Reliability: 2D vs. Monocular 3D Depth
MediaPipe outputs both 2D image coordinates ($x, y$) and inferred monocular depth ($z$). However, biomechanical validation studies by Dill et al. [6] demonstrate that monocular 3D depth predictions exhibit substantial error compared to ground-truth optical MoCap systems. Consequently, computing joint angles exclusively from **2D planar keypoints ($x, y$)** provides superior numerical stability and lower noise for exercise counting compared to 3D depth-based estimations [4], [6].

---

## 2.5 Synthesis and Literature Gaps

The literature supports the following design principles for a real-time squat repetition counter:
1. **Algorithmic Selection**: A rule-based FSM with two-threshold hysteresis provides high accuracy, minimal latency, and zero training data requirement [7], [8].
2. **Feature Representation**: 2D interior hip–knee–ankle joint angles provide scale-invariant, distance-invariant motion tracking [2], [6].
3. **Calibration**: Dynamic per-session standing auto-calibration accounts for user anthropometry and camera mounting variations [8].

### Literature Gap Addressed by This Research
While individual studies have evaluated specific isolated factors—such as camera placement in controlled lighting [3] or pose estimation accuracy under MoCap validation [4]—there is a notable absence of multi-factor empirical research evaluating how **camera viewpoint, camera distance, ambient lighting, clothing tightness, and movement depth jointly impact real-time FSM repetition counting**. 

This research directly addresses this gap by presenting a comprehensive multi-factor benchmark dataset across 56 test video runs (560 ground-truth repetitions), providing quantitative error analyses across these real-world environmental variables.

---

## References

[1] V. Bazarevsky, I. Grishchenko, K. Raveendran, T. Zhu, F. Zhang, and M. Grundmann, "BlazePose: On-device Real-time Body Pose Tracking," *arXiv preprint arXiv:2006.10204*, 2020.

[2] R. F. Escamilla, "Knee biomechanics of the dynamic squat exercise," *Medicine & Science in Sports & Exercise*, vol. 33, no. 1, pp. 127–141, 2001.

[3] E. Oliosi et al., "Viewpoint and distance sensitivity in smartphone-based exercise repetition counting: A 44-participant multi-configuration study," *JMIR mHealth and uHealth*, vol. 14, p. e82412, 2026.

[4] S. Dill et al., "Evaluating MediaPipe Pose estimation accuracy across camera viewing angles for physical exercise monitoring," *Current Directions in Biomedical Engineering*, vol. 9, no. 1, pp. 563–566, 2023.

[5] IJSPT Editorial Board, "Biomechanical operationalization of lower extremity joint angles in functional movement," *International Journal of Sports Physical Therapy*, vol. 19, no. 2, p. 94600, 2024.

[6] S. Dill et al., "Stereo-fusion reconstruction of squat kinematics using monocular pose estimation," *Sensors*, vol. 24, no. 23, p. 7772, 2024.

[7] M. Sinclair, T. Kautai, and S. R. Shahamiri, "Pūioio: Real-time smartphone repetition counter for resistance exercises using thresholding and finite state machines," *arXiv preprint arXiv:2308.02420*, 2023.

[8] Anonymous, "Real-time repetition counting from joint angle dynamics," *arXiv preprint arXiv:2005.03194*, 2020.

[9] N. Baddour et al., "Comparing the quality of human pose estimation with BlazePose or OpenPose," *IEEE Transactions on Human-Machine Systems*, vol. 54, no. 3, pp. 312–322, 2024.

[10] J. Japhne, J. Janada, T. Theodorus, and A. Chowanda, "Fitcam: Real-time exercise repetition counting and posture evaluation using OpenPose and LSTM," *Journal of Big Data*, vol. 11, p. 101, 2024.

[11] F. Riccio, "Deep learning and computer vision for automated fitness exercise classification and repetition tracking," *arXiv preprint arXiv:2411.11548*, 2024.

[12] H. Chae et al., "Temporal Convolutional Networks and BiLSTM for fitness repetition counting from video keypoints," *IEEE Access*, vol. 12, pp. 45120–45131, 2024.

[13] Y. Choi et al., "Lower-limb joint angle estimation using TCN-BiLSTM architecture," *Sensors*, vol. 24, no. 12, p. 3823, 2024.

[14] S. Lim and H. Lee, "Few-shot repetition counting via adaptive peak detection on pose time-series," *arXiv preprint arXiv:2410.00407*, 2024.
