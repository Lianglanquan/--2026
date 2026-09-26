"""In-memory mission event journal for Web and voice feedback adapters."""

from __future__ import annotations

import threading
import time
from collections import deque
from datetime import datetime, timezone

from .model import Mission


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class MissionEventBroker:
    """Keeps a bounded, monotonic event stream and supports long polling."""

    def __init__(self, capacity: int = 256) -> None:
        self._condition = threading.Condition()
        self._events: deque[dict[str, object]] = deque(maxlen=max(16, capacity))
        self._next_id = 1

    def publish(self, mission: Mission) -> dict[str, object]:
        with self._condition:
            event = {
                "event_id": self._next_id,
                "event_type": "MISSION_STATE_CHANGED",
                "timestamp": _utc_now(),
                "mission_id": mission.mission_id,
                "state": mission.state,
                "detail": mission.detail,
                "error_code": mission.error_code,
                "mission": mission.to_dict(),
            }
            self._next_id += 1
            self._events.append(event)
            self._condition.notify_all()
            return dict(event)

    def after(self, event_id: int, limit: int = 100) -> list[dict[str, object]]:
        with self._condition:
            return self._after_unlocked(event_id, limit)

    def wait_after(
        self,
        event_id: int,
        timeout_s: float = 0.0,
        limit: int = 100,
    ) -> list[dict[str, object]]:
        deadline = time.monotonic() + max(0.0, timeout_s)
        with self._condition:
            while True:
                events = self._after_unlocked(event_id, limit)
                if events:
                    return events
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return []
                self._condition.wait(remaining)

    def latest_id(self) -> int:
        with self._condition:
            return self._next_id - 1

    def _after_unlocked(self, event_id: int, limit: int) -> list[dict[str, object]]:
        bounded_limit = min(256, max(1, limit))
        return [dict(item) for item in self._events if int(item["event_id"]) > event_id][
            :bounded_limit
        ]
