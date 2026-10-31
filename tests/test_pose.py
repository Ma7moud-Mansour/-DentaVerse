"""Synthetic coordinates test calibration math, never gesture accuracy evidence."""
import pytest

from backend.pose import PoseTracker


def body(offset=0, right_visibility=1):
    points = [{"x": 0.5, "y": 0.5, "visibility": 1.0} for _ in range(33)]
    points[11].update(x=0.35 + offset, y=0.3)
    points[12].update(x=0.65 + offset, y=0.3)
    points[15].update(x=0.2, y=0.6)
    points[16].update(x=0.8, y=0.6, visibility=right_visibility)
    return points


def test_calibration_requires_stable_samples_over_time():
    tracker = PoseTracker()
    tracker.observe(body(), 0)
    tracker.begin_calibration(0)
    tracker.observe(body(), 0.01)
    assert not tracker.calibrated
    for step in range(1, 20):
        tracker.observe(body(), step * 0.05)
    assert tracker.calibrated and tracker.progress == 1
    assert tracker.origin == pytest.approx((0.5, 0.3))
    assert tracker.normalized_wrist() == pytest.approx((1, 1))


def test_moving_shoulders_do_not_calibrate_and_timeout_is_retryable():
    tracker = PoseTracker()
    tracker.observe(body(), 0)
    tracker.begin_calibration(0)
    for step in range(1, 41):
        tracker.observe(body(offset=0.09 if step % 2 else -0.09), step * 0.05)
    assert not tracker.calibrated
    tracker.observe(body(), 8.1)
    assert tracker.started is None and "timed out" in tracker.error
    tracker.begin_calibration(9)
    assert tracker.error is None


def test_preferred_wrist_visibility_and_smoothing_reset_on_loss():
    tracker = PoseTracker()
    tracker.observe(body(right_visibility=0.1), 0)
    assert not tracker.ready and tracker.wrist is None
    with pytest.raises(ValueError, match="shoulders"):
        tracker.begin_calibration(0)
    tracker.set_hand("left")
    tracker.observe(body(right_visibility=0.1), 0.1)
    assert tracker.ready and tracker.wrist == (0.2, 0.6)
    tracker.observe([], 0.2)
    assert tracker.wrist is None and not tracker.ready
    tracker.observe(body(), 0.3)
    assert tracker.wrist == (0.2, 0.6)


def test_display_is_mirrored_without_changing_anatomical_hand():
    tracker = PoseTracker("left")
    tracker.observe(body(), 0)
    tracker.origin, tracker.scale = (0.5, 0.3), 0.3
    preview = tracker.preview([(-1, 1)], 1.27)
    assert preview["landmarks"][15]["x"] == pytest.approx(0.8)
    assert preview["trail"][0] == pytest.approx((0.8, 0.6))
    assert body()[15]["x"] == 0.2
    assert preview["capture_elapsed"] == 1.3
