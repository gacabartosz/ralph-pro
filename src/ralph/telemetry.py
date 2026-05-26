"""R0 — Telemetry hook.

Append-only JSONL stream of every notable event in a Ralph run. Lives at
``~/.ralph/telemetry/events.jsonl`` by default; overridable via
``RALPH_TELEMETRY_PATH``. Set ``RALPH_TELEMETRY=0`` to disable entirely
(useful in tests).

Format: one JSON object per line with ``ts`` (ISO 8601 UTC), ``event``
(string), and arbitrary additional keys. No schema enforcement — caller
controls payload shape. R7 (memory) and R9 (dashboard) consume this.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

_DEFAULT_PATH = Path.home() / ".ralph" / "telemetry" / "events.jsonl"


def _enabled() -> bool:
    return os.environ.get("RALPH_TELEMETRY", "1") != "0"


def _path() -> Path:
    override = os.environ.get("RALPH_TELEMETRY_PATH")
    return Path(override) if override else _DEFAULT_PATH


def emit(event: str, **fields: Any) -> None:
    """Append one event to the telemetry log.

    Best-effort: never raises — telemetry failure must not break a Ralph run.
    """
    if not _enabled():
        return
    try:
        record = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            "event": event,
            **fields,
        }
        path = _path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str) + "\n")
    except Exception as e:  # pragma: no cover — defensive
        log.warning("telemetry emit failed for event=%s: %s", event, e)


def read_tail(n: int = 100) -> list[dict[str, Any]]:
    """Read the last ``n`` events. Returns [] when telemetry is disabled or
    the file doesn't exist yet."""
    path = _path()
    if not path.exists():
        return []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
        return [json.loads(line) for line in lines[-n:] if line.strip()]
    except Exception as e:
        log.warning("telemetry read_tail failed: %s", e)
        return []
