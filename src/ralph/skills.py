"""R1 — Skills-as-markdown loader.

A *skill* is a self-contained capability described by ``SKILL.md`` with
YAML frontmatter. Layout::

    ~/.ralph/skills/<name>/
    ├── SKILL.md           ← required (frontmatter + body)
    ├── examples/          ← optional
    └── scripts/           ← optional

Frontmatter shape (compatible with Anthropic ``~/.claude/skills/`` shape)::

    ---
    name: jira-sprint-report
    description: Generuje raport sprintu (Jira + Tempo) jako Confluence draft
    activation:
      patterns:
        - "raport sprintu"
        - "sprint report"
      intent_match: 0.6
    requires_tools:
      - jira_get_sprint_issues
    estimated_cost_usd: 0.30
    ---

Discovery + lazy-load contract:

* ``discover()`` reads frontmatter only — body is *not* loaded into the
  returned descriptor. The LLM system prompt only sees ``name`` +
  ``description`` + activation patterns (cheap).
* ``load_body(skill)`` reads the full markdown body. Call only when
  activation fires (LLM emits ``LOAD_SKILL: <name>``).
* Per-project skills (``<cwd>/.ralph/skills/``) override global skills
  with the same ``name`` — local always wins.

Failure isolation matches plugins.py: a broken ``SKILL.md`` is logged +
telemetry-emitted, Ralph keeps booting.
"""
from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from ralph import telemetry

log = logging.getLogger(__name__)

_DEFAULT_GLOBAL_DIR = Path.home() / ".ralph" / "skills"
_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", re.DOTALL)


def _global_dir() -> Path:
    override = os.environ.get("RALPH_SKILLS_DIR")
    return Path(override) if override else _DEFAULT_GLOBAL_DIR


def _project_dir() -> Path | None:
    override = os.environ.get("RALPH_PROJECT_SKILLS_DIR")
    if override:
        return Path(override)
    cwd_skills = Path.cwd() / ".ralph" / "skills"
    return cwd_skills if cwd_skills.exists() else None


# ─── Public API ────────────────────────────────────────────────────────


@dataclass
class Skill:
    name: str
    description: str
    path: Path
    scope: str  # "global" or "project"
    activation: dict[str, Any] = field(default_factory=dict)
    requires_tools: list[str] = field(default_factory=list)
    estimated_cost_usd: float | None = None
    frontmatter: dict[str, Any] = field(default_factory=dict)

    def system_prompt_line(self) -> str:
        """Cheap one-line representation injected into LLM system prompt."""
        return f"- {self.name}: {self.description}"


def _parse_skill_md(content: str) -> tuple[dict[str, Any], str]:
    """Split a SKILL.md into (frontmatter_dict, body). Raises ValueError on bad shape."""
    m = _FRONTMATTER_RE.match(content)
    if not m:
        raise ValueError("missing YAML frontmatter (expected --- ... --- block at top)")
    raw_fm, body = m.group(1), m.group(2)
    try:
        fm = yaml.safe_load(raw_fm) or {}
    except yaml.YAMLError as e:
        raise ValueError(f"invalid YAML frontmatter: {e}") from e
    if not isinstance(fm, dict):
        raise ValueError(f"frontmatter must be a YAML mapping, got {type(fm).__name__}")
    return fm, body


def _build_skill(skill_md: Path, scope: str) -> Skill | None:
    """Parse one SKILL.md into a Skill descriptor; return None on failure
    (logged + telemetry-emitted)."""
    try:
        content = skill_md.read_text(encoding="utf-8")
    except OSError as e:
        log.warning("skill %s: read failed — %s", skill_md, e)
        telemetry.emit("skill.load_failed", skill=skill_md.parent.name, reason="read_error", error=str(e))
        return None

    try:
        fm, _body = _parse_skill_md(content)
    except ValueError as e:
        log.warning("skill %s: %s", skill_md, e)
        telemetry.emit("skill.load_failed", skill=skill_md.parent.name, reason="parse_error", error=str(e))
        return None

    name = fm.get("name") or skill_md.parent.name
    description = fm.get("description")
    if not description or not isinstance(description, str):
        log.warning("skill %s: missing or non-string `description` in frontmatter", skill_md)
        telemetry.emit("skill.load_failed", skill=name, reason="missing_description")
        return None

    return Skill(
        name=str(name),
        description=description.strip(),
        path=skill_md.parent,
        scope=scope,
        activation=fm.get("activation") or {},
        requires_tools=list(fm.get("requires_tools") or []),
        estimated_cost_usd=fm.get("estimated_cost_usd"),
        frontmatter=fm,
    )


