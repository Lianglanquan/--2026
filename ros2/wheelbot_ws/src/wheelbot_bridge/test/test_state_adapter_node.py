import math

from builtin_interfaces.msg import Time
from nav_msgs.msg import Odometry
import pytest
from sensor_msgs.msg import BatteryState, Imu, JointState
from wheelbot_interfaces.msg import RobotState

from wheelbot_bridge.state_adapter_node import (
    fill_imu_message,
    fill_wheel_odom_message,
    fill_joint_message,
    fill_battery_message,
    wheel_feedback_valid,
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


def test_joint_feedback_degrees_are_published_in_radians():
    state = RobotState()
    state.joint_position = [0.0, 90.0, -90.0, 180.0]
    state.joint_velocity = [0.0, 45.0, -45.0, 90.0]
    state.joint_status = [0, 0, 0, 0]
    joint = JointState()
    fill_joint_message(state, joint, Time(sec=1))
    assert joint.name == ["ha8_lf", "ha8_lr", "ha8_rf", "ha8_rr"]
    assert joint.position == pytest.approx([0.0, 1.5707963268, -1.5707963268, 3.1415926536])
    assert joint.velocity == pytest.approx([0.0, 0.7853981634, -0.7853981634, 1.5707963268])


def test_unavailable_servo_does_not_publish_a_false_zero():
    state = RobotState()
    state.joint_status = [0, 255, 0, 0]
    joint = JointState()
    fill_joint_message(state, joint, Time())
    assert math.isnan(joint.position[1])


def test_battery_reports_measured_voltage_without_inventing_soc():
    state = RobotState()
    state.battery_voltage = 24.2
    battery = BatteryState()
    fill_battery_message(state, battery, Time(sec=2))
    assert battery.voltage == pytest.approx(24.2)
    assert battery.percentage != battery.percentage


def test_wheel_feedback_fault_is_checked_only_for_configured_indices():
    assert wheel_feedback_valid(1 << 5, (0,))
    assert not wheel_feedback_valid(1 << 4, (0,))
    assert not wheel_feedback_valid(1 << 5, (0, 1))
