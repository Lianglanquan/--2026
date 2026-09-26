"""ROS 2 Mission Manager: high-level tasks to Nav2 and arm service boundaries."""

from __future__ import annotations

import json
import math
import threading
import time
from pathlib import Path

import rclpy
import yaml
from action_msgs.msg import GoalStatus
from geometry_msgs.msg import PoseStamped
from nav2_msgs.action import NavigateToPose
from nav_msgs.msg import Odometry
from rclpy.action import ActionClient
from rclpy.node import Node
from std_msgs.msg import String
from wheelbot_interfaces.msg import RobotState

from .events import MissionEventBroker
from .feedback import FeedbackWebhook
from .http_api import MissionHttpServer
from .model import Mission, MissionState, MissionStore, MissionType
from .safety import evaluate_mission_safety


class MissionManagerNode(Node):
    def __init__(self):
        super().__init__("wheelbot_mission_manager")
        self.declare_parameter("locations_file", "")
        self.declare_parameter("state_file", "missions.json")
        self.declare_parameter("api_host", "0.0.0.0")
        self.declare_parameter("api_port", 8080)
        self.declare_parameter("api_token", "change-me-before-deploy")
        self.declare_parameter("navigation_mode", "nav2")
        self.declare_parameter("fake_navigation_delay_s", 0.25)
        self.declare_parameter("allow_uncommissioned_locations", False)
        self.declare_parameter("navigation_timeout_s", 300.0)
        self.declare_parameter("arm_timeout_s", 180.0)
        self.declare_parameter("robot_state_timeout_s", 2.0)
        self.declare_parameter("require_robot_state", True)
        self.declare_parameter("fail_on_robot_fault", True)
        self.declare_parameter("dashboard_file", "")
        self.declare_parameter("feedback_webhook_url", "")
        self.declare_parameter("feedback_webhook_token", "")
        self.declare_parameter("feedback_webhook_timeout_s", 3.0)

        self.status_pub = self.create_publisher(String, "/wheelbot/mission/status", 20)
        self.arm_request_pub = self.create_publisher(String, "/wheelbot/arm/task_requests", 10)
        self.arm_cancel_pub = self.create_publisher(String, "/wheelbot/arm/cancel", 10)
        self.create_subscription(String, "/wheelbot/arm/task_results", self._on_arm_result, 10)
        self.create_subscription(Odometry, "/odometry/filtered", self._on_odometry, 10)
        self.create_subscription(RobotState, "/wheelbot/state", self._on_robot_state, 10)
        self._telemetry_lock = threading.RLock()
        self._pose = None
        self._pose_update = 0.0
        self._robot = None
        self._robot_update = 0.0
        self._phase_lock = threading.RLock()
        self._phase_deadline = 0.0
        self._phase_mission_id = None

        self.events = MissionEventBroker()
        self.feedback = FeedbackWebhook(
            str(self.get_parameter("feedback_webhook_url").value),
            str(self.get_parameter("feedback_webhook_token").value),
            float(self.get_parameter("feedback_webhook_timeout_s").value),
            log=lambda message: self.get_logger().warning(message),
        )
        self.store = MissionStore(
            str(self.get_parameter("state_file").value), on_change=self._on_mission_change
        )
        self.locations = self._load_locations(str(self.get_parameter("locations_file").value))
        self.navigation_mode = str(self.get_parameter("navigation_mode").value)
        if self.navigation_mode not in {"nav2", "fake"}:
            raise ValueError("navigation_mode must be 'nav2' or 'fake'")
        self.nav_client = ActionClient(self, NavigateToPose, "navigate_to_pose")
        self._goal_handle = None
        self._goal_mission_id = None
        self._pending_goal_mission_id = None
        self._dispatched_mission_id = None
        self._fake_timer = None
        self._fake_mission_id = None
        self.create_timer(0.1, self._tick)

        self.http = MissionHttpServer(
            str(self.get_parameter("api_host").value),
            int(self.get_parameter("api_port").value),
            str(self.get_parameter("api_token").value),
            self.store,
            self._on_cancel,
            self._system_status,
            self.events,
            str(self.get_parameter("dashboard_file").value),
        )
        self.http.start()
        self.get_logger().info(f"mission API listening on {self.http.address[0]}:{self.http.address[1]}")

    def _on_odometry(self, msg: Odometry) -> None:
        q = msg.pose.pose.orientation
        yaw = math.atan2(2.0 * (q.w * q.z + q.x * q.y),
                         1.0 - 2.0 * (q.y * q.y + q.z * q.z))
        with self._telemetry_lock:
            self._pose = {
                "frame_id": msg.header.frame_id,
                "x": msg.pose.pose.position.x,
                "y": msg.pose.pose.position.y,
                "yaw": yaw,
            }
            self._pose_update = time.monotonic()

    def _on_robot_state(self, msg: RobotState) -> None:
        with self._telemetry_lock:
            self._robot = {
                "mode": msg.mode,
                "cboard_link": msg.cboard_link,
                "battery_voltage": msg.battery_voltage,
                "faults": msg.faults,
            }
            self._robot_update = time.monotonic()

    def _system_status(self) -> dict[str, object]:
        now = time.monotonic()
        active = self.store.active()
        visible_mission = active or self.store.latest()
        with self._telemetry_lock:
            pose = dict(self._pose) if self._pose else None
            robot = dict(self._robot) if self._robot else None
            pose_fresh = pose is not None and now - self._pose_update <= 2.0
            robot_fresh = robot is not None and now - self._robot_update <= 1.0
        return {
            "robot_pose": pose,
            "robot_pose_fresh": pose_fresh,
            "robot": robot,
            "robot_state_fresh": robot_fresh,
            "mission": visible_mission.to_dict() if visible_mission else None,
            "navigation_state": active.state if active and active.state in {
                MissionState.NAVIGATING.value,
                MissionState.RETURNING.value,
            } else "IDLE",
            "arm_state": active.state if active and active.state in {
                MissionState.WAITING_FOR_ARM.value,
                MissionState.ARM_RUNNING.value,
                MissionState.LOADED.value,
            } else "IDLE",
            "perception": {"status": "unavailable"},
        }

    def _load_locations(self, filename: str) -> dict[str, dict[str, object]]:
        if not filename:
            raise ValueError("locations_file is required")
        data = yaml.safe_load(Path(filename).read_text(encoding="utf-8")) or {}
        locations = data.get("locations")
        if not isinstance(locations, dict) or not locations:
            raise ValueError("locations_file must define a non-empty locations map")
        return locations

    def _on_mission_change(self, mission: Mission) -> None:
        msg = String()
        msg.data = json.dumps(mission.to_dict(), ensure_ascii=False)
        self.status_pub.publish(msg)
        self.events.publish(mission)
        self.feedback.publish(mission)
        timeout_s = 0.0
        if mission.state_enum in {MissionState.NAVIGATING, MissionState.RETURNING}:
            timeout_s = float(self.get_parameter("navigation_timeout_s").value)
        elif mission.state_enum in {MissionState.WAITING_FOR_ARM, MissionState.ARM_RUNNING}:
            timeout_s = float(self.get_parameter("arm_timeout_s").value)
        with self._phase_lock:
            self._phase_mission_id = mission.mission_id if timeout_s > 0 else None
            self._phase_deadline = time.monotonic() + timeout_s if timeout_s > 0 else 0.0

    def _tick(self) -> None:
        mission = self.store.active()
        if mission is None:
            return
        if self._safety_failed(mission):
            return
        if mission.state_enum != MissionState.PENDING:
            return
        if mission.mission_id == self._dispatched_mission_id:
            return
        self._dispatched_mission_id = mission.mission_id
        if mission.type_enum == MissionType.RETURN_HOME:
            self._start_navigation(mission, mission.return_location, returning=True)
        else:
            self._start_navigation(mission, mission.target_location, returning=False)

    def _safety_failed(self, mission: Mission) -> bool:
        now = time.monotonic()
        with self._telemetry_lock:
            robot = dict(self._robot) if self._robot else None
            robot_age = now - self._robot_update if robot is not None else float("inf")

        with self._phase_lock:
            timed_out = (
                self._phase_mission_id == mission.mission_id
                and self._phase_deadline > 0
                and now >= self._phase_deadline
            )
        failure = evaluate_mission_safety(
            mission.state_enum,
            require_robot_state=bool(self.get_parameter("require_robot_state").value),
            robot=robot,
            robot_age_s=robot_age,
            robot_timeout_s=float(self.get_parameter("robot_state_timeout_s").value),
            fail_on_robot_fault=bool(self.get_parameter("fail_on_robot_fault").value),
            phase_timed_out=timed_out,
        )
        if failure is None:
            return False
        self._fail_mission(mission, failure.detail, failure.error_code)
        return True

    def _fail_mission(self, mission: Mission, detail: str, error_code: str) -> None:
        if self._goal_handle is not None and self._goal_mission_id == mission.mission_id:
            self._goal_handle.cancel_goal_async()
            self._goal_handle = None
            self._goal_mission_id = None
        if self._fake_timer is not None and self._fake_mission_id == mission.mission_id:
            self._fake_timer.cancel()
            self._fake_timer = None
            self._fake_mission_id = None
        if mission.state_enum in {MissionState.WAITING_FOR_ARM, MissionState.ARM_RUNNING}:
            msg = String()
            msg.data = json.dumps({"mission_id": mission.mission_id})
            self.arm_cancel_pub.publish(msg)
        self.store.transition(mission.mission_id, MissionState.FAILED, detail, error_code)

    def _pose_for(self, location_name: str) -> PoseStamped:
        raw = self.locations.get(location_name)
        if not isinstance(raw, dict):
            raise ValueError(f"unknown semantic location: {location_name}")
        commissioned = bool(raw.get("commissioned", False))
        if not commissioned and not bool(self.get_parameter("allow_uncommissioned_locations").value):
            raise ValueError(f"semantic location is not commissioned: {location_name}")
        pose = PoseStamped()
        pose.header.frame_id = str(raw.get("frame_id", "map"))
        pose.header.stamp = self.get_clock().now().to_msg()
        pose.pose.position.x = float(raw["x"])
        pose.pose.position.y = float(raw["y"])
        pose.pose.orientation.z = float(raw.get("qz", 0.0))
        pose.pose.orientation.w = float(raw.get("qw", 1.0))
        return pose

    def _start_navigation(self, mission: Mission, location: str, returning: bool) -> None:
        try:
            pose = self._pose_for(location)
            state = MissionState.RETURNING if returning else MissionState.NAVIGATING
            self.store.transition(mission.mission_id, state, f"navigating to {location}")
        except (KeyError, ValueError) as exc:
            self.store.transition(mission.mission_id, MissionState.FAILED, str(exc), "LOCATION_INVALID")
            return

        if self.navigation_mode == "fake":
            delay = float(self.get_parameter("fake_navigation_delay_s").value)
            self._fake_mission_id = mission.mission_id
            self._fake_timer = self.create_timer(
                max(0.01, delay), lambda: self._finish_fake_navigation(mission.mission_id, returning)
            )
            return
        if not self.nav_client.wait_for_server(timeout_sec=1.0):
            self.store.transition(
                mission.mission_id, MissionState.FAILED, "Nav2 action server unavailable", "NAV2_OFFLINE"
            )
            return
        goal = NavigateToPose.Goal()
        goal.pose = pose
        self._pending_goal_mission_id = mission.mission_id
        future = self.nav_client.send_goal_async(goal)
        future.add_done_callback(
            lambda value: self._on_goal_response(value, mission.mission_id, returning)
        )

    def _finish_fake_navigation(self, mission_id: str, returning: bool) -> None:
        if self._fake_timer is not None and self._fake_mission_id == mission_id:
            self._fake_timer.cancel()
            self._fake_timer = None
            self._fake_mission_id = None
        mission = self.store.get(mission_id)
        if mission is None or mission.terminal:
            return
        self._navigation_succeeded(mission, returning)

    def _on_goal_response(self, future, mission_id: str, returning: bool) -> None:
        self._pending_goal_mission_id = None
        try:
            goal_handle = future.result()
        except Exception as exc:
            mission = self.store.get(mission_id)
            if mission is not None and not mission.terminal:
                self.store.transition(
                    mission_id, MissionState.FAILED, f"Nav2 goal request failed: {exc}", "NAV_ERROR"
                )
            return
        mission = self.store.get(mission_id)
        if mission is None or mission.terminal:
            if goal_handle.accepted:
                goal_handle.cancel_goal_async()
            return
        if not goal_handle.accepted:
            self.store.transition(mission_id, MissionState.FAILED, "Nav2 rejected goal", "NAV_REJECTED")
            return
        self._goal_handle = goal_handle
        self._goal_mission_id = mission_id
        result = goal_handle.get_result_async()
        result.add_done_callback(lambda value: self._on_navigation_result(value, mission_id, returning))

    def _on_navigation_result(self, future, mission_id: str, returning: bool) -> None:
        if self._goal_mission_id == mission_id:
            self._goal_handle = None
            self._goal_mission_id = None
        mission = self.store.get(mission_id)
        if mission is None or mission.terminal:
            return
        try:
            status = future.result().status
        except Exception as exc:
            self.store.transition(
                mission_id, MissionState.FAILED, f"Nav2 result failed: {exc}", "NAV_ERROR"
            )
            return
        if status == GoalStatus.STATUS_SUCCEEDED:
            self._navigation_succeeded(mission, returning)
        else:
            self.store.transition(
                mission_id, MissionState.FAILED, f"Nav2 finished with status {status}", "NAV_FAILED"
            )

    def _navigation_succeeded(self, mission: Mission, returning: bool) -> None:
        if returning:
            self.store.transition(mission.mission_id, MissionState.COMPLETED, "returned successfully")
            return
        self.store.transition(mission.mission_id, MissionState.ARRIVED, "arrived at target")
        if mission.type_enum == MissionType.NAVIGATE:
            self.store.transition(mission.mission_id, MissionState.COMPLETED, "navigation completed")
            return
        self.store.transition(
            mission.mission_id, MissionState.WAITING_FOR_ARM, "waiting for manipulator service"
        )
        msg = String()
        msg.data = json.dumps(
            {
                "mission_id": mission.mission_id,
                "action": "PICK_AND_PLACE",
                "target_item": mission.target_item,
                "drop_zone": "wheelbot_payload_area",
            },
            ensure_ascii=False,
        )
        self.arm_request_pub.publish(msg)

    def _on_arm_result(self, msg: String) -> None:
        try:
            payload = json.loads(msg.data)
            mission = self.store.get(str(payload["mission_id"]))
            if mission is None or mission.terminal:
                return
            status = str(payload.get("status", "")).upper()
            if status in {"ACCEPTED", "RUNNING"} and mission.state_enum == MissionState.WAITING_FOR_ARM:
                self.store.transition(mission.mission_id, MissionState.ARM_RUNNING, "manipulator running")
            elif status == "SUCCEEDED" and mission.state_enum in {
                MissionState.WAITING_FOR_ARM,
                MissionState.ARM_RUNNING,
            }:
                if mission.state_enum == MissionState.WAITING_FOR_ARM:
                    self.store.transition(mission.mission_id, MissionState.ARM_RUNNING, "manipulator running")
                self.store.transition(mission.mission_id, MissionState.LOADED, "payload loaded")
                self._start_navigation(mission, mission.return_location, returning=True)
            elif status in {"FAILED", "CANCELLED"}:
                self.store.transition(
                    mission.mission_id,
                    MissionState.FAILED,
                    str(payload.get("detail", "manipulator failed")),
                    "ARM_FAILED",
                )
        except (KeyError, ValueError, json.JSONDecodeError) as exc:
            self.get_logger().warning(f"ignored invalid arm result: {exc}")

    def _on_cancel(self, mission: Mission) -> None:
        if self._goal_handle is not None and self._goal_mission_id == mission.mission_id:
            self._goal_handle.cancel_goal_async()
            self._goal_handle = None
            self._goal_mission_id = None
        if self._fake_timer is not None and self._fake_mission_id == mission.mission_id:
            self._fake_timer.cancel()
            self._fake_timer = None
            self._fake_mission_id = None
        msg = String()
        msg.data = json.dumps({"mission_id": mission.mission_id})
        self.arm_cancel_pub.publish(msg)

    def destroy_node(self):
        self.http.close()
        self.feedback.close()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = MissionManagerNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
