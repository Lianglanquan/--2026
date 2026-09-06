import serial
import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class WheelbotBridge(Node):
    def __init__(self):
        super().__init__('wheelbot_bridge')
        self.declare_parameter('device', '/dev/wheelbot')
        self.declare_parameter('baud', 115200)
        self.declare_parameter('period', 1.0)
        self.pub = self.create_publisher(String, 'wheelbot/status', 10)
        self.port = None
        self.timer = self.create_timer(float(self.get_parameter('period').value), self.poll)

    def poll(self):
        try:
            if self.port is None or not self.port.is_open:
                self.port = serial.Serial(str(self.get_parameter('device').value), int(self.get_parameter('baud').value), timeout=0.2)
            self.port.write(b'PING\n')
            reply = self.port.readline().strip()
            msg = String()
            msg.data = 'PONG' if reply == b'PONG' else 'unexpected:' + reply.decode(errors='replace')
            self.pub.publish(msg)
        except (serial.SerialException, OSError) as exc:
            if self.port is not None:
                self.port.close()
            self.port = None
            msg = String(); msg.data = 'disconnected:' + str(exc)
            self.pub.publish(msg)

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
