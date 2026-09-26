import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from wheelbot_mission.feedback import FeedbackWebhook, feedback_payload
from wheelbot_mission.model import MissionState, MissionStore


class FeedbackWebhookTest(unittest.TestCase):
    def test_maps_completed_mission_to_spoken_feedback(self):
        store = MissionStore()
        mission, _ = store.submit({"request_id": "feedback-text", "task_type": "RETURN_HOME"})
        store.transition(mission.mission_id, MissionState.RETURNING)
        mission = store.transition(mission.mission_id, MissionState.COMPLETED)

        payload = feedback_payload(mission)

        self.assertEqual("任务完成。", payload["speak_text"])
        self.assertEqual("COMPLETED", payload["state"])

    def test_posts_feedback_with_bearer_token(self):
        received = []
        done = threading.Event()

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, fmt, *args):
                return

            def do_POST(self):
                length = int(self.headers["Content-Length"])
                received.append((self.headers.get("Authorization"), json.loads(self.rfile.read(length))))
                self.send_response(204)
                self.end_headers()
                done.set()

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        feedback = FeedbackWebhook(
            f"http://127.0.0.1:{server.server_address[1]}/events",
            "secret-token",
            timeout_s=1,
        )
        store = MissionStore(on_change=feedback.publish)

        store.submit({"request_id": "feedback-http", "task_type": "RETURN_HOME"})

        self.assertTrue(done.wait(2))
        feedback.close()
        server.shutdown()
        server.server_close()
        thread.join(timeout=1)
        self.assertEqual("Bearer secret-token", received[0][0])
        self.assertEqual("PENDING", received[0][1]["state"])


if __name__ == "__main__":
    unittest.main()
