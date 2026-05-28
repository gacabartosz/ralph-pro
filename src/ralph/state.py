"""Rolling state for a Ralph loop: PROMPT.md, fix_plan.md, transcript."""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ralph import skills as skills_mod

FIX_PLAN_DEFAULT = """# fix_plan.md

Priority-sorted to-do list. Each iteration: pick the topmost unchecked item,
do ONE thing, update this file (check it off or refine it), then exit.

- [ ] (no plan yet — first iteration should populate this)
"""


@dataclass(slots=True)
class State:
    """Owns the on-disk state files for one run."""

    worktree_path: Path
    output_dir: Path
    prompt_template: str  # raw text of PROMPT.md, copied at start
    completion_signal: str

    @classmethod
    def initialize(
        cls,
        worktree_path: Path,
        output_dir: Path,
        prompt_path: Path,
        completion_signal: str,
    ) -> State:
        """Read PROMPT.md, drop a copy + fix_plan.md skeleton into the worktree."""
        prompt_text = prompt_path.read_text(encoding="utf-8")
        output_dir.mkdir(parents=True, exist_ok=True)

        target_prompt = worktree_path / "PROMPT.md"
        if not target_prompt.exists():
            target_prompt.write_text(prompt_text, encoding="utf-8")

        target_plan = worktree_path / "fix_plan.md"
        if not target_plan.exists():
            target_plan.write_text(FIX_PLAN_DEFAULT, encoding="utf-8")

        return cls(
            worktree_path=worktree_path,
            output_dir=output_dir,
            prompt_template=prompt_text,
            completion_signal=completion_signal,
        )

    @property
    def transcript_path(self) -> Path:
        return self.output_dir / "transcript.jsonl"

    def compose_prompt(self, iteration: int) -> str:
        """Compose the prompt for iteration N: PROMPT.md + fix_plan.md + skills.

        Skills are injected as a cheap descriptor list (name + description
        only). Disable with ``RALPH_SKILLS_ENABLED=0`` if a project wants
        a clean prompt without skill auto-discovery.
        """
        prompt = (self.worktree_path / "PROMPT.md").read_text(encoding="utf-8")
        plan_path = self.worktree_path / "fix_plan.md"
        plan = plan_path.read_text(encoding="utf-8") if plan_path.exists() else FIX_PLAN_DEFAULT
        header = (
            f"# Ralph iteration {iteration}\n\n"
            f"You are running inside an autonomous loop. Do ONE thing per iteration.\n"
            f"When the entire mission is done, output exactly: `{self.completion_signal}`.\n\n"
        )
        skills_section = ""
        if os.environ.get("RALPH_SKILLS_ENABLED", "1") != "0":
            skills_section = skills_mod.system_prompt_section(skills_mod.discover())
            if skills_section:
                skills_section = "\n\n" + skills_section
        return header + prompt + "\n\n## Current fix_plan.md\n\n" + plan + skills_section

    def append_transcript(self, record: dict[str, Any]) -> None:
        record = {"ts": time.time(), **record}
        with self.transcript_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
