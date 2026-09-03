from __future__ import annotations

from datetime import datetime, timezone

from prime_foreman_preflight import classify_stall


def test_agent_status_heartbeat_is_not_useful():
    now = datetime(2026, 8, 23, 12, 5, tzinfo=timezone.utc)
    events = [
        {"type": "token", "timestamp": "2026-08-23T12:00:00+00:00"},
        {"type": "agent_status", "status": "working", "timestamp": "2026-08-23T12:04:50+00:00"},
    ]
    report = classify_stall(events, now=now, stall_seconds=120)
    assert report["verdict"] == "STALL_SUSPECT"
    assert report["action"] == "alarm_only"
    assert report["heartbeat_counts_as_useful"] is False
    assert report["unattended_mode"] == "DISABLED"


def test_tool_and_token_reset_stall():
    now = datetime(2026, 8, 23, 12, 2, tzinfo=timezone.utc)
    events = [
        {"type": "agent_status", "status": "working", "timestamp": "2026-08-23T12:00:00+00:00"},
        {"type": "tool_start", "timestamp": "2026-08-23T12:01:30+00:00"},
    ]
    report = classify_stall(events, now=now, stall_seconds=120)
    assert report["verdict"] == "OK"
    assert report["action"] == "none"


def test_turn_terminal_clears_working():
    now = datetime(2026, 8, 23, 12, 10, tzinfo=timezone.utc)
    events = [
        {"type": "token", "timestamp": "2026-08-23T12:00:00+00:00"},
        {"type": "turn_end", "timestamp": "2026-08-23T12:00:10+00:00"},
        {"type": "agent_status", "status": "idle", "timestamp": "2026-08-23T12:09:00+00:00"},
    ]
    report = classify_stall(events, now=now, stall_seconds=120)
    assert report["verdict"] == "OK"
    assert report["working"] is False
