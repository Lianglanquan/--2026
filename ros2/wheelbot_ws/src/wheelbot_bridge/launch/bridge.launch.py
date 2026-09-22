from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(
            package="wheelbot_bridge",
            executable="bridge_node",
            name="wheelbot_bridge",
            output="screen",
            parameters=[{"period": 0.02}],
        ),
    ])
