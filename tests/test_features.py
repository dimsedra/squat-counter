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


def _pose(angle_left, angle_right, vis_left=1.0, vis_right=1.0):
    lm = {}
    lm.update(_leg((0.5, 0.2), (0.5, 0.5), angle_left, vis_left, 23, 25, 27))
    lm.update(_leg((0.5, 0.2), (0.5, 0.5), angle_right, vis_right, 24, 26, 28))
    return PoseFrame(landmarks=lm, timestamp=0.0)


def test_interior_angle_straight_and_right():
    hip = Landmark(0.5, 0.2, 1.0)
    knee = Landmark(0.5, 0.5, 1.0)
    assert interior_angle(hip, knee, Landmark(0.5, 0.8, 1.0)) == pytest.approx(180.0, abs=1e-6)
    assert interior_angle(hip, knee, Landmark(0.8, 0.5, 1.0)) == pytest.approx(90.0, abs=1e-6)


def test_uses_visible_leg_when_other_occluded():
    pose = _pose(90, 90, vis_left=0.0, vis_right=1.0)
    features = FeatureExtractor().update(pose)
    assert features.angle == pytest.approx(90.0, abs=1e-6)
    assert features.visibility == pytest.approx(1.0)


def test_averages_both_legs_when_confident():
    pose = _pose(80, 100, vis_left=1.0, vis_right=1.0)
    features = FeatureExtractor().update(pose)
    assert features.angle == pytest.approx(90.0, abs=1e-6)
    assert features.visibility == pytest.approx(1.0)


def test_ema_smooths():
    ex = FeatureExtractor(ema_alpha=0.5)
    f1 = ex.update(_pose(100, 100))
    f2 = ex.update(_pose(80, 80))
    assert f1.angle == pytest.approx(100.0, abs=1e-6)
    assert f2.angle == pytest.approx(90.0, abs=1e-6)


def test_z_ignored():
    ex_a = FeatureExtractor()
    ex_b = FeatureExtractor()
    angle_a = ex_a.update(_pose(90, 90)).angle
    angle_b = ex_b.update(_pose(90, 90)).angle
    assert angle_a == pytest.approx(angle_b, abs=1e-9)


def test_no_leg_returns_unreliable():
    pose = _pose(90, 90, vis_left=0.0, vis_right=0.0)
    features = FeatureExtractor().update(pose)
    assert features.angle is None
    assert features.visibility < 0.5


def test_features_to_count_counts_rep():
    ex = FeatureExtractor(ema_alpha=1.0)
    counter = RepCounter(standing_angle=170.0)
    last = None
    for angle in [170, 120, 80, 120, 170, 170]:
        features = ex.update(_pose(angle, angle, vis_left=1.0, vis_right=1.0))
        last = counter.update(features.angle, features.visibility)
    assert last.rep_count == 1
