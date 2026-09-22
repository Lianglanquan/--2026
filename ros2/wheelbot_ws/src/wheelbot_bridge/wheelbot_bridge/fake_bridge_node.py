import math

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu, JointState

from wheelbot_interfaces.msg import RobotState


class FakeBridgeNode(Node):
    """无 C 板时的 Dummy/Fake 模式：发布假 RobotState / joint_states / imu。"""

    def __init__(self):
        super().__init__('fake_bridge')
        self.state_pub = self.create_publisher(RobotState, '/wheelbot/state', 10)
        self.joint_pub = self.create_publisher(JointState, '/joint_states', 10)
        self.imu_pub = self.create_publisher(Imu, '/imu', 10)
        self.joint_names = ['hip_lf', 'hip_rf', 'hip_lb', 'hip_rb']
        self.declare_parameter('fake_wheel_rpm', 0.0)
        self.t = 0.0
        self.wheel_angle = 0.0
        self.timer = self.create_timer(0.02, self.tick)

    def tick(self):
        now = self.get_clock().now().to_msg()
        self.t += 0.02

        state = RobotState()
        state.header.stamp = now
        state.mode = 'fake'
        state.cboard_link = 'down'
        state.battery_voltage = 24.0
        state.gyro = [0.0, 0.0, 0.0]
        state.accel = [0.0, 0.0, 9.81]
        state.quaternion = [1.0, 0.0, 0.0, 0.0]
        wheel_rpm = float(self.get_parameter('fake_wheel_rpm').value)
        self.wheel_angle += wheel_rpm * 2.0 * math.pi / 60.0 * 0.02
        state.wheel_position = [self.wheel_angle, self.wheel_angle]
        state.wheel_velocity = [wheel_rpm, wheel_rpm]
        state.wheel_fault = [0, 0]
        self.state_pub.publish(state)

        joint = JointState()
        joint.header.stamp = now
        joint.name = self.joint_names
        joint.position = [0.2 * math.sin(self.t + i) for i in range(4)]
        joint.velocity = [0.2 * math.cos(self.t + i) for i in range(4)]
        self.joint_pub.publish(joint)

        imu = Imu()
        imu.header.stamp = now
        imu.orientation.w = 1.0
        imu.angular_velocity.z = 0.05 * math.sin(self.t)
        imu.linear_acceleration.z = 9.81
        self.imu_pub.publish(imu)


def main(args=None):
    rclpy.init(args=args)
    node = FakeBridgeNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()
