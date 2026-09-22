"""Convert WheelBot's project state message into standard ROS sensor messages."""

import math

import rclpy
from builtin_interfaces.msg import Time
from nav_msgs.msg import Odometry
from rclpy.node import Node
from sensor_msgs.msg import Imu
from wheelbot_interfaces.msg import RobotState

from wheelbot_bridge.state_adapter import WheelOdometer, quaternion_wxyz_to_xyzw


def fill_imu_message(state: RobotState, message: Imu, frame_id: str, stamp: Time) -> None:
    message.header.stamp = stamp
    message.header.frame_id = frame_id
    x, y, z, w = quaternion_wxyz_to_xyzw(state.quaternion)
    message.orientation.x = float(x)
    message.orientation.y = float(y)
    message.orientation.z = float(z)
    message.orientation.w = float(w)
    message.angular_velocity.x = float(state.gyro[0])
    message.angular_velocity.y = float(state.gyro[1])
    message.angular_velocity.z = float(state.gyro[2])
    message.linear_acceleration.x = float(state.accel[0])
    message.linear_acceleration.y = float(state.accel[1])
    message.linear_acceleration.z = float(state.accel[2])
    message.orientation_covariance = [0.05, 0.0, 0.0, 0.0, 0.05, 0.0, 0.0, 0.0, 0.05]
    message.angular_velocity_covariance = [0.02, 0.0, 0.0, 0.0, 0.02, 0.0, 0.0, 0.0, 0.02]
    message.linear_acceleration_covariance = [0.1, 0.0, 0.0, 0.0, 0.1, 0.0, 0.0, 0.0, 0.1]


def fill_wheel_odom_message(
    sample,
    message: Odometry,
    odom_frame: str,
    base_frame: str,
    stamp: Time,
) -> None:
    message.header.stamp = stamp
    message.header.frame_id = odom_frame
    message.child_frame_id = base_frame
    message.pose.pose.position.x = sample.x_m
    message.pose.pose.position.y = sample.y_m
    message.pose.pose.orientation.z = math.sin(sample.yaw_rad / 2.0)
    message.pose.pose.orientation.w = math.cos(sample.yaw_rad / 2.0)
    message.twist.twist.linear.x = sample.linear_x_mps
    message.twist.twist.angular.z = sample.angular_z_rps
    message.pose.covariance[0] = 0.1 if sample.has_valid_motion else 100.0
    message.pose.covariance[7] = 0.1 if sample.has_valid_motion else 100.0
    message.pose.covariance[35] = sample.yaw_covariance
    message.twist.covariance[0] = 0.05 if sample.has_valid_motion else 100.0
    message.twist.covariance[35] = sample.yaw_covariance


class StateAdapterNode(Node):
    def __init__(self) -> None:
        super().__init__("wheelbot_state_adapter")
        self.declare_parameter("imu_frame", "imu_link")
        self.declare_parameter("odom_frame", "odom")
        self.declare_parameter("base_frame", "base_link")
        self.declare_parameter("wheel_radius_m", 0.1)
        self.declare_parameter("wheel_track_m", 0.4)
        self.declare_parameter("wheel_indices", [0])
        self.declare_parameter("wheel_signs", [1.0])

        self.imu_frame = str(self.get_parameter("imu_frame").value)
        self.odom_frame = str(self.get_parameter("odom_frame").value)
        self.base_frame = str(self.get_parameter("base_frame").value)
        wheel_indices = tuple(int(value) for value in self.get_parameter("wheel_indices").value)
        wheel_signs = tuple(float(value) for value in self.get_parameter("wheel_signs").value)
        self.odometer = WheelOdometer(
            float(self.get_parameter("wheel_radius_m").value),
            float(self.get_parameter("wheel_track_m").value),
            wheel_indices,
            wheel_signs,
        )
        self._warned_single_wheel = False
        self.imu_pub = self.create_publisher(Imu, "/imu/data", 10)
        self.odom_pub = self.create_publisher(Odometry, "/wheelbot/wheel_odom", 10)
        self.state_sub = self.create_subscription(
            RobotState, "/wheelbot/state", self.state_callback, 10
        )

    def state_callback(self, state: RobotState) -> None:
        stamp = self.get_clock().now().to_msg()
        imu = Imu()
        fill_imu_message(state, imu, self.imu_frame, stamp)
        self.imu_pub.publish(imu)

        sample = self.odometer.update(state.wheel_velocity, stamp.sec + stamp.nanosec * 1e-9)
        odom = Odometry()
        fill_wheel_odom_message(sample, odom, self.odom_frame, self.base_frame, stamp)
        self.odom_pub.publish(odom)
        if len(self.odometer.wheel_indices) == 1 and not self._warned_single_wheel:
            self.get_logger().warning(
                "Only one wheel feedback index is enabled; yaw odometry is unobservable "
                "until wheel_indices contains both wheels."
            )
            self._warned_single_wheel = True


def main(args=None):
    rclpy.init(args=args)
    node = StateAdapterNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
