"""Translate Nav2 Twist intent into the C board's commissioned wheel order."""

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node
from wheelbot_interfaces.msg import RobotCommand

from wheelbot_bridge.wheel_command import twist_to_rpm


class CmdVelNode(Node):
    def __init__(self):
        super().__init__("wheelbot_cmd_vel")
        self.declare_parameter("wheel_radius_m", 0.0)
        self.declare_parameter("wheel_track_m", 0.0)
        self.declare_parameter("motor_signs", [1, 1])
        self.radius = float(self.get_parameter("wheel_radius_m").value)
        self.track = float(self.get_parameter("wheel_track_m").value)
        self.signs = tuple(int(x) for x in self.get_parameter("motor_signs").value)
        twist_to_rpm(0.0, 0.0, self.radius, self.track, self.signs)
        self.publisher = self.create_publisher(RobotCommand, "/wheelbot/command", 10)
        self.create_subscription(Twist, "/cmd_vel", self.on_twist, 10)

    def on_twist(self, twist):
        command = RobotCommand()
        command.enable = True
        command.mode = "wheel"
        command.joint_target = [0.0] * 4
        command.wheel_command = list(twist_to_rpm(
            twist.linear.x, twist.angular.z, self.radius, self.track, self.signs
        ))
        self.publisher.publish(command)


def main(args=None):
    rclpy.init(args=args)
    node = CmdVelNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
