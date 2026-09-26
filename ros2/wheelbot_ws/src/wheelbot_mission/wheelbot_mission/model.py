"""Thread-safe, ROS-independent mission model and persistence."""

from __future__ import annotations

import json
import re
import threading
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Callable


class MissionType(str, Enum):
    NAVIGATE = "NAVIGATE"
    FETCH_ITEM = "FETCH_ITEM"
    RETURN_HOME = "RETURN_HOME"


class MissionState(str, Enum):
    PENDING = "PENDING"
    NAVIGATING = "NAVIGATING"
    ARRIVED = "ARRIVED"
    WAITING_FOR_ARM = "WAITING_FOR_ARM"
    ARM_RUNNING = "ARM_RUNNING"
    LOADED = "LOADED"
    RETURNING = "RETURNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


TERMINAL_STATES = {
    MissionState.COMPLETED,
    MissionState.FAILED,
    MissionState.CANCELLED,
}

ALLOWED_TRANSITIONS = {
    MissionState.PENDING: {
        MissionState.NAVIGATING,
        MissionState.RETURNING,
        MissionState.CANCELLED,
        MissionState.FAILED,
    },
    MissionState.NAVIGATING: {
        MissionState.ARRIVED,
        MissionState.CANCELLED,
        MissionState.FAILED,
    },
    MissionState.ARRIVED: {
        MissionState.WAITING_FOR_ARM,
        MissionState.COMPLETED,
        MissionState.CANCELLED,
        MissionState.FAILED,
    },
    MissionState.WAITING_FOR_ARM: {
        MissionState.ARM_RUNNING,
        MissionState.CANCELLED,
        MissionState.FAILED,
    },
    MissionState.ARM_RUNNING: {
        MissionState.LOADED,
        MissionState.CANCELLED,
        MissionState.FAILED,
    },
    MissionState.LOADED: {
        MissionState.RETURNING,
        MissionState.CANCELLED,
        MissionState.FAILED,
    },
    MissionState.RETURNING: {
        MissionState.COMPLETED,
        MissionState.CANCELLED,
        MissionState.FAILED,
    },
}

_IDENTIFIER = re.compile(r"^[A-Za-z0-9._:-]{1,80}$")


