import json
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from wheelbot_mission.events import MissionEventBroker
from wheelbot_mission.http_api import MissionHttpServer
from wheelbot_mission.model import MissionStore


class MissionHttpApiTest(unittest.TestCase):
    def setUp(self):
        self.events = MissionEventBroker()
        self.store = MissionStore(on_change=self.events.publish)
        self.server = MissionHttpServer(
            "127.0.0.1", 0, "test-token", self.store,
            get_system_status=lambda: {"robot_state_fresh": True},
            events=self.events,
            dashboard_file=Path(__file__).parents[1] / "web" / "index.html",
        )
        self.server.start()
        self.base = f"http://127.0.0.1:{self.server.address[1]}"

    def tearDown(self):
        self.server.close()

    def request(self, path, method="GET", body=None, token="test-token"):
        headers = {"Authorization": f"Bearer {token}"}
        data = None
        if body is not None:
            data = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(self.base + path, data=data, headers=headers, method=method)
        with urllib.request.urlopen(request, timeout=2) as response:
            return response.status, json.load(response)

    def test_submit_query_and_cancel(self):
        status, payload = self.request("/api/v1/missions", "POST", {
            "request_id": "http-1",
            "task_type": "NAVIGATE",
            "target_location": "workbench",
        })
        self.assertEqual(202, status)
        mission_id = payload["mission"]["mission_id"]
        _, current = self.request("/api/v1/missions/current")
        self.assertEqual(mission_id, current["mission"]["mission_id"])
        _, cancelled = self.request(f"/api/v1/missions/{mission_id}/cancel", "POST")
        self.assertEqual("CANCELLED", cancelled["mission"]["state"])

    def test_requires_bearer_token(self):
        with self.assertRaises(urllib.error.HTTPError) as error:
            self.request("/api/v1/missions", token="wrong")
        self.assertEqual(401, error.exception.code)

    def test_system_status(self):
        status, payload = self.request("/api/v1/system/status")
        self.assertEqual(200, status)
        self.assertTrue(payload["robot_state_fresh"])

    def test_dashboard_and_event_feed(self):
        with urllib.request.urlopen(self.base + "/dashboard", timeout=2) as response:
            self.assertIn(b"WheelBot Mission Console", response.read())
        self.request("/api/v1/missions", "POST", {
            "request_id": "event-http",
            "task_type": "RETURN_HOME",
        })
        _, feed = self.request("/api/v1/events?after=0&wait_ms=10")
        self.assertEqual("PENDING", feed["events"][0]["state"])
        self.assertEqual(feed["events"][-1]["event_id"], feed["latest_event_id"])

    def test_return_home_replaces_active_mission(self):
        _, first = self.request("/api/v1/missions", "POST", {
            "request_id": "active-1",
            "task_type": "NAVIGATE",
            "target_location": "workbench",
        })
        _, replacement = self.request("/api/v1/missions", "POST", {
            "request_id": "return-1",
            "task_type": "RETURN_HOME",
            "return_location": "home",
        })
        old = self.store.get(first["mission"]["mission_id"])
        self.assertEqual("CANCELLED", old.state)
        self.assertEqual("PENDING", replacement["mission"]["state"])

    def test_invalid_return_request_does_not_cancel_active_mission(self):
        _, first = self.request("/api/v1/missions", "POST", {
            "request_id": "keep-active",
            "task_type": "NAVIGATE",
            "target_location": "workbench",
        })
        with self.assertRaises(urllib.error.HTTPError) as error:
            self.request("/api/v1/missions", "POST", {
                "request_id": "contains spaces",
                "task_type": "RETURN_HOME",
            })
        self.assertEqual(400, error.exception.code)
        self.assertEqual("PENDING", self.store.get(first["mission"]["mission_id"]).state)


if __name__ == "__main__":
    unittest.main()
