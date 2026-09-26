from pathlib import Path

from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    urdf = Path(__file__).parent.parent / 'urdf' / 'wheelbot.urdf'
    return LaunchDescription([
        Node(package='robot_state_publisher',
             executable='robot_state_publisher',
             arguments=[str(urdf)],
             output='screen'),
    ])
