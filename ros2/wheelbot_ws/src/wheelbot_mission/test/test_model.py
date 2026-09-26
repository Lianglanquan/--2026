import tempfile
import unittest
from pathlib import Path

from wheelbot_mission.model import MissionState, MissionStore, MissionValidationError


class MissionStoreTest(unittest.TestCase):
    def test_fetch_lifecycle_and_idempotency(self):
        with tempfile.TemporaryDirectory() as directory:
            store = MissionStore(Path(directory) / "missions.json")
            payload = {
                "request_id": "voice-001",
                "task_type": "FETCH_ITEM",
                "target_item": "矿泉水",
                "target_location": "arm_zone",
                "return_location": "home",
            }
            mission, created = store.submit(payload)
            self.assertTrue(created)
            duplicate, created = store.submit(payload)
            self.assertFalse(created)
            self.assertEqual(mission.mission_id, duplicate.mission_id)
            for state in (
                MissionState.NAVIGATING,
                MissionState.ARRIVED,
                MissionState.WAITING_FOR_ARM,
                MissionState.ARM_RUNNING,
                MissionState.LOADED,
                MissionState.RETURNING,
                MissionState.COMPLETED,
            ):
                mission = store.transition(mission.mission_id, state)
            self.assertTrue(mission.terminal)

    def test_rejects_concurrent_and_illegal_transitions(self):
        store = MissionStore()
        mission, _ = store.submit({
            "request_id": "one",
            "task_type": "NAVIGATE",
            "target_location": "workbench",
        })
        with self.assertRaises(MissionValidationError):
            store.submit({
                "request_id": "two",
                "task_type": "RETURN_HOME",
            })
        with self.assertRaises(MissionValidationError):
            store.transition(mission.mission_id, MissionState.COMPLETED)

    def test_restart_fails_interrupted_mission(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "missions.json"
            store = MissionStore(path)
            mission, _ = store.submit({
                "request_id": "restart-test",
                "task_type": "RETURN_HOME",
            })
            store.transition(mission.mission_id, MissionState.RETURNING)
            restored = MissionStore(path).get(mission.mission_id)
            self.assertEqual(MissionState.FAILED, restored.state_enum)
            self.assertEqual("MANAGER_RESTARTED", restored.error_code)

    def test_idempotency_key_rejects_a_different_payload(self):
        store = MissionStore()
        store.submit({
            "request_id": "same-key",
            "task_type": "NAVIGATE",
            "target_location": "workbench",
        })
        with self.assertRaisesRegex(MissionValidationError, "different payload"):
            store.submit({
                "request_id": "same-key",
                "task_type": "NAVIGATE",
                "target_location": "arm_zone",
            })

    def test_return_replay_does_not_cancel_a_newer_active_mission(self):
        store = MissionStore()
        payload = {"request_id": "return-once", "task_type": "RETURN_HOME"}
        returned, _, cancelled = store.replace_active_with_return(payload)
        self.assertIsNone(cancelled)
        store.transition(returned.mission_id, MissionState.RETURNING)
        store.transition(returned.mission_id, MissionState.COMPLETED)
        active, _ = store.submit({
            "request_id": "new-navigation",
            "task_type": "NAVIGATE",
            "target_location": "workbench",
        })

        replay, created, cancelled = store.replace_active_with_return(payload)

        self.assertFalse(created)
        self.assertIsNone(cancelled)
        self.assertEqual(returned.mission_id, replay.mission_id)
        self.assertEqual(MissionState.PENDING, store.get(active.mission_id).state_enum)

    def test_return_cancels_downstream_before_announcing_replacement(self):
        observed = []
        store = MissionStore(on_change=lambda mission: observed.append(mission.state))
        store.submit({
            "request_id": "moving",
            "task_type": "NAVIGATE",
            "target_location": "workbench",
        })
        observed.clear()

        store.replace_active_with_return(
            {"request_id": "safe-return", "task_type": "RETURN_HOME"},
            on_cancel=lambda mission: observed.append(f"STOP:{mission.state}"),
        )

        self.assertEqual(["STOP:CANCELLED", "CANCELLED", "PENDING"], observed)


if __name__ == "__main__":
    unittest.main()
