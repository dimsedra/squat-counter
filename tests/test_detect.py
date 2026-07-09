"""M4 tests for the Detect seam (PoseLandmarkerDetector).

T1 -- mocked unit tests (no model, no network): landmark mapping, BGR->RGB
     conversion, world-landmark population, empty-result -> None.
T2 -- real detector on a single clip frame (skip-guarded: needs the model).
T3 -- full pipeline (Detector -> Features -> Count) over a public clip
     (skip-guarded: needs model + extracted frames + manifest ground truth).

The mocked tests always run and carry the unit coverage; T2/T3 validate the
real adapter end-to-end once assets are present (see scripts/fetch_model.py and
scripts/fetch_test_clip.py).
"""
from __future__ import annotations

import json
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np
import pytest

from repcounter.count import RepCounter
from repcounter.detect import PoseLandmarkerDetector
from repcounter.detect.pose_landmarker import _MP_VISION
from repcounter.features import FeatureExtractor
from repcounter.types import PoseFrame

FIXTURES = Path(__file__).parent / "fixtures"
CLIP_DIR = FIXTURES / "clip"
MANIFEST = FIXTURES / "manifest.json"
MODEL_PATH = Path(__file__).resolve().parent.parent / "models" / "pose_landmarker_full.task"

has_model = MODEL_PATH.exists()
has_clip = CLIP_DIR.exists() and any(CLIP_DIR.glob("*.png"))
has_manifest = MANIFEST.exists()


# --------------------------------------------------------------------------- #
# Fakes for T1 (no mediapipe model / network required)
# --------------------------------------------------------------------------- #
class _FakeLandmark:
    def __init__(self, x, y, visibility=None, presence=None):
        self.x = x
        self.y = y
        self.visibility = visibility
        self.presence = presence


class _FakeResult:
    def __init__(self, pose_landmarks, pose_world_landmarks):
        self.pose_landmarks = pose_landmarks
        self.pose_world_landmarks = pose_world_landmarks


class _FakeImage:
    def __init__(self, image_format, data):
        self.image_format = image_format
        self.data = data


class _FakeDetector:
    def __init__(self, result, captures):
        self._result = result
        self.captures = captures

    def detect(self, mp_image):
        self.captures.append(mp_image)
        return self._result


def _install_fake(monkeypatch, result, captures):
    fake_detector = _FakeDetector(result, captures)

    class _FakePoseLandmarker:
        @staticmethod
        def create_from_options(options):
            return fake_detector

    monkeypatch.setattr(_MP_VISION, "PoseLandmarker", _FakePoseLandmarker)
    monkeypatch.setattr(mp, "Image", _FakeImage)
    return fake_detector


# --------------------------------------------------------------------------- #
# T1: mocked unit tests
# --------------------------------------------------------------------------- #
def test_detect_maps_33_image_landmarks_and_flips_bgr_to_rgb(monkeypatch):
    landmarks = [_FakeLandmark(i / 33.0, i / 33.0, visibility=0.9) for i in range(33)]
    result = _FakeResult([landmarks], None)
    captures = []
    _install_fake(monkeypatch, result, captures)

    det = PoseLandmarkerDetector("fake.model")
    bgr = np.zeros((100, 80, 3), dtype=np.uint8)
    bgr[:, :, 2] = 255  # red-position channel only in the BGR input

    pose = det.detect(bgr)

    assert pose is not None
    assert len(pose.landmarks) == 33
    assert all(pose.landmarks[i].visibility == 0.9 for i in range(33))
    # BGR -> RGB: the red-position value must arrive at the detector as red.
    assert captures[0].data[:, :, 0].max() == 255
    assert captures[0].data[:, :, 2].max() == 0