# ─── Loader ────────────────────────────────────────────────────────────


def discover() -> list[Skill]:
    """Scan global + project skill directories; return successfully loaded
    skills with project overriding global by name.

    Errors are logged + telemetry-emitted; broken skills are skipped.
    Returned list is sorted by name for deterministic system prompt order.
    """
    accumulated: dict[str, Skill] = {}

    for root, scope in [(_global_dir(), "global"), (_project_dir(), "project")]:
        if root is None or not root.exists():
            continue
        for entry in sorted(root.iterdir()):
            if not entry.is_dir():
                continue
            skill_md = entry / "SKILL.md"
            if not skill_md.exists():
                log.debug("skipping %s — no SKILL.md", entry)
                continue
            skill = _build_skill(skill_md, scope)
            if skill is None:
                continue
            previous = accumulated.get(skill.name)
            accumulated[skill.name] = skill  # project (loaded second) overrides global
            telemetry.emit(
                "skill.loaded",
                skill=skill.name,
                scope=scope,
                overrode=previous.scope if previous else None,
            )

    result = sorted(accumulated.values(), key=lambda s: s.name)
    log.info("loaded %d skills (global=%s, project=%s)", len(result), _global_dir(), _project_dir())
    return result


def load_body(skill: Skill) -> str:
    """Read the markdown body of a skill (everything after frontmatter).

    Called by the dispatcher only when activation fires. Returns "" if the
    file disappeared between discover() and now (best-effort).
    """
    skill_md = skill.path / "SKILL.md"
    try:
        content = skill_md.read_text(encoding="utf-8")
    except OSError as e:
        log.warning("skill %s: body read failed — %s", skill.name, e)
        telemetry.emit("skill.body_read_failed", skill=skill.name, error=str(e))
        return ""
    try:
        _fm, body = _parse_skill_md(content)
    except ValueError:
        return ""
    return body.strip()


# ─── System prompt injection ──────────────────────────────────────────


SKILLS_SECTION_HEADER = "## Available skills"


def system_prompt_section(skills: list[Skill]) -> str:
    """Render the system-prompt snippet that lists discovered skills.

    Cheap — only ``name + description`` (no body, no patterns). The LLM can
    request the full body by emitting ``LOAD_SKILL: <name>`` which the loop
    intercepts and resolves via ``load_body(skill)``.

    Returns empty string when there are no skills (no header at all — keep
    the prompt clean rather than printing an empty section).
    """
    if not skills:
        return ""
    lines = [SKILLS_SECTION_HEADER, ""]
    lines.extend(s.system_prompt_line() for s in skills)
    lines.append("")
    lines.append('To use one, emit `LOAD_SKILL: <name>` and the loop will inject its body next iteration.')
    return "\n".join(lines)


# ─── Activation (Tier 1: substring match) ─────────────────────────────


def match(skills: list[Skill], query: str) -> list[Skill]:
    """Tier 1 activation: case-insensitive substring match of any
    ``activation.patterns`` entry in the user query.

    R7 will add Tier 2 (embeddings). For now keep it free + deterministic.
    """
    q = query.lower()
    matched = []
    for s in skills:
        patterns = s.activation.get("patterns") or []
        for p in patterns:
            if isinstance(p, str) and p.lower() in q:
                matched.append(s)
                telemetry.emit("skill.matched", skill=s.name, pattern=p)
                break
    return matched
