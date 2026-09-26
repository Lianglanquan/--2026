from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    locations = Path(get_package_share_directory("wheelbot_mission")) / "config" / "semantic_locations.yaml"
    return LaunchDescription([
        DeclareLaunchArgument("navigation_mode", default_value="nav2"),
        DeclareLaunchArgument("allow_uncommissioned_locations", default_value="false"),
        DeclareLaunchArgument("api_host", default_value="0.0.0.0"),
        DeclareLaunchArgument("api_port", default_value="8080"),
        DeclareLaunchArgument("api_token", default_value="change-me-before-deploy"),
        DeclareLaunchArgument("use_fake_arm", default_value="false"),
        Node(
            package="wheelbot_mission",
            executable="mission_manager_node",
            name="wheelbot_mission_manager",
            output="screen",
            parameters=[{
                "locations_file": str(locations),
                "state_file": "missions.json",
                "navigation_mode": LaunchConfiguration("navigation_mode"),
                "allow_uncommissioned_locations": LaunchConfiguration("allow_uncommissioned_locations"),
                "api_host": LaunchConfiguration("api_host"),
                "api_port": LaunchConfiguration("api_port"),
                "api_token": LaunchConfiguration("api_token"),
            }],
        ),
        Node(
            package="wheelbot_mission",
            executable="fake_arm_node",
            name="wheelbot_fake_arm",
            output="screen",
            condition=IfCondition(LaunchConfiguration("use_fake_arm")),
        ),
    ])