def test_detect_populates_world_landmarks_with_presence_as_visibility(monkeypatch):
    """World landmark visibility: prefers explicit visibility over presence;
    visibility=0.0 must NOT fall through to presence (guards against ``or``)."""
    image_lms = [_FakeLandmark(0.1, 0.1, visibility=0.8) for _ in range(33)]
    # Landmark #0: visibility=0.0, presence=0.7 → expects 0.0 (not 0.7)
    # Landmark #1: visibility=None, presence=0.7 → expects 0.7 (fallback)
    # Landmark #2..32: visibility=None, presence=None → expects 1.0 (no data)
    world_lms = [_FakeLandmark(0.2, 0.2, visibility=0.0, presence=0.7)]
    world_lms += [_FakeLandmark(0.2, 0.2, presence=0.7) for _ in range(1, 2)]
    world_lms += [_FakeLandmark(0.2, 0.2) for _ in range(2, 33)]
    result = _FakeResult([image_lms], [world_lms])
    captures = []
    _install_fake(monkeypatch, result, captures)

    pose = PoseLandmarkerDetector("fake.model").detect(np.zeros((10, 10, 3), dtype=np.uint8))

    assert pose is not None
    assert pose.world_landmarks is not None
    assert len(pose.world_landmarks) == 33
    assert pose.world_landmarks[0].visibility == 0.0  # visibility takes precedence over presence
    assert pose.world_landmarks[1].visibility == 0.7  # None visibility → presence fallback
    assert pose.world_landmarks[2].visibility == 1.0  # no data → default 1.0


def test_detect_returns_none_when_no_person(monkeypatch):
    result = _FakeResult([], None)
    captures = []
    _install_fake(monkeypatch, result, captures)

    pose = PoseLandmarkerDetector("fake.model").detect(np.zeros((10, 10, 3), dtype=np.uint8))

    assert pose is None


def test_detect_returns_none_on_empty_image(monkeypatch):
    result = _FakeResult([[_FakeLandmark(0, 0, 0.5)]], None)
    captures = []
    _install_fake(monkeypatch, result, captures)

    det = PoseLandmarkerDetector("fake.model")
    assert det.detect(None) is None
    assert det.detect(np.empty((0, 0, 3), dtype=np.uint8)) is None


# --------------------------------------------------------------------------- #
# T1b: additional unit tests for the M4 post-review fixes
# --------------------------------------------------------------------------- #
def test_returns_none_on_empty_sublist(monkeypatch):
    """F1/F2 defensive: empty inner sublist is handled without crash.
    - Empty pose_landmarks = [[]] -> no person -> None.
    - Valid pose_landmarks but empty world = [[lm]],[[]] -> person with
      world_landmarks=None (not crash, not empty-dict)."""
    cases: list[tuple[list, list | None, bool]] = [
        ([[]], None, True),       # no outer list -> None
        ([[]], [[]], True),       # both empty -> None
        ([[_FakeLandmark(0, 0, 0.5)]], [[]], False),  # person, no world
    ]
    for pl, pw, expect_none in cases:
        result = _FakeResult(pl, pw)
        captures = []
        _install_fake(monkeypatch, result, captures)
        pose = PoseLandmarkerDetector("fake.model").detect(
            np.zeros((10, 10, 3), dtype=np.uint8)
        )
        if expect_none:
            assert pose is None, f"expected None for pl={pl!r} pw={pw!r}"
        else:
            assert pose is not None, f"expected PoseFrame for pl={pl!r} pw={pw!r}"
            assert pose.world_landmarks is None


def test_detect_rejects_grayscale(monkeypatch):
    """F3: grayscale or single-channel input raises ValueError."""
    captures = []
    _install_fake(monkeypatch, _FakeResult([[]], None), captures)
    det = PoseLandmarkerDetector("fake.model")
    with pytest.raises(ValueError, match="expected HxWx3"):
        det.detect(np.zeros((100, 100), dtype=np.uint8))
    with pytest.raises(ValueError, match="expected HxWx3"):
        det.detect(np.zeros((100, 100, 1), dtype=np.uint8))


def test_world_landmark_zero_presence_does_not_become_one(monkeypatch):
    """F4: presence=0.0 must map to visibility=0.0, not 1.0."""
    image_lms = [_FakeLandmark(0.1, 0.1, visibility=0.8) for _ in range(33)]
    world_lms = [_FakeLandmark(0.2, 0.2, presence=0.0) for _ in range(33)]
    result = _FakeResult([image_lms], [world_lms])
    captures = []
    _install_fake(monkeypatch, result, captures)
    pose = PoseLandmarkerDetector("fake.model").detect(
        np.zeros((10, 10, 3), dtype=np.uint8)
    )
    assert pose is not None
    assert pose.world_landmarks is not None
    assert pose.world_landmarks[0].visibility == 0.0  # NOT 1.0


def test_visibility_clamped_to_unit_interval(monkeypatch):
    """H1: visibility > 1.0 is clamped down; < 0.0 is clamped up."""
    for raw, expected in [(1.5, 1.0), (-0.1, 0.0), (0.5, 0.5)]:
        lms = [_FakeLandmark(0, 0, visibility=raw) for _ in range(33)]
        result = _FakeResult([lms], None)
        captures = []
        _install_fake(monkeypatch, result, captures)
        pose = PoseLandmarkerDetector("fake.model").detect(
            np.zeros((10, 10, 3), dtype=np.uint8)
        )
        assert pose is not None
        assert pose.landmarks[0].visibility == expected, f"raw={raw!r}"


