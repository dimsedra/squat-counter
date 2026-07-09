# Counting algorithm: joint-angle threshold + FSM with hysteresis

We count squats with a **rule-based pipeline**: extract the interior hip–knee–ankle
angle from landmarks, smooth it, and drive a finite-state machine (FSM) with
two-threshold hysteresis. We rejected learned sequence models (LSTM/BiLSTM, HMM, TCN).

**Why:** Pūioio (Sinclair et al. 2023, arXiv:2308.02420) reaches ~99% accuracy on squats
with exactly this pipeline; a 2020 preprint reports Squat F1 0.99 and ±1-rep error
(arXiv:2005.03194). It needs no training data, runs real-time on CPU, and is the
simplest robust choice for one fixed exercise. Learned models add complexity and
labelled-sequence requirements for marginal gain on a single exercise.

**Considered options:** angle+FSM+hysteresis (chosen) · LSTM/BiLSTM · HMM/Viterbi ·
TCN/peak-detection. Reserve learned models for a later multi-exercise expansion.

**Consequences:** counting logic is pure Python (no camera/UI dependency) → fully
testable headless against recorded fixtures. Depth thresholds and hysteresis margins
are the main tunable parameters.

See `docs/research/squat-rep-counting.md` §1, §3.
