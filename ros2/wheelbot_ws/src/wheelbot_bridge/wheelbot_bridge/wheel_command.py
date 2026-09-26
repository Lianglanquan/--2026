"""Explicit wheel geometry conversion for the commissioned QD4310 pair."""

import math


def twist_to_rpm(linear_x, angular_z, radius_m, track_m, motor_signs):
    if radius_m <= 0 or track_m <= 0:
        raise ValueError("wheel radius and track must be positive measured values")
    if len(motor_signs) != 2 or any(sign not in (-1, 1) for sign in motor_signs):
        raise ValueError("motor_signs must contain two values of +1 or -1")
    if not all(math.isfinite(x) for x in (linear_x, angular_z, radius_m, track_m)):
        raise ValueError("wheel command values must be finite")
    factor = 60.0 / (2.0 * math.pi * radius_m)
    left = (linear_x - angular_z * track_m / 2.0) * factor * motor_signs[0]
    right = (linear_x + angular_z * track_m / 2.0) * factor * motor_signs[1]
    return left, right
