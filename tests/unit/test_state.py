"""State — PROMPT.md / fix_plan.md round-trip + transcript."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from ralph.state import State


@pytest.fixture
def setup_dirs(tmp_path: Path) -> tuple[Path, Path, Path]:
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    output = tmp_path / "out"
    output.mkdir()
    prompt = tmp_path / "PROMPT.md"
    prompt.write_text("# Test mission\n\nDo a thing.", encoding="utf-8")
    return worktree, output, prompt


def test_initialize_drops_prompt_and_fix_plan(setup_dirs: tuple[Path, Path, Path]):
    worktree, output, prompt = setup_dirs
    state = State.initialize(worktree, output, prompt, "EXIT_SIGNAL: true")
    assert (worktree / "PROMPT.md").exists()
    assert (worktree / "fix_plan.md").exists()
    assert "Test mission" in (worktree / "PROMPT.md").read_text(encoding="utf-8")
    assert state.completion_signal == "EXIT_SIGNAL: true"


def test_compose_prompt_includes_fix_plan(setup_dirs: tuple[Path, Path, Path]):
    worktree, output, prompt = setup_dirs
    state = State.initialize(worktree, output, prompt, "EXIT_SIGNAL: true")
    composed = state.compose_prompt(iteration=3)
    assert "Ralph iteration 3" in composed
    assert "Test mission" in composed
    assert "fix_plan.md" in composed.lower()


def test_compose_prompt_picks_up_updated_plan(setup_dirs: tuple[Path, Path, Path]):
    worktree, output, prompt = setup_dirs
    state = State.initialize(worktree, output, prompt, "EXIT_SIGNAL: true")
    (worktree / "fix_plan.md").write_text("- [x] done\n- [ ] next thing\n", encoding="utf-8")
    composed = state.compose_prompt(iteration=2)
    assert "next thing" in composed


def test_transcript_appends_jsonl(setup_dirs: tuple[Path, Path, Path]):
    worktree, output, prompt = setup_dirs
    state = State.initialize(worktree, output, prompt, "EXIT_SIGNAL: true")
    state.append_transcript({"iteration": 1, "summary": "first"})
    state.append_transcript({"iteration": 2, "summary": "second"})
    lines = state.transcript_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    rec = json.loads(lines[1])
    assert rec["iteration"] == 2
    assert rec["summary"] == "second"
    assert "ts" in rec
