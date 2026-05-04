"""Runner — dry-run stub returns valid ClaudeResult without spawning claude."""
from __future__ import annotations

from pathlib import Path

from ralph.runner import invoke_claude


def test_dry_run_returns_success(tmp_path: Path):
    result = invoke_claude(
        prompt="hello",
        cwd=tmp_path,
        model="claude-opus-4-7",
        allowed_tools=["Read"],
        dry_run=True,
    )
    assert result.success
    assert result.return_code == 0
    assert result.cost_usd == 0.0
    assert "dry-run" in result.text
    assert not result.is_error
