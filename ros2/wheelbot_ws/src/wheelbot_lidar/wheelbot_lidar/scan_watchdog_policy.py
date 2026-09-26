"""Pure scan-stream health policy used by the ROS watchdog node."""


class ScanHealthMonitor:
    """Deterministic policy for deciding when a scan stream is stalled."""

    def __init__(self, started_at, timeout_s, startup_grace_s, restart_cooldown_s):
        if timeout_s <= 0.0 or startup_grace_s < 0.0 or restart_cooldown_s < 0.0:
            raise ValueError("watchdog timing values are invalid")
        self.started_at = float(started_at)
        self.timeout_s = float(timeout_s)
        self.startup_grace_s = float(startup_grace_s)
        self.restart_cooldown_s = float(restart_cooldown_s)
        self.last_scan_at = None
        self.last_restart_at = None

    def record_scan(self, now):
        self.last_scan_at = float(now)

    def mark_restart(self, now):
        self.last_restart_at = float(now)

    def restart_due(self, now):
        now = float(now)
        if now - self.started_at < self.startup_grace_s:
            return False
        if self.last_restart_at is not None and now - self.last_restart_at < self.restart_cooldown_s:
            return False
        reference = self.started_at if self.last_scan_at is None else self.last_scan_at
        return now - reference >= self.timeout_s
