import serial
import time
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from wheelbot_interfaces.msg import RobotCommand, RobotState

from wheelbot_bridge.robot_protocol import decode_state, encode_command
from wheelbot_bridge.usb_protocol import drain_serial_buffer


class WheelbotBridge(Node):
    def __init__(self):
        super().__init__('wheelbot_bridge')
        self.declare_parameter('device', '/dev/wheelbot')
        self.declare_parameter('baud', 115200)
        self.declare_parameter('period', 0.02)
        self.pub = self.create_publisher(String, 'wheelbot/status', 10)
        self.state_pub = self.create_publisher(RobotState, 'wheelbot/state', 10)
        self.command_sub = self.create_subscription(RobotCommand, 'wheelbot/command', self.command_callback, 10)
        self.sequence = 0
        self.rx_buffer = bytearray()
        self.port = None
        self.last_pong = False
        self.next_ping_s = 0.0
        self.timer = self.create_timer(float(self.get_parameter('period').value), self.poll)

    def poll(self):
        try:
            if self.port is None or not self.port.is_open:
                self.port = serial.Serial(
                    str(self.get_parameter('device').value),
                    int(self.get_parameter('baud').value),
                    timeout=0.01,
                )
                self.next_ping_s = 0.0
            now = time.monotonic()
            if now >= self.next_ping_s:
                self.port.write(b'PING\n')
                self.port.flush()
                self.next_ping_s = now + 1.0
            deadline = now + 0.015
            while time.monotonic() < deadline:
                waiting = self.port.in_waiting
                data = self.port.read(waiting if waiting else 1)
                if not data:
                    break
                self.rx_buffer.extend(data)
            frames, lines = drain_serial_buffer(self.rx_buffer)
            self.last_pong = b'PONG' in lines
            msg = String()
            if frames:
                msg.data = 'STATE'
            elif self.last_pong:
                msg.data = 'PONG'
            elif lines:
                msg.data = 'unexpected:' + lines[-1].decode(errors='replace')
            else:
                msg.data = 'timeout'
            self.pub.publish(msg)
            self._publish_state_frames(frames)
        except (serial.SerialException, OSError) as exc:
            if self.port is not None:
                self.port.close()
            self.port = None
            msg = String(); msg.data = 'disconnected:' + str(exc)
            self.pub.publish(msg)

    def command_callback(self, command):
        if self.port is None or not self.port.is_open:
            return
        from wheelbot_bridge.robot_protocol import RobotCommand
        frame = encode_command(self.sequence, RobotCommand(
            enable=command.enable, mode=command.mode,
            joint_target=tuple(command.joint_target),
            wheel_command=tuple(command.wheel_command)))
        self.sequence = (self.sequence + 1) & 0xffff
        try:
            self.port.write(frame)
            self.port.flush()
        except (serial.SerialException, OSError):
            self.port.close()
            self.port = None

    def _publish_state_frames(self, frames):
        for frame in frames:
            try:
                _, state = decode_state(frame)
            except ValueError:
                continue
            msg = RobotState()
            msg.header.stamp = self.get_clock().now().to_msg()
            msg.mode = 'real'; msg.cboard_link = 'up'
            for field in ('gyro', 'accel', 'quaternion', 'rpy', 'joint_position',
                          'joint_velocity', 'joint_status', 'wheel_position',
                          'wheel_velocity', 'wheel_current', 'wheel_fault'):
                setattr(msg, field, list(getattr(state, field)))
            msg.battery_voltage = state.battery_voltage; msg.faults = state.faults
            self.state_pub.publish(msg)

    def destroy_node(self):
        if self.port is not None:
            self.port.close()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = WheelbotBridge()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()
