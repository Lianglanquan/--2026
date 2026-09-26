import math

import pytest

from wheelbot_bridge.wheel_command import twist_to_rpm


def test_forward_twist_maps_to_both_motor_rpms():
    rpm = twist_to_rpm(2 * math.pi * 0.1, 0.0, 0.1, 0.4, (1, -1))
    assert rpm == pytest.approx((60.0, -60.0))


def test_turn_twist_maps_to_opposite_wheels():
    assert twist_to_rpm(0.0, 1.0, 0.1, 0.4, (1, 1)) == pytest.approx(
        (-0.2 / (2 * math.pi * 0.1) * 60, 0.2 / (2 * math.pi * 0.1) * 60)
    )


def test_unmeasured_geometry_is_rejected():
    with pytest.raises(ValueError, match="positive"):
        twist_to_rpm(1.0, 0.0, 0.0, 0.4, (1, 1))
