import threading
import time
import unittest

from wheelbot_mission.events import MissionEventBroker
from wheelbot_mission.model import MissionStore


class MissionEventBrokerTest(unittest.TestCase):
    def test_orders_and_filters_events(self):
        events = MissionEventBroker()
        store = MissionStore(on_change=events.publish)
        mission, _ = store.submit({
            "request_id": "event-1",
            "task_type": "NAVIGATE",
            "target_location": "workbench",
        })
        store.cancel(mission.mission_id)

        received = events.after(0)

        self.assertEqual([1, 2], [item["event_id"] for item in received])
        self.assertEqual(["PENDING", "CANCELLED"], [item["state"] for item in received])
        self.assertEqual([2], [item["event_id"] for item in events.after(1)])

    def test_long_poll_wakes_on_publish(self):
        events = MissionEventBroker()
        store = MissionStore(on_change=events.publish)

        def submit_later():
            time.sleep(0.05)
            store.submit({
                "request_id": "event-wait",
                "task_type": "RETURN_HOME",
            })

        worker = threading.Thread(target=submit_later)
        worker.start()
        received = events.wait_after(0, timeout_s=1)
        worker.join()

        self.assertEqual("PENDING", received[0]["state"])


if __name__ == "__main__":
    unittest.main()
