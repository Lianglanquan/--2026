from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    config = Path(get_package_share_directory("wheelbot_bridge")) / "config" / "wheel_geometry.yaml"
    return LaunchDescription([
        DeclareLaunchArgument("use_cmd_vel", default_value="false"),
        DeclareLaunchArgument("use_state_adapter", default_value="false"),
        Node(
            package="wheelbot_bridge",
            executable="bridge_node",
            name="wheelbot_bridge",
            output="screen",
            parameters=[{"period": 0.02}],
        ),
        Node(
            package="wheelbot_bridge",
            executable="state_adapter_node",
            name="wheelbot_state_adapter",
            output="screen",
            condition=IfCondition(LaunchConfiguration("use_state_adapter")),
        ),
        Node(
            package="wheelbot_bridge",
            executable="cmd_vel_node",
            name="wheelbot_cmd_vel",
            output="screen",
            parameters=[str(config)],
            condition=IfCondition(LaunchConfiguration("use_cmd_vel")),
        ),
    ])
