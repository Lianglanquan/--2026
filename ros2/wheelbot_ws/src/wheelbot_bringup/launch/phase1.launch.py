from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def _include(package, launch_file, condition):
    path = Path(get_package_share_directory(package)) / "launch" / launch_file
    return IncludeLaunchDescription(
        PythonLaunchDescriptionSource(str(path)),
        condition=IfCondition(LaunchConfiguration(condition)),
    )


def generate_launch_description():
    arguments = [
        DeclareLaunchArgument("use_real_bridge", default_value="false"),
        DeclareLaunchArgument("use_fake_bridge", default_value="true"),
        DeclareLaunchArgument("use_lidar", default_value="false"),
        DeclareLaunchArgument("use_ekf", default_value="true"),
        DeclareLaunchArgument("use_slam", default_value="false"),
        DeclareLaunchArgument("use_description", default_value="true"),
        DeclareLaunchArgument("fake_wheel_rpm", default_value="0.0"),
    ]
    fake_bridge = Node(
        package="wheelbot_bridge",
        executable="fake_bridge_node",
        name="fake_bridge",
        output="screen",
        parameters=[{"fake_wheel_rpm": LaunchConfiguration("fake_wheel_rpm")}],
        condition=IfCondition(LaunchConfiguration("use_fake_bridge")),
    )
    return LaunchDescription(arguments + [
        fake_bridge,
        _include("wheelbot_bridge", "bridge.launch.py", "use_real_bridge"),
        _include("wheelbot_description", "sensors.launch.py", "use_description"),
        _include("wheelbot_lidar", "x2.launch.py", "use_lidar"),
        _include("wheelbot_localization", "localization.launch.py", "use_ekf"),
        _include("wheelbot_mapping", "mapping.launch.py", "use_slam"),
    ])
