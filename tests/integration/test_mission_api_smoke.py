import threading
import time

from tools.mission_api_smoke import EXPECTED_STATES, run
from wheelbot_mission.events import MissionEventBroker
from wheelbot_mission.http_api import MissionHttpServer
from wheelbot_mission.model import MissionState, MissionStore


def test_smoke_client_verifies_complete_fetch_sequence():
    events = MissionEventBroker()
    store_holder = {}
    workers = []

    def on_change(mission):
        events.publish(mission)
        if mission.state == MissionState.PENDING.value:
            def complete():
                for state in EXPECTED_STATES[1:]:
                    time.sleep(0.01)
                    store_holder["store"].transition(mission.mission_id, state)

            worker = threading.Thread(target=complete)
            workers.append(worker)
            worker.start()

    store = MissionStore(on_change=on_change)
    store_holder["store"] = store
    server = MissionHttpServer(
        "127.0.0.1",
        0,
        "smoke-token",
        store,
        events=events,
    )
    server.start()
    try:
        result = run(
            f"http://127.0.0.1:{server.address[1]}",
            "smoke-token",
            timeout_s=2,
        )
        assert result["result"]["state"] == "COMPLETED"
        assert result["states"] == EXPECTED_STATES
    finally:
        for worker in workers:
            worker.join(timeout=1)
        server.close()
