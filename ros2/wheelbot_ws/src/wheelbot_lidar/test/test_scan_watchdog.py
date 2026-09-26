from wheelbot_lidar.scan_watchdog_policy import ScanHealthMonitor


def test_single_short_scan_gap_does_not_request_restart():
    monitor = ScanHealthMonitor(
        started_at=0.0,
        timeout_s=1.5,
        startup_grace_s=10.0,
        restart_cooldown_s=15.0,
    )
    monitor.record_scan(10.0)

    assert monitor.restart_due(11.4) is False


def test_sustained_scan_gap_requests_restart_after_startup_grace():
    monitor = ScanHealthMonitor(
        started_at=0.0,
        timeout_s=1.5,
        startup_grace_s=10.0,
        restart_cooldown_s=15.0,
    )

    assert monitor.restart_due(9.9) is False
    assert monitor.restart_due(10.0) is True


def test_restart_cooldown_prevents_repeated_restart_requests():
    monitor = ScanHealthMonitor(
        started_at=0.0,
        timeout_s=1.5,
        startup_grace_s=0.0,
        restart_cooldown_s=15.0,
    )
    monitor.record_scan(0.0)

    assert monitor.restart_due(1.5) is True
    monitor.mark_restart(1.5)
    assert monitor.restart_due(10.0) is False
    assert monitor.restart_due(17.0) is True
