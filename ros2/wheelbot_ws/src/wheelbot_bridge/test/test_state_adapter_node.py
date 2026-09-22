from builtin_interfaces.msg import Time
from nav_msgs.msg import Odometry
import pytest
from sensor_msgs.msg import Imu
from wheelbot_interfaces.msg import RobotState

from wheelbot_bridge.state_adapter_node import (
    fill_imu_message,
    fill_wheel_odom_message,
)
from wheelbot_bridge.state_adapter import WheelOdomSample


def test_fill_imu_message_maps_c_board_wxyz_and_sensor_fields():
    state = RobotState()
    state.quaternion = [0.9, 0.1, 0.2, 0.3]
    state.gyro = [1.0, 2.0, 3.0]
    state.accel = [4.0, 5.0, 6.0]
    message = Imu()
    stamp = Time(sec=12, nanosec=34)

    fill_imu_message(state, message, "imu_link", stamp)

    assert message.header.frame_id == "imu_link"
    assert message.header.stamp == stamp
    assert [message.orientation.x, message.orientation.y,
            message.orientation.z, message.orientation.w] == pytest.approx([0.1, 0.2, 0.3, 0.9])
    assert [message.angular_velocity.x, message.angular_velocity.y,
            message.angular_velocity.z] == pytest.approx([1.0, 2.0, 3.0])
    assert [message.linear_acceleration.x, message.linear_acceleration.y,
            message.linear_acceleration.z] == pytest.approx([4.0, 5.0, 6.0])


def test_fill_imu_message_accepts_generated_float32_arrays():
    state = RobotState()
    state.gyro = [1.0, 2.0, 3.0]
    state.accel = [4.0, 5.0, 6.0]
    state.quaternion = [1.0, 0.0, 0.0, 0.0]

    message = Imu()
    fill_imu_message(state, message, "imu_link", Time())

    assert message.angular_velocity.z == pytest.approx(3.0)
    assert message.linear_acceleration.z == pytest.approx(6.0)


def test_fill_wheel_odom_message_sets_frames_pose_and_twist():
    message = Odometry()
    sample = WheelOdomSample(
        x_m=1.5,
        y_m=-0.2,
        yaw_rad=0.25,
        linear_x_mps=0.4,
        angular_z_rps=-0.1,
        has_valid_motion=True,
        yaw_covariance=0.05,
    )
    stamp = Time(sec=8, nanosec=9)

    fill_wheel_odom_message(sample, message, "odom", "base_link", stamp)

    assert message.header.frame_id == "odom"
    assert message.child_frame_id == "base_link"
    assert message.header.stamp == stamp
    assert message.pose.pose.position.x == 1.5
    assert message.pose.pose.position.y == -0.2
    assert message.twist.twist.linear.x == 0.4
    assert message.twist.twist.angular.z == -0.1
    assert message.pose.covariance[35] == 0.05
