"""Loop — end-to-end dry run hits the budget cap and exits cleanly."""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from ralph.config import RunConfig
from ralph.loop import RunStatus, run


@pytest.fixture
def temp_git_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "-C", str(repo), "init", "-b", "main"], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.email", "test@example.com"],
        check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.name", "Test"],
        check=True, capture_output=True,
    )
    (repo / "README.md").write_text("hello", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-m", "init", "--no-verify"],
        check=True, capture_output=True,
    )
    return repo


def test_dry_run_loop_hits_iteration_cap(temp_git_repo: Path, tmp_path: Path):
    prompt = tmp_path / "PROMPT.md"
    prompt.write_text("# Test\n\nDo nothing.", encoding="utf-8")

    config = RunConfig(
        run_id="test-dry",
        repo_path=temp_git_repo,
        prompt_path=prompt,
        max_iterations=3,
        max_cost_usd=10.0,
        circuit_breaker_enabled=False,
        dry_run=True,
    )
    result = run(config)

    assert result.status == RunStatus.ITERATIONS_EXHAUSTED
    assert result.iterations == 3
    assert result.total_cost_usd == 0.0


def test_dry_run_completion_signal_terminates(temp_git_repo: Path, tmp_path: Path):
    """If we make the dry-run text contain both signals, loop terminates."""
    from unittest.mock import patch

    from ralph.runner import ClaudeResult

    prompt = tmp_path / "PROMPT.md"
    prompt.write_text("# Test\n\nDo nothing.", encoding="utf-8")

    fake = ClaudeResult(
        success=True,
        text="all tasks complete\nEXIT_SIGNAL: true",
        cost_usd=0.0,
        duration_s=0.01,
        raw_json=None,
        stderr="",
        return_code=0,
    )

    with patch("ralph.loop.runner.invoke_claude", return_value=fake):
        config = RunConfig(
            run_id="test-complete",
            repo_path=temp_git_repo,
            prompt_path=prompt,
            max_iterations=10,
            max_cost_usd=10.0,
            circuit_breaker_enabled=False,
            dry_run=True,
        )
        result = run(config)

    assert result.status == RunStatus.COMPLETE
    assert result.iterations == 1
