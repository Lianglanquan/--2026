"""Small dependency-free REST API used by XiaoZhi and future web clients."""

from __future__ import annotations

import hmac
import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import parse_qs, urlparse

from .events import MissionEventBroker
from .model import MissionStore, MissionValidationError


class _MissionThreadingHttpServer(ThreadingHTTPServer):
    daemon_threads = True


class MissionHttpServer:
    def __init__(
        self,
        host: str,
        port: int,
        token: str,
        store: MissionStore,
        on_cancel=None,
        get_system_status=None,
        events: MissionEventBroker | None = None,
        dashboard_file: str | Path | None = None,
    ) -> None:
        self.store = store
        self.token = token
        self.on_cancel = on_cancel
        self.get_system_status = get_system_status
        self.events = events
        self.dashboard_file = Path(dashboard_file) if dashboard_file else None
        api = self

        class Handler(BaseHTTPRequestHandler):
            server_version = "WheelBotMission/1.0"
            _mission_path = re.compile(r"^/api/v1/missions/([^/]+)$")
            _cancel_path = re.compile(r"^/api/v1/missions/([^/]+)/cancel$")

            def log_message(self, fmt, *args):
                return

            def _authorized(self) -> bool:
                if not api.token:
                    return True
                expected = f"Bearer {api.token}"
                supplied = self.headers.get("Authorization", "")
                return hmac.compare_digest(supplied, expected)

            def _send(self, status: int, payload: object) -> None:
                encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(encoded)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(encoded)

            def _send_html(self, status: int, html: bytes) -> None:
                self.send_response(status)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(html)))
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'unsafe-inline'; script-src 'unsafe-inline'")
                self.end_headers()
                self.wfile.write(html)

            def _require_auth(self) -> bool:
                if self._authorized():
                    return True
                self._send(401, {"error": "unauthorized"})
                return False

            def _read_json(self) -> dict[str, object]:
                length = int(self.headers.get("Content-Length", "0"))
                if length < 1 or length > 4096:
                    raise MissionValidationError("request body must be 1..4096 bytes")
                body = json.loads(self.rfile.read(length).decode("utf-8"))
                if not isinstance(body, dict):
                    raise MissionValidationError("request body must be a JSON object")
                return body

            def do_GET(self):
                parsed = urlparse(self.path)
                path = parsed.path
                if path in {"/", "/dashboard"}:
                    if api.dashboard_file and api.dashboard_file.is_file():
                        self._send_html(200, api.dashboard_file.read_bytes())
                    else:
                        self._send(404, {"error": "dashboard not installed"})
                    return
                if path == "/healthz":
                    active = api.store.active()
                    self._send(200, {"ok": True, "active_mission_id": active.mission_id if active else None})
                    return
                if not self._require_auth():
                    return
                if path == "/api/v1/missions/current":
                    mission = api.store.active()
                    self._send(200, {"mission": mission.to_dict() if mission else None})
                    return
                if path == "/api/v1/missions":
                    self._send(200, {"missions": [item.to_dict() for item in api.store.all()]})
                    return
                if path == "/api/v1/system/status":
                    payload = api.get_system_status() if api.get_system_status else {}
                    self._send(200, payload)
                    return
                if path == "/api/v1/events":
                    try:
                        query = parse_qs(parsed.query)
                        after = int(query.get("after", ["0"])[0])
                        wait_ms = min(25000, max(0, int(query.get("wait_ms", ["0"])[0])))
                        if after < 0:
                            raise ValueError("after must be non-negative")
                        events = api.events.wait_after(after, wait_ms / 1000.0) if api.events else []
                        latest = api.events.latest_id() if api.events else 0
                        self._send(200, {"events": events, "latest_event_id": latest})
                    except ValueError as exc:
                        self._send(400, {"error": str(exc)})
                    return
                match = self._mission_path.fullmatch(path)
                if match:
                    mission = api.store.get(match.group(1))
                    if mission is None:
                        self._send(404, {"error": "mission not found"})
                    else:
                        self._send(200, {"mission": mission.to_dict()})
                    return
                self._send(404, {"error": "not found"})

            def do_POST(self):
                path = urlparse(self.path).path
                if not self._require_auth():
                    return
                try:
                    if path == "/api/v1/missions":
                        request_body = self._read_json()
                        if str(request_body.get("task_type", "")).upper() == "RETURN_HOME":
                            mission, created, _ = api.store.replace_active_with_return(
                                request_body, on_cancel=api.on_cancel
                            )
                        else:
                            mission, created = api.store.submit(request_body)
                        self._send(202 if created else 200, {"mission": mission.to_dict(), "created": created})
                        return
                    match = self._cancel_path.fullmatch(path)
                    if match:
                        mission = api.store.cancel(match.group(1))
                        if api.on_cancel:
                            api.on_cancel(mission)
                        self._send(200, {"mission": mission.to_dict()})
                        return
                    self._send(404, {"error": "not found"})
                except KeyError:
                    self._send(404, {"error": "mission not found"})
                except (MissionValidationError, ValueError, json.JSONDecodeError) as exc:
                    self._send(409 if "already active" in str(exc) else 400, {"error": str(exc)})

        self._server = _MissionThreadingHttpServer((host, port), Handler)
        self._thread = Thread(target=self._server.serve_forever, name="mission-http", daemon=True)

    @property
    def address(self) -> tuple[str, int]:
        return self._server.server_address

    def start(self) -> None:
        self._thread.start()

    def close(self) -> None:
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=3)
