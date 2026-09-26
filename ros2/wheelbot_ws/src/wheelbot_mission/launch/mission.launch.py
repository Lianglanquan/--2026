from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    locations = Path(get_package_share_directory("wheelbot_mission")) / "config" / "semantic_locations.yaml"
    dashboard = Path(get_package_share_directory("wheelbot_mission")) / "web" / "index.html"
    return LaunchDescription([
        DeclareLaunchArgument("navigation_mode", default_value="nav2"),
        DeclareLaunchArgument("allow_uncommissioned_locations", default_value="false"),
        DeclareLaunchArgument("api_host", default_value="0.0.0.0"),
        DeclareLaunchArgument("api_port", default_value="8080"),
        DeclareLaunchArgument("api_token", default_value="change-me-before-deploy"),
        DeclareLaunchArgument("navigation_timeout_s", default_value="300.0"),
        DeclareLaunchArgument("arm_timeout_s", default_value="180.0"),
        DeclareLaunchArgument("robot_state_timeout_s", default_value="2.0"),
        DeclareLaunchArgument("require_robot_state", default_value="true"),
        DeclareLaunchArgument("fail_on_robot_fault", default_value="true"),
        DeclareLaunchArgument("feedback_webhook_url", default_value=""),
        DeclareLaunchArgument("feedback_webhook_token", default_value=""),
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
                "navigation_timeout_s": LaunchConfiguration("navigation_timeout_s"),
                "arm_timeout_s": LaunchConfiguration("arm_timeout_s"),
                "robot_state_timeout_s": LaunchConfiguration("robot_state_timeout_s"),
                "require_robot_state": LaunchConfiguration("require_robot_state"),
                "fail_on_robot_fault": LaunchConfiguration("fail_on_robot_fault"),
                "dashboard_file": str(dashboard),
                "feedback_webhook_url": LaunchConfiguration("feedback_webhook_url"),
                "feedback_webhook_token": LaunchConfiguration("feedback_webhook_token"),
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
