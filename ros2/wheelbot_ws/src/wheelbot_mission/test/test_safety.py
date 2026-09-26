import unittest

from wheelbot_mission.model import MissionState
from wheelbot_mission.safety import evaluate_mission_safety


class MissionSafetyTest(unittest.TestCase):
    def evaluate(self, state=MissionState.NAVIGATING, **overrides):
        values = {
            "require_robot_state": True,
            "robot": {"cboard_link": "up", "faults": 0},
            "robot_age_s": 0.1,
            "robot_timeout_s": 2.0,
            "fail_on_robot_fault": True,
            "phase_timed_out": False,
        }
        values.update(overrides)
        return evaluate_mission_safety(state, **values)

    def test_rejects_stale_and_disconnected_robot(self):
        self.assertEqual("ROBOT_STATE_STALE", self.evaluate(robot_age_s=2.1).error_code)
        self.assertEqual(
            "CBOARD_OFFLINE",
            self.evaluate(robot={"cboard_link": "down", "faults": 0}).error_code,
        )

    def test_rejects_fault_mask(self):
        failure = self.evaluate(robot={"cboard_link": "up", "faults": 128})
        self.assertEqual("ROBOT_FAULT", failure.error_code)
        self.assertIn("0x80", failure.detail)

    def test_phase_specific_timeouts(self):
        self.assertEqual("NAV_TIMEOUT", self.evaluate(phase_timed_out=True).error_code)
        self.assertEqual(
            "ARM_TIMEOUT",
            self.evaluate(MissionState.ARM_RUNNING, phase_timed_out=True).error_code,
        )

    def test_fake_mode_can_disable_robot_state_gate(self):
        self.assertIsNone(
            self.evaluate(require_robot_state=False, robot=None, robot_age_s=float("inf"))
        )


if __name__ == "__main__":
    unittest.main()
