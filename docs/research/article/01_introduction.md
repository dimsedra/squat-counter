# Chapter 1: Introduction

## 1.1 Background and Motivation

In recent years, computer vision and human motion analysis have driven significant progress in fitness tracking, sports science, and digital telerehabilitation. Traditionally, monitoring exercise repetition and movement quality relied on human trainers or specialized equipment, such as wearable inertial measurement units (IMUs), goniometers, or multi-camera optical motion-capture (MoCap) systems (e.g., VICON). Although specialized wearable sensors and MoCap systems provide high precision in clinical settings, their high cost, complex setup, and physical attachments make them impractical for everyday home workouts and remote health tracking.

The widespread availability of standard RGB cameras—built into smartphones, laptops, and webcams—offers a practical, non-invasive alternative: markerless pose estimation. By detecting 2D and 3D body keypoints directly from video streams, modern deep-learning models, such as Google’s MediaPipe PoseLandmarker [1], allow automated exercise tracking using standard consumer devices.

Among core strength exercises, the **bodyweight squat** is a fundamental movement used in both athletic training and physical rehabilitation [2]. Performing a proper squat engages major lower-body muscle groups while assessing knee mobility, hip mobility, and balance. However, counting exercise repetitions automatically from video streams introduces key computer vision challenges. A reliable real-time exercise counter must perform accurately despite differences in user body size, camera placement, ambient lighting, clothing tightness, and movement execution.

---

## 1.2 Problem Statement and Environmental Vulnerabilities

Although modern pose estimation models achieve high accuracy on standardized benchmarks, deploying them for real-time exercise counting in unconstrained home environments reveals several real-world failure modes:

1. **Camera Angle and Distance Sensitivities**: Camera viewpoint (front, 45° diagonal, or side view) and distance (e.g., 1 m vs. 2 m) significantly affect keypoint detection. As demonstrated by Oliosi et al. [3] and Dill et al. [4], MediaPipe accuracy is highly dependent on camera viewing angle. In 2D video, perspective distortion (foreshortening) can alter perceived joint angles in frontal views, while side views often suffer from limb self-occlusion where the near leg blocks the far leg [3].
2. **Lighting and Clothing Obstacles**: Environmental conditions such as low lighting (dim rooms) or high-contrast backlighting reduce landmark detection reliability. Additionally, loose-fitting clothing obscures body contours, introducing visual noise into keypoint predictions.
3. **Movement Variability and Signal Noise**: Exercisers differ in squat depth—ranging from shallow partial reps to parallel (knee flexion ~100°) and deep squats [2], [5]—as well as movement tempo. Small fluctuations or landmark jitter near turnaround points (the bottom of the squat) often cause simple threshold-based counters to double-count repetitions.

While previous research has evaluated pose estimation models in laboratory settings, few studies systematically examine how environmental factors—such as camera angle, distance, lighting, and clothing—interact with rule-based counting algorithms in everyday conditions.

---

## 1.3 Proposed System Overview

To address these challenges, this study presents a lightweight, real-time computer vision system for bodyweight squat monitoring and repetition counting. Built on MediaPipe Tasks Vision `PoseLandmarker` (using a 33-keypoint 3D landmark model) [1], the system features a hardware-efficient processing pipeline:

- **Scale-Invariant Feature Extraction**: The system calculates the interior joint angle of the hip–knee–ankle triplet using 2D coordinates. This joint angle remains constant regardless of the person's height, body proportions, or distance from the camera. Following findings by Dill et al. [6], the monocular depth ($z$) channel is excluded due to its lower reliability compared to 2D planar landmarks.
- **Per-Session Standing Auto-Calibration**: To adjust for different camera heights and user postures, the system measures the user's standing angle at the start of each session, establishing a dynamic baseline for depth thresholds.
- **Hysteresis Finite State Machine (FSM)**: Grounded in the proven efficacy of rule-based counters [7], [8], repetition tracking uses a two-threshold hysteresis state machine (`STANDING` → `DESCENDING` → `BOTTOM` → `ASCENDING` → `STANDING`). The state machine requires clear entry and exit margins before crediting a completed repetition, effectively preventing double-counting caused by landmark jitter.

---

## 1.4 Research Objectives and Questions

The main goal of this study is to evaluate the accuracy, environmental robustness, and execution sensitivity of the MediaPipe-based squat repetition counter under realistic conditions. Specifically, this research addresses three key questions:

- **RQ1**: *What repetition-counting accuracy (Mean Absolute Error and Mean Absolute Percentage Error) can a joint-angle hysteresis FSM achieve in real time?*
- **RQ2**: *How do variations in camera angle (front, diagonal, side), camera distance (1m vs. 2m), lighting (normal, backlit, dim), and clothing (fitted vs. loose) impact pose detection stability and counting accuracy?*
- **RQ3**: *How effectively do automatic calibration and two-threshold hysteresis distinguish valid squats (full and parallel) from incomplete partial repetitions?*

---

## 1.5 Key Contributions and Empirical Findings

The principal contributions of this work are:

1. **System Implementation**: An end-to-end Python and web-compatible framework that processes video streams in real time using MediaPipe PoseLandmarker, featuring standing posture auto-calibration, FSM repetition counting, and session logging.
2. **Multi-Factor Dataset Evaluation**: A structured empirical evaluation conducted on 56 test videos across 4 athletes (totaling 560 ground-truth repetitions) testing 6 experimental sub-conditions (camera angle, distance, lighting, clothing, squat depth, and duration).
3. **Empirical Viewpoint and Depth Insights**:
   - The overall system achieved an average repetition counting accuracy of **83.57%** (Mean Absolute Percentage Error of **16.43%**).
   - **Viewpoint Superiority**: Lateral **side views** achieved the highest accuracy (**MAE of 0.25**) compared to diagonal (**MAE of 1.725**) and frontal views (**MAE of 2.625**), because side views directly capture knee and hip flexion without the perspective distortion present in frontal views.
   - **Depth Filtering**: The hysteresis FSM effectively filtered partial squats (MAE of 5.75 on partial rep trials), preventing shallow movements from being incorrectly counted as completed reps.

---

## 1.6 Structure of the Article

The rest of this article is organized as follows:
- **Chapter 2 (Literature Review)** reviews current methods in exercise pose estimation, comparing state machines with sequence-learning models, squat depth definitions, and reported failure modes.
- **Chapter 3 (Methodology & System Architecture)** details the joint angle formulas, standing auto-calibration procedure, state machine transition rules, and experimental setup.
- **Chapter 4 (Experimental Results & Analysis)** presents quantitative results across all 56 video trials, breaking down accuracy and MAE by athlete, camera angle, distance, lighting, clothing, and squat depth.
- **Chapter 5 (Discussion & Conclusion)** summarizes the findings, provides practical recommendations for camera placement in fitness applications, addresses current limitations, and outlines future work.

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
