"""Pure safety decisions shared by the ROS node and host-side tests."""

from __future__ import annotations

from dataclasses import dataclass

from .model import MissionState, TERMINAL_STATES


@dataclass(frozen=True)
class SafetyFailure:
    detail: str
    error_code: str


def evaluate_mission_safety(
    state: MissionState,
    *,
    require_robot_state: bool,
    robot: dict[str, object] | None,
    robot_age_s: float,
    robot_timeout_s: float,
    fail_on_robot_fault: bool,
    phase_timed_out: bool,
) -> SafetyFailure | None:
    if state in TERMINAL_STATES:
        return None
    if require_robot_state:
        if robot is None or robot_age_s > robot_timeout_s:
            return SafetyFailure("robot state is unavailable or stale", "ROBOT_STATE_STALE")
        if str(robot.get("cboard_link", "")).lower() != "up":
            return SafetyFailure("C Board communication link is down", "CBOARD_OFFLINE")
        faults = int(robot.get("faults", 0))
        if fail_on_robot_fault and faults:
            return SafetyFailure(
                f"robot controller reported fault mask {faults:#x}", "ROBOT_FAULT"
            )
    if phase_timed_out:
        if state in {MissionState.NAVIGATING, MissionState.RETURNING}:
            return SafetyFailure("navigation timed out", "NAV_TIMEOUT")
        if state in {MissionState.WAITING_FOR_ARM, MissionState.ARM_RUNNING}:
            return SafetyFailure("manipulator task timed out", "ARM_TIMEOUT")
    return None
