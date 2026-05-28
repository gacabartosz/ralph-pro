"""State — PROMPT.md / fix_plan.md round-trip + transcript."""
from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest

from ralph.state import State


@pytest.fixture
def setup_dirs(tmp_path: Path, monkeypatch) -> tuple[Path, Path, Path]:
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    output = tmp_path / "out"
    output.mkdir()
    prompt = tmp_path / "PROMPT.md"
    prompt.write_text("# Test mission\n\nDo a thing.", encoding="utf-8")
    # Isolate skills discovery so global ~/.ralph/skills/ does not leak in.
    monkeypatch.setenv("RALPH_SKILLS_DIR", str(tmp_path / "no_skills"))
    monkeypatch.setenv("RALPH_PROJECT_SKILLS_DIR", str(tmp_path / "no_proj_skills"))
    monkeypatch.setenv("RALPH_TELEMETRY_PATH", str(tmp_path / "tel.jsonl"))
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


def test_compose_prompt_injects_skills_section(tmp_path: Path, monkeypatch):
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    output = tmp_path / "out"
    output.mkdir()
    prompt = tmp_path / "PROMPT.md"
    prompt.write_text("# Mission", encoding="utf-8")
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    (skills_dir / "demo").mkdir()
    (skills_dir / "demo" / "SKILL.md").write_text(textwrap.dedent("""\
        ---
        name: demo
        description: demo skill for state injection
        ---
        body
    """))
    monkeypatch.setenv("RALPH_SKILLS_DIR", str(skills_dir))
    monkeypatch.setenv("RALPH_PROJECT_SKILLS_DIR", str(tmp_path / "no_proj"))
    monkeypatch.setenv("RALPH_TELEMETRY_PATH", str(tmp_path / "tel.jsonl"))

    state = State.initialize(worktree, output, prompt, "EXIT_SIGNAL: true")
    composed = state.compose_prompt(iteration=1)
    assert "## Available skills" in composed
    assert "- demo: demo skill for state injection" in composed
    assert "LOAD_SKILL:" in composed


def test_compose_prompt_omits_skills_section_when_disabled(tmp_path: Path, monkeypatch):
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    output = tmp_path / "out"
    output.mkdir()
    prompt = tmp_path / "PROMPT.md"
    prompt.write_text("# Mission", encoding="utf-8")
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    (skills_dir / "demo").mkdir()
    (skills_dir / "demo" / "SKILL.md").write_text("---\nname: d\ndescription: x\n---\n")
    monkeypatch.setenv("RALPH_SKILLS_DIR", str(skills_dir))
    monkeypatch.setenv("RALPH_PROJECT_SKILLS_DIR", str(tmp_path / "no_proj"))
    monkeypatch.setenv("RALPH_TELEMETRY_PATH", str(tmp_path / "tel.jsonl"))
    monkeypatch.setenv("RALPH_SKILLS_ENABLED", "0")

    state = State.initialize(worktree, output, prompt, "EXIT_SIGNAL: true")
    composed = state.compose_prompt(iteration=1)
    assert "## Available skills" not in composed


def test_compose_prompt_omits_skills_section_when_none_discovered(setup_dirs):
    worktree, output, prompt = setup_dirs
    state = State.initialize(worktree, output, prompt, "EXIT_SIGNAL: true")
    composed = state.compose_prompt(iteration=1)
    # setup_dirs already points RALPH_SKILLS_DIR at an empty path
    assert "## Available skills" not in composed


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
