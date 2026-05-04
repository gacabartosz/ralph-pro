"""CLI: `ralph runs` lists historic runs from .ralph-runs/."""
from __future__ import annotations

import json
import time
from pathlib import Path

from typer.testing import CliRunner

from ralph.cli import app


def _seed_run(repo: Path, run_id: str, *, iters: int, cost: float, age_seconds: float = 0.0) -> Path:
    run_dir = repo / ".ralph-runs" / run_id
    run_dir.mkdir(parents=True)
    transcript = run_dir / "transcript.jsonl"
    with transcript.open("w", encoding="utf-8") as f:
        for i in range(iters):
            f.write(json.dumps({"iteration": i + 1, "cost_usd": cost / iters}) + "\n")
    if age_seconds:
        old = time.time() - age_seconds
        import os
        os.utime(run_dir, (old, old))
    return run_dir


def test_runs_lists_existing_runs(tmp_path: Path):
    _seed_run(tmp_path, "run-aaa", iters=5, cost=2.0)
    _seed_run(tmp_path, "run-bbb", iters=12, cost=8.5)

    runner = CliRunner()
    result = runner.invoke(app, ["runs", "--repo", str(tmp_path)])
    assert result.exit_code == 0
    # Rich tables get rendered; check for the run ids and cost figures.
    assert "run-aaa" in result.output
    assert "run-bbb" in result.output
    assert "8.5" in result.output


def test_runs_handles_missing_directory(tmp_path: Path):
    runner = CliRunner()
    result = runner.invoke(app, ["runs", "--repo", str(tmp_path)])
    assert result.exit_code == 0
    assert "No .ralph-runs/" in result.output


def test_runs_clean_older_than_removes(tmp_path: Path):
    _seed_run(tmp_path, "run-old", iters=1, cost=0.1, age_seconds=86400 * 60)  # 60d old
    _seed_run(tmp_path, "run-new", iters=1, cost=0.1)

    runner = CliRunner()
    result = runner.invoke(app, ["runs", "--repo", str(tmp_path), "--clean-older-than", "30"])
    assert result.exit_code == 0
    assert (tmp_path / ".ralph-runs" / "run-old").exists() is False
    assert (tmp_path / ".ralph-runs" / "run-new").exists() is True
