"""Typed Python view of the C board's WB v1 binary protocol."""

from dataclasses import dataclass
import math
import struct

from wheelbot_bridge.usb_protocol import (
    MSG_COMMAND,
    MSG_STATE,
    decode_frame,
    encode_frame,
)


COMMAND_PAYLOAD = struct.Struct("<BB4f2f")
MODES = {"idle": 0, "joint": 1, "wheel": 2, "combined": 3}
# Must remain byte-for-byte compatible with wheelbot_state_t in C.
STATE_PAYLOAD = struct.Struct("<I3f3f4f3f4f4f4B2f2f2f2IfI")


def _check_count(values, count, label):
    if len(values) != count:
        raise ValueError(f"{label} must contain exactly {count} values")


@dataclass(frozen=True)
class RobotCommand:
    enable: bool
    mode: int
    joint_target: tuple[float, ...]
    wheel_command: tuple[float, ...]

    def __post_init__(self):
        _check_count(self.joint_target, 4, "command must contain exactly 4 joints and 2 wheels")
        _check_count(self.wheel_command, 2, "command must contain exactly 4 joints and 2 wheels")
        if self.mode not in MODES.values():
            raise ValueError("unknown command mode")
        if not all(math.isfinite(v) for v in (*self.joint_target, *self.wheel_command)):
            raise ValueError("command values must be finite")


def command_from_ros(message):
    if message.mode not in MODES:
        raise ValueError(f"unknown command mode: {message.mode}")
    return RobotCommand(
        bool(message.enable), MODES[message.mode],
        tuple(message.joint_target), tuple(message.wheel_command),
    )


@dataclass(frozen=True)
class RobotState:
    timestamp_ms: int
    gyro: tuple[float, ...]
    accel: tuple[float, ...]
    quaternion: tuple[float, ...]
    rpy: tuple[float, ...]
    joint_position: tuple[float, ...]
    joint_velocity: tuple[float, ...]
    joint_status: tuple[int, ...]
    wheel_position: tuple[float, ...]
    wheel_velocity: tuple[float, ...]
    wheel_current: tuple[float, ...]
    wheel_fault: tuple[int, ...]
    battery_voltage: float
    faults: int

    def __post_init__(self):
        for values, count, label in (
            (self.gyro, 3, "gyro"), (self.accel, 3, "accel"),
            (self.quaternion, 4, "quaternion"), (self.rpy, 3, "rpy"),
            (self.joint_position, 4, "joint_position"),
            (self.joint_velocity, 4, "joint_velocity"),
            (self.joint_status, 4, "joint_status"),
            (self.wheel_position, 2, "wheel_position"),
            (self.wheel_velocity, 2, "wheel_velocity"),
            (self.wheel_current, 2, "wheel_current"),
            (self.wheel_fault, 2, "wheel_fault"),
        ):
            _check_count(values, count, label)


def encode_command(sequence: int, command: RobotCommand) -> bytes:
    payload = COMMAND_PAYLOAD.pack(
        int(command.enable), int(command.mode), *command.joint_target, *command.wheel_command
    )
    return encode_frame(MSG_COMMAND, sequence, payload)


def decode_command(frame: bytes) -> tuple[int, RobotCommand]:
    sequence, _, payload = decode_frame(frame, MSG_COMMAND)
    values = COMMAND_PAYLOAD.unpack(payload)
    return sequence, RobotCommand(bool(values[0]), values[1], tuple(values[2:6]), tuple(values[6:8]))


def encode_state(sequence: int, state: RobotState) -> bytes:
    payload = STATE_PAYLOAD.pack(
        state.timestamp_ms, *state.gyro, *state.accel, *state.quaternion, *state.rpy,
        *state.joint_position, *state.joint_velocity, *state.joint_status,
        *state.wheel_position, *state.wheel_velocity, *state.wheel_current,
        *state.wheel_fault, state.battery_voltage, state.faults,
    )
    return encode_frame(MSG_STATE, sequence, payload)


def decode_state(frame: bytes) -> tuple[int, RobotState]:
    sequence, _, payload = decode_frame(frame, MSG_STATE)
    values = STATE_PAYLOAD.unpack(payload)
    i = 0
    timestamp_ms = values[i]; i += 1
    fields = {}
    for key, count in (("gyro", 3), ("accel", 3), ("quaternion", 4), ("rpy", 3),
                       ("joint_position", 4), ("joint_velocity", 4)):
        fields[key] = tuple(values[i:i + count]); i += count
    fields["joint_status"] = tuple(values[i:i + 4]); i += 4
    for key in ("wheel_position", "wheel_velocity", "wheel_current", "wheel_fault"):
        count = 2
        fields[key] = tuple(values[i:i + count]); i += count
    battery_voltage = values[i]; faults = values[i + 1]
    return sequence, RobotState(timestamp_ms, battery_voltage=battery_voltage, faults=faults, **fields)