class MissionValidationError(ValueError):
    pass


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _require_text(value: object, field: str, max_length: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise MissionValidationError(f"{field} must be a non-empty string")
    value = value.strip()
    if len(value) > max_length:
        raise MissionValidationError(f"{field} exceeds {max_length} characters")
    return value


@dataclass
class Mission:
    mission_id: str
    request_id: str
    task_type: str
    target_location: str
    return_location: str
    target_item: str
    state: str
    detail: str
    error_code: str
    created_at: str
    updated_at: str

    @property
    def state_enum(self) -> MissionState:
        return MissionState(self.state)

    @property
    def type_enum(self) -> MissionType:
        return MissionType(self.task_type)

    @property
    def terminal(self) -> bool:
        return self.state_enum in TERMINAL_STATES

    def to_dict(self) -> dict[str, str]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "Mission":
        return cls(**{field: str(data.get(field, "")) for field in cls.__dataclass_fields__})


class MissionStore:
    """Owns mission IDs, idempotency, legal transitions, and durable snapshots."""

    def __init__(
        self,
        state_file: str | Path | None = None,
        on_change: Callable[[Mission], None] | None = None,
    ) -> None:
        self._lock = threading.RLock()
        self._missions: dict[str, Mission] = {}
        self._request_ids: dict[str, str] = {}
        self._state_file = Path(state_file) if state_file else None
        self._on_change = on_change
        self._load()

    def submit(self, payload: dict[str, object]) -> tuple[Mission, bool]:
        normalized = self._normalize(payload)
        with self._lock:
            return self._submit_normalized(normalized)

    def replace_active_with_return(
        self,
        payload: dict[str, object],
        detail: str = "replaced by return-home request",
        on_cancel: Callable[[Mission], None] | None = None,
    ) -> tuple[Mission, bool, Mission | None]:
        """Atomically validate a return-home request, cancel the active mission, and submit it.

        A replay of an existing request never cancels a newer mission. This is important for
        retries from an intermittently connected voice device.
        """
        normalized = self._normalize(payload)
        if normalized["task_type"] != MissionType.RETURN_HOME.value:
            raise MissionValidationError("replacement mission must be RETURN_HOME")

        with self._lock:
            existing_id = self._request_ids.get(normalized["request_id"])
            if existing_id:
                existing = self._missions[existing_id]
                self._require_matching_replay(existing, normalized)
                return self._copy(existing), False, None

            active = self._active_unlocked()
            cancelled = None
            if active is not None:
                active.state = MissionState.CANCELLED.value
                active.detail = detail[:240]
                active.error_code = ""
                active.updated_at = _utc_now()
                cancelled = self._copy(active)
            mission = self._new_mission(normalized)
            self._missions[mission.mission_id] = mission
            self._request_ids[mission.request_id] = mission.mission_id
            self._persist()
            if cancelled is not None and on_cancel:
                on_cancel(self._copy(cancelled))
            if self._on_change:
                if cancelled is not None:
                    self._on_change(self._copy(cancelled))
                self._on_change(self._copy(mission))
            return self._copy(mission), True, cancelled

    def _normalize(self, payload: dict[str, object]) -> dict[str, str]:
        task_raw = _require_text(payload.get("task_type"), "task_type", 32).upper()
        try:
            task_type = MissionType(task_raw)
        except ValueError as exc:
            supported = ", ".join(item.value for item in MissionType)
            raise MissionValidationError(f"unsupported task_type; expected one of {supported}") from exc

        request_id = _require_text(
            payload.get("request_id") or str(uuid.uuid4()), "request_id", 80
        )
        if not _IDENTIFIER.fullmatch(request_id):
            raise MissionValidationError("request_id contains unsupported characters")

        target_location = str(payload.get("target_location") or "").strip()
        return_location = str(payload.get("return_location") or "home").strip()
        target_item = str(payload.get("target_item") or "").strip()

        if task_type in {MissionType.NAVIGATE, MissionType.FETCH_ITEM}:
            target_location = _require_text(target_location, "target_location", 80)
        if task_type == MissionType.RETURN_HOME:
            target_location = return_location
        return_location = _require_text(return_location, "return_location", 80)
        if task_type == MissionType.FETCH_ITEM:
            target_item = _require_text(target_item, "target_item", 120)
        elif len(target_item) > 120:
            raise MissionValidationError("target_item exceeds 120 characters")

        return {
            "request_id": request_id,
            "task_type": task_type.value,
            "target_location": target_location,
            "return_location": return_location,
            "target_item": target_item,
        }

    def _submit_normalized(self, normalized: dict[str, str]) -> tuple[Mission, bool]:
        existing_id = self._request_ids.get(normalized["request_id"])
        if existing_id:
            existing = self._missions[existing_id]
            self._require_matching_replay(existing, normalized)
            return self._copy(existing), False
        if self._active_unlocked() is not None:
            raise MissionValidationError("another mission is already active")

        mission = self._new_mission(normalized)
        self._missions[mission.mission_id] = mission
        self._request_ids[mission.request_id] = mission.mission_id
        self._commit(mission)
        return self._copy(mission), True

    @staticmethod
    def _new_mission(normalized: dict[str, str]) -> Mission:
        now = _utc_now()
        return Mission(
            mission_id=str(uuid.uuid4()),
            request_id=normalized["request_id"],
            task_type=normalized["task_type"],
            target_location=normalized["target_location"],
            return_location=normalized["return_location"],
            target_item=normalized["target_item"],
            state=MissionState.PENDING.value,
            detail="accepted",
            error_code="",
            created_at=now,
            updated_at=now,
        )

    @staticmethod
    def _require_matching_replay(mission: Mission, normalized: dict[str, str]) -> None:
        comparable = (
            "task_type",
            "target_location",
            "return_location",
            "target_item",
        )
        if any(getattr(mission, field) != normalized[field] for field in comparable):
            raise MissionValidationError("request_id was already used with a different payload")

    def transition(
        self,
        mission_id: str,
        new_state: MissionState | str,
        detail: str = "",
        error_code: str = "",
    ) -> Mission:
        new_state = MissionState(new_state)
        with self._lock:
            mission = self._missions.get(mission_id)
            if mission is None:
                raise KeyError(mission_id)
            old_state = mission.state_enum
            if old_state == new_state:
                return self._copy(mission)
            if old_state in TERMINAL_STATES or new_state not in ALLOWED_TRANSITIONS.get(old_state, set()):
                raise MissionValidationError(
                    f"illegal mission transition {old_state.value} -> {new_state.value}"
                )
            mission.state = new_state.value
            mission.detail = detail[:240]
            mission.error_code = error_code[:80]
            mission.updated_at = _utc_now()
            self._commit(mission)
            return self._copy(mission)

    def cancel(self, mission_id: str, detail: str = "cancelled by user") -> Mission:
        with self._lock:
            mission = self._missions.get(mission_id)
            if mission is None:
                raise KeyError(mission_id)
            if mission.terminal:
                return self._copy(mission)
        return self.transition(mission_id, MissionState.CANCELLED, detail)

    def get(self, mission_id: str) -> Mission | None:
        with self._lock:
            mission = self._missions.get(mission_id)
            return self._copy(mission) if mission else None

    def active(self) -> Mission | None:
        with self._lock:
            active = self._active_unlocked()
            return self._copy(active) if active else None

    def _active_unlocked(self) -> Mission | None:
        active = [mission for mission in self._missions.values() if not mission.terminal]
        return max(active, key=lambda item: item.created_at) if active else None

    def all(self) -> list[Mission]:
        with self._lock:
            return [
                self._copy(item)
                for item in sorted(self._missions.values(), key=lambda value: value.created_at)
            ]

    def latest(self) -> Mission | None:
        with self._lock:
            if not self._missions:
                return None
            return self._copy(max(self._missions.values(), key=lambda item: item.created_at))

    def _copy(self, mission: Mission) -> Mission:
        return Mission.from_dict(mission.to_dict())

    def _load(self) -> None:
        if self._state_file is None or not self._state_file.exists():
            return
        data = json.loads(self._state_file.read_text(encoding="utf-8"))
        for raw in data.get("missions", []):
            mission = Mission.from_dict(raw)
            MissionType(mission.task_type)
            MissionState(mission.state)
            if not mission.terminal:
                mission.state = MissionState.FAILED.value
                mission.detail = "mission manager restarted before completion"
                mission.error_code = "MANAGER_RESTARTED"
                mission.updated_at = _utc_now()
            self._missions[mission.mission_id] = mission
            self._request_ids[mission.request_id] = mission.mission_id
        if self._missions:
            self._persist()

    def _commit(self, mission: Mission) -> None:
        self._persist()
        if self._on_change:
            self._on_change(self._copy(mission))

    def _persist(self) -> None:
        if self._state_file is None:
            return
        self._state_file.parent.mkdir(parents=True, exist_ok=True)
        temp = self._state_file.with_suffix(self._state_file.suffix + ".tmp")
        payload = {"version": 1, "missions": [item.to_dict() for item in self._missions.values()]}
        temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        temp.replace(self._state_file)
