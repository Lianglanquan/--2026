import json
import unittest
import urllib.error
import urllib.request

from wheelbot_mission.http_api import MissionHttpServer
from wheelbot_mission.model import MissionStore


class MissionHttpApiTest(unittest.TestCase):
    def setUp(self):
        self.store = MissionStore()
        self.server = MissionHttpServer(
            "127.0.0.1", 0, "test-token", self.store,
            get_system_status=lambda: {"robot_state_fresh": True},
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


if __name__ == "__main__":
    unittest.main()
