#!/usr/bin/env python3
"""Exercise a complete fetch mission through the public Mission Manager API."""

from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request
import uuid


EXPECTED_STATES = [
    "PENDING",
    "NAVIGATING",
    "ARRIVED",
    "WAITING_FOR_ARM",
    "ARM_RUNNING",
    "LOADED",
    "RETURNING",
    "COMPLETED",
]


def request(base_url: str, token: str, path: str, method: str = "GET", body=None):
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    encoded = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        encoded = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        base_url.rstrip("/") + path,
        data=encoded,
        headers=headers,
        method=method,
    )
    with urllib.request.urlopen(req, timeout=3) as response:
        return response.status, json.load(response)


def is_subsequence(expected: list[str], actual: list[str]) -> bool:
    cursor = iter(actual)
    return all(any(value == item for value in cursor) for item in expected)


def run(base_url: str, token: str, timeout_s: float) -> dict[str, object]:
    request_id = f"smoke-{uuid.uuid4()}"
    _, submitted = request(
        base_url,
        token,
        "/api/v1/missions",
        "POST",
        {
            "request_id": request_id,
            "task_type": "FETCH_ITEM",
            "target_item": "integration-test-item",
            "target_location": "arm_zone",
            "return_location": "home",
        },
    )
    mission_id = str(submitted["mission"]["mission_id"])
    deadline = time.monotonic() + timeout_s
    mission = submitted["mission"]
    while time.monotonic() < deadline:
        _, payload = request(base_url, token, f"/api/v1/missions/{mission_id}")
        mission = payload["mission"]
        if mission["state"] in {"COMPLETED", "FAILED", "CANCELLED"}:
            break
        time.sleep(0.1)
    if mission["state"] != "COMPLETED":
        raise RuntimeError(
            f"mission did not complete: state={mission['state']} "
            f"error={mission.get('error_code', '')} detail={mission.get('detail', '')}"
        )

    _, feed = request(base_url, token, "/api/v1/events?after=0")
    states = [
        str(event["state"])
        for event in feed.get("events", [])
        if event.get("mission_id") == mission_id
    ]
    if not is_subsequence(EXPECTED_STATES, states):
        raise RuntimeError(f"mission event sequence incomplete: {states}")
    return {"mission_id": mission_id, "states": states, "result": mission}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    parser.add_argument("--token", required=True)
    parser.add_argument("--timeout", type=float, default=15.0)
    args = parser.parse_args()
    try:
        result = run(args.base_url, args.token, args.timeout)
    except (KeyError, RuntimeError, urllib.error.URLError, json.JSONDecodeError) as exc:
        print(f"mission smoke test failed: {exc}")
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
