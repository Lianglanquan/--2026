import pytest

from wheelbot_bridge.robot_protocol import (
    RobotCommand,
    RobotState,
    decode_command,
    decode_state,
    encode_command,
    encode_state,
    command_from_ros,
)


def test_command_dataclass_round_trips_as_wb_binary_frame():
    command = RobotCommand(True, 2, (0.1, 0.2, 0.3, 0.4), (1.0, -2.0))

    sequence, decoded = decode_command(encode_command(7, command))

    assert sequence == 7
    assert decoded.enable == command.enable
    assert decoded.mode == command.mode
    assert decoded.joint_target == pytest.approx(command.joint_target)
    assert decoded.wheel_command == pytest.approx(command.wheel_command)


def test_state_dataclass_round_trips_complete_c_layout():
    state = RobotState(
        timestamp_ms=1234,
        gyro=(1.0, 2.0, 3.0), accel=(4.0, 5.0, 6.0),
        quaternion=(1.0, 0.0, 0.0, 0.0), rpy=(0.1, 0.2, 0.3),
        joint_position=(0.1, 0.2, 0.3, 0.4),
        joint_velocity=(1.1, 1.2, 1.3, 1.4), joint_status=(1, 2, 3, 4),
        wheel_position=(10.0, 20.0), wheel_velocity=(11.0, 21.0),
        wheel_current=(12.0, 22.0), wheel_fault=(0x11, 0x22),
        battery_voltage=24.5, faults=9,
    )

    sequence, decoded = decode_state(encode_state(9, state))

    assert sequence == 9
    assert decoded.timestamp_ms == state.timestamp_ms
    for field in ("gyro", "accel", "quaternion", "rpy", "joint_position", "joint_velocity",
                  "wheel_position", "wheel_velocity", "wheel_current"):
        assert getattr(decoded, field) == pytest.approx(getattr(state, field))
    assert decoded.joint_status == state.joint_status
    assert decoded.wheel_fault == state.wheel_fault
    assert decoded.battery_voltage == pytest.approx(state.battery_voltage)
    assert decoded.faults == state.faults


def test_command_rejects_wrong_fixed_array_sizes():
    with pytest.raises(ValueError, match="4 joints and 2 wheels"):
        RobotCommand(False, 0, (0.0,), (0.0, 0.0))

    with pytest.raises(ValueError, match="4 joints and 2 wheels"):
        RobotCommand(False, 0, (0.0,) * 4, (0.0,))


def test_decoder_rejects_corrupt_crc_and_wrong_type():
    command = RobotCommand(False, 0, (0.0,) * 4, (0.0, 0.0))
    frame = bytearray(encode_command(0, command))
    frame[-1] ^= 0xFF
    with pytest.raises(ValueError, match="crc"):
        decode_command(bytes(frame))
    with pytest.raises(ValueError, match="message type"):
        decode_state(encode_command(0, command))


def test_ros_command_mode_maps_to_wire_enum():
    class Message:
        enable = True
        mode = "combined"
        joint_target = [0.1, 0.2, 0.3, 0.4]
        wheel_command = [12.0, -12.0]

    _, decoded = decode_command(encode_command(3, command_from_ros(Message())))
    assert decoded.mode == 3
    assert decoded.wheel_command == pytest.approx((12.0, -12.0))


def test_command_rejects_nonfinite_and_unknown_mode():
    with pytest.raises(ValueError, match="mode"):
        RobotCommand(True, 255, (0.0,) * 4, (0.0,) * 2)
    with pytest.raises(ValueError, match="finite"):
        RobotCommand(True, 2, (float("nan"),) * 4, (0.0,) * 2)
