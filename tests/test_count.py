import math

import pytest

from repcounter.count import RepCounter
from repcounter.types import RepState

from conftest import feed


def test_full_cycle_counts_one_rep():
    c = RepCounter(standing_angle=170.0)
    steps = feed(c, [170, 140, 100, 70, 100, 140, 170])
    assert steps[-1].rep_count == 1
    assert steps[-1].rep_event is not None
    assert steps[-1].rep_event.depth_angle == 70


def test_hysteresis_no_double_count():
    c = RepCounter(standing_angle=170.0)
    steps = feed(c, [170, 140, 100, 95, 101, 95, 100, 140, 170])
    assert steps[-1].rep_count == 1


def test_partial_not_counted_but_flagged():
    c = RepCounter(standing_angle=170.0)
    steps = feed(c, [170, 140, 120, 140, 170])
    assert steps[-1].rep_count == 0
    assert steps[-1].partial is True


def test_dropout_pauses_and_resumes():
    c = RepCounter(standing_angle=170.0)
    c.update(170)
    c.update(120)
    paused = c.update(120, visibility=0.1)
    assert paused.paused is True
    assert paused.state is RepState.DESCENDING
    assert paused.rep_count == 0
    steps = feed(c, [120, 80, 120, 170])
    assert steps[-1].rep_count == 1


def test_calibration_sets_baseline():
    c = RepCounter()
    c.calibrate(171.0)
    steps = feed(c, [100, 70, 100, 171, 171])
    assert steps[-1].rep_count == 1


def test_full_rep_marks_is_full():
    c = RepCounter(standing_angle=170.0)
    steps = feed(c, [170, 120, 80, 170, 170])
    assert steps[-1].rep_count == 1
    assert steps[-1].rep_event.is_full is True
    assert steps[-1].rep_event.depth_angle == 80


def test_multiple_reps_reset_state():
    c = RepCounter(standing_angle=170.0)
    angles = []
    for _ in range(3):
        angles += [170, 120, 80, 170, 170]
    steps = feed(c, angles)
    assert steps[-1].rep_count == 3
    assert steps[-1].partial is False


def test_rep_depth_independent_across_reps():
    c = RepCounter(standing_angle=170.0)
    steps1 = feed(c, [170, 120, 80, 170, 170])
    assert steps1[-1].rep_event.depth_angle == 80
    steps2 = feed(c, [170, 120, 95, 170, 170])
    assert steps2[-1].rep_count == 2
    assert steps2[-1].rep_event.depth_angle == 95


def test_descending_without_depth_recovers():
    c = RepCounter(standing_angle=170.0)
    feed(c, [170, 140, 120])
    recovered = c.update(170)
    assert recovered.partial is True
    assert recovered.rep_count == 0
    steps = feed(c, [120, 80, 120, 170, 170])
    assert steps[-1].rep_count == 1


def test_standing_oscillation_no_double_count():
    c = RepCounter(standing_angle=170.0)
    assert feed(c, [170, 100, 70, 100, 170, 170])[-1].rep_count == 1
    more = feed(c, [150, 170, 150, 170])
    assert more[-1].rep_count == 1
    assert more[-1].partial is True


def test_angle_exactly_at_standing_exit_counts():
    c = RepCounter(standing_angle=170.0)
    steps = feed(c, [170, 100, 70, 100, 160, 160])
    assert steps[-1].rep_count == 1


def test_dropout_during_bottom():
    c = RepCounter(standing_angle=170.0)
    feed(c, [170, 100, 70])
    paused = c.update(70, visibility=0.1)
    assert paused.paused is True
    assert paused.state is RepState.BOTTOM
    steps = feed(c, [70, 110, 170, 170])
    assert steps[-1].rep_count == 1


def test_dropout_during_ascending():
    c = RepCounter(standing_angle=170.0)
    feed(c, [170, 100, 70])
    c.update(110)
    paused = c.update(130, visibility=0.1)
    assert paused.paused is True
    assert paused.state is RepState.ASCENDING
    steps = feed(c, [150, 170, 170])
    assert steps[-1].rep_count == 1


def test_parallel_rep_not_full():
    c = RepCounter(standing_angle=170.0)
    steps = feed(c, [170, 120, 95, 170, 170])
    assert steps[-1].rep_count == 1
    assert steps[-1].rep_event.is_full is False
    assert steps[-1].rep_event.depth_angle == 95


def test_full_boundary_at_90_not_full():
    c = RepCounter(standing_angle=170.0)
    steps = feed(c, [170, 120, 90, 170, 170])
    assert steps[-1].rep_event.is_full is False
    assert steps[-1].rep_event.depth_angle == 90


def test_bottom_at_exactly_threshold_counts():
    c = RepCounter(standing_angle=170.0)
    steps = feed(c, [170, 120, 100, 170, 170])
    assert steps[-1].rep_count == 1
    assert steps[-1].rep_event.depth_angle == 100


def test_invalid_angle_pauses_and_resumes():
    c = RepCounter(standing_angle=170.0)
    c.update(170)
    assert c.update(float("nan")).paused is True
    assert c.update(-20).paused is True
    assert c.update(170).paused is False


def test_visibility_boundary_pauses():
    c = RepCounter(standing_angle=170.0)
    c.update(170)
    assert c.update(120, visibility=0.5).paused is True
    assert c.update(120, visibility=0.55).paused is True
    assert c.update(120, visibility=0.7).paused is False


def test_auto_calibrates_from_standing_frames():
    c = RepCounter()
    steps = feed(c, [150, 150, 150, 150, 150])
    assert steps[-1].uncalibrated is False
    steps = feed(c, [150, 110, 80, 110, 150, 150])
    assert steps[-1].rep_count == 1


def test_no_count_while_uncalibrated():
    c = RepCounter()
    steps = feed(c, [150, 100, 70, 100, 150, 150])
    assert steps[-1].uncalibrated is True
    assert steps[-1].rep_count == 0


def test_calibrate_ignored_mid_rep():
    c = RepCounter(standing_angle=170.0)
    c.update(170)
    c.update(120)
    c.calibrate(150)
    assert c._standing_angle == 170.0
    assert c.uncalibrated is False
    steps = feed(c, [80, 120, 170, 170])
    assert steps[-1].rep_count == 1


def test_constructor_rejects_degenerate_standing():
    with pytest.raises(ValueError):
        RepCounter(standing_angle=100)


def test_calibrate_rejects_degenerate_standing():
    c = RepCounter(standing_angle=170.0)
    with pytest.raises(ValueError):
        c.calibrate(100)
