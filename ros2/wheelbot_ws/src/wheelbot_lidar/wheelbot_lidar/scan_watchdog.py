"""Restart the YDLIDAR service when the ROS scan stream stalls."""

from __future__ import annotations

import subprocess
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import LaserScan
from wheelbot_lidar.scan_watchdog_policy import ScanHealthMonitor


class ScanWatchdog(Node):
    def __init__(self) -> None:
        super().__init__("wheelbot_scan_watchdog")
        self.declare_parameter("scan_topic", "/scan")
        self.declare_parameter("service_name", "ydlidar-x2.service")
        self.declare_parameter("check_period_s", 0.25)
        self.declare_parameter("scan_timeout_s", 1.5)
        self.declare_parameter("startup_grace_s", 10.0)
        self.declare_parameter("restart_cooldown_s", 15.0)

        now = time.monotonic()
        self.service_name = str(self.get_parameter("service_name").value)
        self.monitor = ScanHealthMonitor(
            started_at=now,
            timeout_s=float(self.get_parameter("scan_timeout_s").value),
            startup_grace_s=float(self.get_parameter("startup_grace_s").value),
            restart_cooldown_s=float(self.get_parameter("restart_cooldown_s").value),
        )
        scan_topic = str(self.get_parameter("scan_topic").value)
        self.subscription = self.create_subscription(
            LaserScan,
            scan_topic,
            self._scan_callback,
            qos_profile_sensor_data,
        )
        self.timer = self.create_timer(
            float(self.get_parameter("check_period_s").value), self._check_callback
        )
        self.get_logger().info(
            f"Watching {scan_topic}; restart {self.service_name} "
            f"after {self.monitor.timeout_s:.1f}s without a scan"
        )

    def _scan_callback(self, _message: LaserScan) -> None:
        self.monitor.record_scan(time.monotonic())

    def _check_callback(self) -> None:
        now = time.monotonic()
        if not self.monitor.restart_due(now):
            return
        self.monitor.mark_restart(now)
        self.get_logger().error(
            f"No LaserScan received for {self.monitor.timeout_s:.1f}s; "
            f"restarting {self.service_name}"
        )
        result = subprocess.run(
            ["/usr/bin/systemctl", "restart", self.service_name],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            self.get_logger().error(
                f"Failed to restart {self.service_name} (exit {result.returncode}): "
                f"{result.stderr.strip()}"
            )


def main(args=None) -> None:
    rclpy.init(args=args)
    node = ScanWatchdog()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
