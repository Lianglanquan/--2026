from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    config = Path(get_package_share_directory("wheelbot_mapping")) / "config" / "mapper_params_online_sync.yaml"
    return LaunchDescription([
        DeclareLaunchArgument("slam_params_file", default_value=str(config)),
        Node(
            package="slam_toolbox",
            executable="sync_slam_toolbox_node",
            name="slam_toolbox",
            output="screen",
            parameters=[LaunchConfiguration("slam_params_file")],
        ),
    ])
