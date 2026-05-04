"""Dual-condition exit detection.

Per Huntley + frankbria:
    - Explicit signal (e.g. `EXIT_SIGNAL: true`) is the primary trigger.
    - A heuristic check ("seems-done" language) is the secondary signal.
    - Both must agree to terminate, otherwise we keep looping.
"""
from __future__ import annotations

import re

_DONE_PHRASES = [
    "all tasks complete",
    "all tools audited",
    "audit complete",
    "nothing more to do",
    "task fully completed",
    "all items in fix_plan completed",
]
_DONE_RE = re.compile("|".join(re.escape(p) for p in _DONE_PHRASES), re.IGNORECASE)


def is_complete(claude_output_text: str, completion_signal: str, *, require_both: bool = True) -> bool:
    """Decide whether the loop should terminate cleanly.

    Args:
        claude_output_text: full text of last claude response (assistant_text + result).
        completion_signal: exact string the prompt told claude to emit on success.
        require_both: if True, both signal AND heuristic must hit (recommended).

    Returns:
        True iff the loop should stop with status=complete.
    """
    if not claude_output_text:
        return False

    explicit_hit = completion_signal in claude_output_text
    heuristic_hit = bool(_DONE_RE.search(claude_output_text))

    if require_both:
        return explicit_hit and heuristic_hit
    return explicit_hit or heuristic_hit
