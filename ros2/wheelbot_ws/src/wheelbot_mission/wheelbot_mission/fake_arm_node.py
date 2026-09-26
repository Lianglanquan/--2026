"""Test-only manipulator service double for end-to-end mission bring-up."""

import json

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class FakeArmNode(Node):
    def __init__(self):
        super().__init__("wheelbot_fake_arm")
        self.declare_parameter("delay_s", 0.5)
        self.publisher = self.create_publisher(String, "/wheelbot/arm/task_results", 10)
        self.create_subscription(String, "/wheelbot/arm/task_requests", self._on_request, 10)
        self._timers = []

    def _publish(self, mission_id: str, status: str) -> None:
        msg = String()
        msg.data = json.dumps({"mission_id": mission_id, "status": status})
        self.publisher.publish(msg)

    def _on_request(self, msg: String) -> None:
        try:
            mission_id = str(json.loads(msg.data)["mission_id"])
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            self.get_logger().warning(f"ignored invalid fake arm request: {exc}")
            return
        self._publish(mission_id, "ACCEPTED")
        timer = None

        def finish():
            self._publish(mission_id, "SUCCEEDED")
            timer.cancel()
            self._timers.remove(timer)

        timer = self.create_timer(max(0.01, float(self.get_parameter("delay_s").value)), finish)
        self._timers.append(timer)


def main(args=None):
    rclpy.init(args=args)
    node = FakeArmNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
