"""Pure state-conversion helpers shared by real and fake ROS inputs."""

from dataclasses import dataclass
import math
from typing import Sequence


def quaternion_wxyz_to_xyzw(quaternion: Sequence[float]) -> tuple[float, float, float, float]:
    if len(quaternion) != 4:
        raise ValueError("quaternion must contain four values")
    w, x, y, z = (float(value) for value in quaternion)
    return x, y, z, w


@dataclass(frozen=True)
class WheelOdomSample:
    x_m: float
    y_m: float
    yaw_rad: float
    linear_x_mps: float
    angular_z_rps: float
    has_valid_motion: bool
    yaw_covariance: float


class WheelOdometer:
    """Integrate configured wheel velocities into a planar odometry estimate."""

    def __init__(
        self,
        radius_m: float,
        track_m: float,
        wheel_indices: Sequence[int],
        wheel_signs: Sequence[float],
    ) -> None:
        if radius_m <= 0.0 or track_m <= 0.0:
            raise ValueError("wheel radius and track must be positive")
        if not wheel_indices or len(wheel_indices) != len(wheel_signs):
            raise ValueError("wheel indices and signs must describe at least one wheel")
        if any(int(index) < 0 for index in wheel_indices):
            raise ValueError("wheel indices must be non-negative")
        if any(float(sign) == 0.0 for sign in wheel_signs):
            raise ValueError("wheel signs must be non-zero")

        self.radius_m = float(radius_m)
        self.track_m = float(track_m)
        self.wheel_indices = tuple(int(index) for index in wheel_indices)
        self.wheel_signs = tuple(float(sign) for sign in wheel_signs)
        self.x_m = 0.0
        self.y_m = 0.0
        self.yaw_rad = 0.0
        self._last_stamp_s: float | None = None

    def update(self, wheel_velocity_rpm: Sequence[float], stamp_s: float) -> WheelOdomSample:
        if len(wheel_velocity_rpm) <= max(self.wheel_indices):
            raise ValueError("wheel velocity array is shorter than configured wheel indices")

        if self._last_stamp_s is None:
            self._last_stamp_s = float(stamp_s)
            return self._sample(0.0, 0.0, False)

        dt_s = float(stamp_s) - self._last_stamp_s
        self._last_stamp_s = float(stamp_s)
        if dt_s <= 0.0:
            return self._sample(0.0, 0.0, False)

        wheel_linear_mps = tuple(
            float(wheel_velocity_rpm[index])
            * (2.0 * math.pi / 60.0)
            * self.radius_m
            * sign
            for index, sign in zip(self.wheel_indices, self.wheel_signs)
        )
        if len(wheel_linear_mps) == 1:
            linear_x_mps = wheel_linear_mps[0]
            angular_z_rps = 0.0
            yaw_covariance = 1_000.0
        else:
            left_mps, right_mps = wheel_linear_mps[:2]
            linear_x_mps = (left_mps + right_mps) / 2.0
            angular_z_rps = (right_mps - left_mps) / self.track_m
            yaw_covariance = 0.05

        if abs(angular_z_rps) < 1e-9:
            self.x_m += linear_x_mps * math.cos(self.yaw_rad) * dt_s
            self.y_m += linear_x_mps * math.sin(self.yaw_rad) * dt_s
        else:
            next_yaw = self.yaw_rad + angular_z_rps * dt_s
            radius = linear_x_mps / angular_z_rps
            self.x_m += radius * (math.sin(next_yaw) - math.sin(self.yaw_rad))
            self.y_m -= radius * (math.cos(next_yaw) - math.cos(self.yaw_rad))
            self.yaw_rad = math.atan2(math.sin(next_yaw), math.cos(next_yaw))

        return self._sample(linear_x_mps, angular_z_rps, True, yaw_covariance)

    def _sample(
        self,
        linear_x_mps: float,
        angular_z_rps: float,
        has_valid_motion: bool,
        yaw_covariance: float = 0.05,
    ) -> WheelOdomSample:
        return WheelOdomSample(
            x_m=self.x_m,
            y_m=self.y_m,
            yaw_rad=self.yaw_rad,
            linear_x_mps=linear_x_mps,
            angular_z_rps=angular_z_rps,
            has_valid_motion=has_valid_motion,
            yaw_covariance=yaw_covariance,
        )
