from types import SimpleNamespace

from wheelbot_bridge.bridge_node import WheelbotBridge
from wheelbot_bridge.robot_protocol import decode_command


class Port:
    is_open = True

    def __init__(self):
        self.frames = []

    def write(self, frame):
        self.frames.append(frame)

    def flush(self):
        pass


def test_ros_command_is_written_as_binary_wb_frame():
    port = Port()
    bridge = SimpleNamespace(port=port, sequence=9)
    message = SimpleNamespace(
        enable=True, mode="wheel", joint_target=[0.0] * 4,
        wheel_command=[45.0, -45.0],
    )

    WheelbotBridge.command_callback(bridge, message)

    sequence, command = decode_command(port.frames[0])
    assert sequence == 9
    assert command.enable and command.mode == 2
    assert command.wheel_command == (45.0, -45.0)
    assert bridge.sequence == 10
