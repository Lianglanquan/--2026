"""Shared policy-to-actuator contract for MuJoCo and the real robot.

The policy works with normalized actions.  Hardware adapters are responsible
for converting the returned command into HA8 UART frames and QD4310 CAN/USB
frames; MuJoCo uses the same physical command values.
"""

from dataclasses import dataclass

import numpy as np


ACTION_SIZE = 6
POLICY_HZ = 50
WHEEL_RADIUS_M = 0.033
QD4310_SPEED_LIMIT_RPM = 50.0
QD4310_CURRENT_LIMIT_A = 1.65
HA8_ACTION_RANGE_RAD = 0.35
NOMINAL_STAND_BASE_Z_M = 0.106744
NOMINAL_STAND_JOINT_TARGET_RAD = np.zeros(4, dtype=np.float32)
# The source URDF mirrors the two wheel joint axes. With world +X as
# robot-forward, positive policy speed is +Y-axis rotation on the left and
# -Y-axis rotation on the right.
WHEEL_MUJOCO_SIGN = np.array([1.0, -1.0], dtype=np.float32)

JOINT_NAMES = (
    "LT_joint",
    "LC_joint",
    "RT_joint",
    "RC_joint",
)
WHEEL_NAMES = ("LW_joint", "RW_joint")


@dataclass(frozen=True)
class ActuatorCommand:
    """Physical-unit command shared by simulation and hardware adapters."""

    joint_target_rad: np.ndarray
    wheel_speed_rpm: np.ndarray
    qd4310_current_limit_a: float = QD4310_CURRENT_LIMIT_A


def command_to_mujoco_ctrl(command: ActuatorCommand) -> np.ndarray:
    """Convert the shared physical command to MuJoCo actuator controls."""

    if command.joint_target_rad.shape != (4,) or command.wheel_speed_rpm.shape != (2,):
        raise ValueError("invalid actuator command shape")
    wheel_speed_rad_s = (
        command.wheel_speed_rpm
        * (2.0 * np.pi / 60.0)
        * WHEEL_MUJOCO_SIGN
    )
    return np.concatenate((command.joint_target_rad, wheel_speed_rad_s)).astype(
        np.float32
    )


def action_to_command(action: np.ndarray, nominal_joint_target_rad=None) -> ActuatorCommand:
    """Map one normalized policy action to bounded physical commands.

    The first four entries are position offsets around a nominal pose.  The
    last two entries are QD4310 wheel speed commands in rpm.
    """

    values = np.asarray(action, dtype=np.float32)
    if values.shape != (ACTION_SIZE,):
        raise ValueError(f"expected action shape {(ACTION_SIZE,)}, got {values.shape}")
    if not np.all(np.isfinite(values)):
        raise ValueError("action contains non-finite values")
    values = np.clip(values, -1.0, 1.0)
    if nominal_joint_target_rad is None:
        nominal_joint_target_rad = NOMINAL_STAND_JOINT_TARGET_RAD
    nominal = np.asarray(nominal_joint_target_rad, dtype=np.float32)
    if nominal.shape != (4,):
        raise ValueError("nominal_joint_target_rad must have shape (4,)")
    return ActuatorCommand(
        joint_target_rad=nominal + values[:4] * HA8_ACTION_RANGE_RAD,
        wheel_speed_rpm=values[4:] * QD4310_SPEED_LIMIT_RPM,
    )
