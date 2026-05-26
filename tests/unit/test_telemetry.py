"""R0 — telemetry tests."""
from __future__ import annotations

import json
import os

from ralph import telemetry


def test_emit_appends_event(tmp_path, monkeypatch):
    log_path = tmp_path / "events.jsonl"
    monkeypatch.setenv("RALPH_TELEMETRY_PATH", str(log_path))

    telemetry.emit("test.foo", a=1, b="hello")
    telemetry.emit("test.bar", run_id="r_xyz")

    lines = log_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    a, b = json.loads(lines[0]), json.loads(lines[1])
    assert a["event"] == "test.foo" and a["a"] == 1 and a["b"] == "hello"
    assert b["event"] == "test.bar" and b["run_id"] == "r_xyz"
    assert "ts" in a and "ts" in b


def test_emit_disabled(tmp_path, monkeypatch):
    log_path = tmp_path / "events.jsonl"
    monkeypatch.setenv("RALPH_TELEMETRY_PATH", str(log_path))
    monkeypatch.setenv("RALPH_TELEMETRY", "0")

    telemetry.emit("test.should_not_appear")
    assert not log_path.exists()


def test_emit_never_raises(tmp_path, monkeypatch):
    # Point at a path inside a regular file (not a dir) → write should fail
    # but emit must swallow the error.
    blocker = tmp_path / "blocker"
    blocker.write_text("x")
    bad_path = blocker / "events.jsonl"     # invalid parent
    monkeypatch.setenv("RALPH_TELEMETRY_PATH", str(bad_path))

    telemetry.emit("test.should_not_raise")  # would explode if not caught


def test_read_tail_returns_recent(tmp_path, monkeypatch):
    log_path = tmp_path / "events.jsonl"
    monkeypatch.setenv("RALPH_TELEMETRY_PATH", str(log_path))

    for i in range(5):
        telemetry.emit("test.iter", n=i)

    tail = telemetry.read_tail(3)
    assert [e["n"] for e in tail] == [2, 3, 4]


def test_read_tail_missing_file(tmp_path, monkeypatch):
    monkeypatch.setenv("RALPH_TELEMETRY_PATH", str(tmp_path / "nope.jsonl"))
    assert telemetry.read_tail(10) == []
