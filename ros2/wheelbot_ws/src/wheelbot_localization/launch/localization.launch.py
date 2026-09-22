from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    share = Path(get_package_share_directory("wheelbot_localization"))
    return LaunchDescription([
        Node(
            package="wheelbot_bridge",
            executable="state_adapter_node",
            name="wheelbot_state_adapter",
            output="screen",
            parameters=[str(share / "config" / "robot_kinematics.yaml")],
        ),
        Node(
            package="robot_localization",
            executable="ekf_node",
            name="ekf_filter_node",
            output="screen",
            parameters=[str(share / "config" / "ekf.yaml")],
        ),
    ])
