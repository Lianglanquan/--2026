import math

import pytest

from wheelbot_bridge.state_adapter import WheelOdometer, quaternion_wxyz_to_xyzw


def test_quaternion_wxyz_is_reordered_for_ros_xyzw():
    assert quaternion_wxyz_to_xyzw((0.9, 0.1, 0.2, 0.3)) == pytest.approx((0.1, 0.2, 0.3, 0.9))


def test_first_sample_has_no_motion_until_a_delta_exists():
    odometer = WheelOdometer(0.1, 0.4, (0, 1), (1.0, 1.0))

    sample = odometer.update((60.0, 60.0), 1.0)

    assert sample.has_valid_motion is False
    assert sample.linear_x_mps == 0.0
    assert sample.angular_z_rps == 0.0


def test_two_wheel_straight_motion_integrates_forward_pose():
    odometer = WheelOdometer(0.1, 0.4, (0, 1), (1.0, 1.0))
    odometer.update((0.0, 0.0), 0.0)

    sample = odometer.update((60.0, 60.0), 1.0)

    expected_speed = 2.0 * math.pi * 0.1
    assert sample.has_valid_motion is True
    assert sample.linear_x_mps == pytest.approx(expected_speed)
    assert sample.angular_z_rps == pytest.approx(0.0)
    assert sample.x_m == pytest.approx(expected_speed)
    assert sample.y_m == pytest.approx(0.0)


def test_two_wheel_opposite_motion_integrates_in_place_rotation():
    odometer = WheelOdometer(0.1, 0.4, (0, 1), (1.0, 1.0))
    odometer.update((0.0, 0.0), 0.0)

    sample = odometer.update((-60.0, 60.0), 1.0)

    expected_angular_speed = (2.0 * math.pi * 0.1 * 2.0) / 0.4
    assert sample.linear_x_mps == pytest.approx(0.0)
    assert sample.angular_z_rps == pytest.approx(expected_angular_speed)
    assert sample.yaw_rad == pytest.approx(expected_angular_speed)


def test_single_wheel_motion_does_not_claim_yaw_observability():
    odometer = WheelOdometer(0.1, 0.4, (0,), (1.0,))
    odometer.update((0.0,), 0.0)

    sample = odometer.update((60.0,), 1.0)

    assert sample.linear_x_mps == pytest.approx(2.0 * math.pi * 0.1)
    assert sample.angular_z_rps == pytest.approx(0.0)
    assert sample.yaw_covariance > 100.0


def test_invalid_wheel_configuration_is_rejected():
    with pytest.raises(ValueError, match="wheel indices"):
        WheelOdometer(0.1, 0.4, (), ())
