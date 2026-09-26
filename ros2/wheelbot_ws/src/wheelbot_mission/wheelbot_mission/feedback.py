"""Non-blocking mission feedback webhook for a XiaoZhi server-side adapter."""

from __future__ import annotations

import json
import queue
import threading
import time
import urllib.request
from collections.abc import Callable

from .model import Mission, MissionState


def feedback_payload(mission: Mission) -> dict[str, object]:
    target = mission.target_location or "目标区域"
    messages = {
        MissionState.PENDING: "好的，我现在开始执行任务。",
        MissionState.NAVIGATING: f"正在前往{target}。",
        MissionState.ARRIVED: f"已经到达{target}。",
        MissionState.WAITING_FOR_ARM: "已经到达工作区，正在等待机械臂。",
        MissionState.ARM_RUNNING: "机械臂正在抓取和装载。",
        MissionState.LOADED: "东西已经拿到了，我正在回来。",
        MissionState.RETURNING: "正在返回。",
        MissionState.COMPLETED: "任务完成。",
        MissionState.FAILED: f"任务失败：{mission.detail or '未知原因'}。",
        MissionState.CANCELLED: "任务已经取消。",
    }
    return {
        "event": "wheelbot.mission_state_changed",
        "mission_id": mission.mission_id,
        "request_id": mission.request_id,
        "state": mission.state,
        "speak_text": messages[mission.state_enum],
        "detail": mission.detail,
        "error_code": mission.error_code,
        "mission": mission.to_dict(),
    }


class FeedbackWebhook:
    """Delivers feedback out of the ROS executor with bounded retry."""

    def __init__(
        self,
        url: str,
        token: str = "",
        timeout_s: float = 3.0,
        retries: int = 3,
        log: Callable[[str], None] | None = None,
    ) -> None:
        self._url = url.strip()
        self._token = token
        self._timeout_s = max(0.1, timeout_s)
        self._retries = max(1, retries)
        self._log = log or (lambda message: None)
        self._queue: queue.Queue[dict[str, object] | None] = queue.Queue(maxsize=128)
        self._thread = None
        if self._url:
            self._thread = threading.Thread(
                target=self._run, name="mission-feedback", daemon=True
            )
            self._thread.start()

    @property
    def enabled(self) -> bool:
        return bool(self._url)

    def publish(self, mission: Mission) -> None:
        if not self.enabled:
            return
        payload = feedback_payload(mission)
        try:
            self._queue.put_nowait(payload)
        except queue.Full:
            self._log("mission feedback queue is full; dropping newest event")

    def close(self) -> None:
        if self._thread is None:
            return
        try:
            self._queue.put_nowait(None)
        except queue.Full:
            self._log("mission feedback queue did not stop cleanly")
        self._thread.join(timeout=self._timeout_s + 1.0)

    def _run(self) -> None:
        while True:
            payload = self._queue.get()
            if payload is None:
                return
            self._deliver(payload)

    def _deliver(self, payload: dict[str, object]) -> None:
        encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        for attempt in range(self._retries):
            try:
                request = urllib.request.Request(
                    self._url, data=encoded, headers=headers, method="POST"
                )
                with urllib.request.urlopen(request, timeout=self._timeout_s) as response:
                    if 200 <= response.status < 300:
                        return
                    raise OSError(f"HTTP {response.status}")
            except Exception as exc:
                if attempt + 1 == self._retries:
                    self._log(f"mission feedback delivery failed: {exc}")
                    return
                time.sleep(0.25 * (2**attempt))
