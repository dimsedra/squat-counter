import math

import pytest

from repcounter.count import RepCounter
from repcounter.features import FeatureExtractor, interior_angle
from repcounter.types import Landmark, PoseFrame


def _leg(hip, knee, angle_deg, vis, idx_hip, idx_knee, idx_ankle):
    ux, uy = hip[0] - knee[0], hip[1] - knee[1]
    th = math.radians(angle_deg)
    vx = ux * math.cos(th) - uy * math.sin(th)
    vy = ux * math.sin(th) + uy * math.cos(th)
    ankle = (knee[0] + vx, knee[1] + vy)
    return {
        idx_hip: Landmark(hip[0], hip[1], vis),
        idx_knee: Landmark(knee[0], knee[1], vis),
        idx_ankle: Landmark(ankle[0], ankle[1], vis),
    }


def _pose(
    img_left,
    img_right,
    world_left=None,
    world_right=None,
    vis_left=1.0,
    vis_right=1.0,
):
    lm = {}
    lm.update(_leg((0.5, 0.2), (0.5, 0.5), img_left, vis_left, 23, 25, 27))
    lm.update(_leg((0.5, 0.2), (0.5, 0.5), img_right, vis_right, 24, 26, 28))
    wl = {}
    if world_left is not None:
        wl.update(_leg((0.5, 0.2), (0.5, 0.5), world_left, vis_left, 23, 25, 27))
    if world_right is not None:
        wl.update(_leg((0.5, 0.2), (0.5, 0.5), world_right, vis_right, 24, 26, 28))
    return PoseFrame(landmarks=lm, timestamp=0.0, world_landmarks=wl or None)


def test_interior_angle_straight_and_right():
    hip = Landmark(0.5, 0.2, 1.0)
    knee = Landmark(0.5, 0.5, 1.0)
    assert interior_angle(hip, knee, Landmark(0.5, 0.8, 1.0)) == pytest.approx(180.0, abs=1e-6)
    assert interior_angle(hip, knee, Landmark(0.8, 0.5, 1.0)) == pytest.approx(90.0, abs=1e-6)


def test_coincident_points_return_none():
    assert interior_angle(Landmark(0.5, 0.5, 1.0), Landmark(0.5, 0.5, 1.0), Landmark(0.6, 0.5, 1.0)) is None


def test_uses_visible_leg_when_other_occluded():
    features = FeatureExtractor().update(_pose(90, 90, vis_left=0.0, vis_right=1.0))
    assert features.angle == pytest.approx(90.0, abs=1e-6)
    assert features.visibility == pytest.approx(1.0)


def test_averages_both_legs_when_confident():
    features = FeatureExtractor().update(_pose(80, 100, vis_left=1.0, vis_right=1.0))
    assert features.angle == pytest.approx(90.0, abs=1e-6)
    assert features.visibility == pytest.approx(1.0)


def test_leg_averaging_agreement_gate():
    features = FeatureExtractor().update(_pose(170, 10, vis_left=1.0, vis_right=1.0))
    assert abs(features.angle - 90.0) > 20.0


def test_sticky_selection_no_flicker():
    ex = FeatureExtractor()
    f1 = ex.update(_pose(170, 10, vis_left=0.6, vis_right=0.55))
    f2 = ex.update(_pose(170, 10, vis_left=0.55, vis_right=0.6))
    assert abs(f1.angle - f2.angle) < 5.0


def test_single_leg_visibility_output():
    features = FeatureExtractor().update(_pose(100, 100, vis_left=0.0, vis_right=0.6))
    assert features.visibility == pytest.approx(0.6)


def test_min_visibility_boundary():
    at = FeatureExtractor().update(_pose(100, 100, vis_left=0.0, vis_right=0.5))
    assert at.angle is not None
    below = FeatureExtractor().update(_pose(100, 100, vis_left=0.0, vis_right=0.4))
    assert below.angle is None


def test_angle_bounds():
    for angle in [10, 45, 90, 120, 170]:
        features = FeatureExtractor().update(_pose(angle, angle))
        assert 0.0 <= features.angle <= 180.0


def test_first_frame_passthrough():
    assert FeatureExtractor().update(_pose(100, 100)).angle == pytest.approx(100.0)


def test_ema_smooths_small_jitter():
    ex = FeatureExtractor(ema_alpha=0.5)
    f1 = ex.update(_pose(100, 100))
    f2 = ex.update(_pose(96, 96))
    assert f1.angle == pytest.approx(100.0, abs=1e-6)
    assert f2.angle == pytest.approx(98.0, abs=1e-6)


def test_ema_passthrough_on_large_movement():
    ex = FeatureExtractor(ema_alpha=0.5)
    ex.update(_pose(100, 100))
    f2 = ex.update(_pose(70, 70))
    assert f2.angle == pytest.approx(70.0, abs=1e-6)


def test_reset_clears_smoothing():
    ex = FeatureExtractor()
    ex.update(_pose(100, 100))
    ex.update(_pose(80, 80))
    ex.reset()
    assert ex.update(_pose(120, 120)).angle == pytest.approx(120.0)


def test_prefers_world_landmarks():
    ex = FeatureExtractor()
    pose = _pose(90, 90, world_left=80, world_right=80, vis_left=1.0, vis_right=1.0)
    assert ex.update(pose).angle == pytest.approx(80.0, abs=1e-6)


def test_features_to_count_counts_rep():
    ex = FeatureExtractor()
    counter = RepCounter(standing_angle=170.0)
    last = None
    for angle in [170, 120, 80, 120, 170, 170]:
        features = ex.update(_pose(angle, angle))
        last = counter.update(features.angle, features.visibility)
    assert last.rep_count == 1