def test_detect_graceful_on_exception(monkeypatch):
    """H2: if MediaPipe raises (model error, OOM, etc.), detect returns None."""
    class _CrashingDetector:
        def detect(self, _):  # noqa: ANN202
            raise RuntimeError("MediaPipe crash")

    class _FakePL:
        @staticmethod
        def create_from_options(_):  # noqa: ANN202
            return _CrashingDetector()

    monkeypatch.setattr(_MP_VISION, "PoseLandmarker", _FakePL)
    monkeypatch.setattr(mp, "Image", _FakeImage)
    pose = PoseLandmarkerDetector("fake.model").detect(
        np.zeros((10, 10, 3), dtype=np.uint8)
    )
    assert pose is None


def test_detect_uses_srgb_format(monkeypatch):
    """M2: the mp.Image is created with SRGB format, not e.g. GRAY."""
    lms = [_FakeLandmark(0, 0, visibility=0.5) for _ in range(33)]
    result = _FakeResult([lms], None)
    captures = []
    _install_fake(monkeypatch, result, captures)
    PoseLandmarkerDetector("fake.model").detect(
        np.zeros((10, 10, 3), dtype=np.uint8)
    )
    assert captures[0].image_format == mp.ImageFormat.SRGB


# --------------------------------------------------------------------------- #
# T2: real detector on a single clip frame
# --------------------------------------------------------------------------- #
@pytest.mark.skipif(not has_model, reason="pose_landmarker_full.task not downloaded")
@pytest.mark.skipif(not has_clip, reason="no extracted clip frames")
def test_real_detector_finds_hip_knee_ankle_on_frame():
    frames = sorted(CLIP_DIR.glob("*.png"))
    image = cv2.imread(str(frames[0]))
    det = PoseLandmarkerDetector(str(MODEL_PATH))

    pose = det.detect(image)

    assert pose is not None
    assert pose.world_landmarks is not None
    assert len(pose.world_landmarks) == 33
    for idx in (23, 25, 27, 24, 26, 28):  # hips, knees, ankles
        assert idx in pose.landmarks
        assert idx in pose.world_landmarks
        assert pose.landmarks[idx].visibility > 0.1


# --------------------------------------------------------------------------- #
# T3: full pipeline over the public clip
# --------------------------------------------------------------------------- #
@pytest.mark.skipif(
    not (has_model and has_clip and has_manifest),
    reason="need model + extracted clip + manifest",
)
def test_pipeline_runs_end_to_end_on_clip():
    """Integration + squat-motion sanity check on a real public clip.

    Asserts:
    - Auto-calibration succeeds on real data.
    - Angle range spans both squat depth (≤100°) and standing (≥120°).
    - Plausible rep count (1–30 for a short clip).

    When ``manifest.json`` contains ``ground_truth_count`` (dual-rater labels
    per ADR-0008, or a labelled dataset such as EJUST-SQUAT-21), a strict
    +/-1 accuracy check is also enforced.
    """
    manifest = json.loads(MANIFEST.read_text())
    ground_truth = manifest.get("ground_truth_count")

    det = PoseLandmarkerDetector(str(MODEL_PATH))
    fe = FeatureExtractor()
    counter = RepCounter()

    angles: list[float] = []
    last = None
    for frame_path in sorted(CLIP_DIR.glob("*.png")):
        image = cv2.imread(str(frame_path))
        pose = det.detect(image)
        if pose is None:
            continue
        feat = fe.update(pose)
        last = counter.update(feat.angle, feat.visibility)
        if feat.angle is not None:
            angles.append(feat.angle)

    assert last is not None
    # Auto-calibration must succeed on real data.
    assert not last.uncalibrated, "pipeline never calibrated on the clip"
    # The clip must show real squat-range knee flexion (descend + stand).
    assert angles, "no usable angle samples on the clip"
    assert min(angles) <= 100.0, "never reached squat depth"
    assert max(angles) >= 120.0, "never reached a standing pose"
    # Plausible rep count for a short clip.
    assert 1 <= last.rep_count <= 30

    if ground_truth is not None:
        assert abs(last.rep_count - ground_truth) <= 1
