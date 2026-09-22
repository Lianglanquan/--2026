from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from ament_index_python.packages import get_package_share_directory
from launch.substitutions import LaunchConfiguration
from pathlib import Path


def generate_launch_description():
    config = Path(get_package_share_directory("wheelbot_mapping")) / "config" / "mapper_params_online_sync.yaml"
    return LaunchDescription([
        DeclareLaunchArgument("slam_params_file", default_value=str(config)),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                str(Path(get_package_share_directory("slam_toolbox")) / "launch" / "online_sync_launch.py")
            ),
            launch_arguments={
                "slam_params_file": LaunchConfiguration("slam_params_file"),
                "autostart": "true",
                "use_lifecycle_manager": "false",
                "use_sim_time": "false",
            }.items(),
        ),
    ])
