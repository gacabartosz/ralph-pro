"""R1 — skills loader tests.

The critical property: a broken SKILL.md (missing frontmatter, bad YAML,
missing description) must never crash Ralph. Failure isolation mirrors
plugins.py — broken skills are skipped, good skills load.
"""
from __future__ import annotations

import textwrap

import pytest

from ralph import skills, telemetry


def _write_skill(root, name, content):
    d = root / name
    d.mkdir()
    (d / "SKILL.md").write_text(textwrap.dedent(content).lstrip())


GOOD_SKILL = """\
---
name: hello-world
description: Says hello to the user
activation:
  patterns:
    - "say hello"
    - "hello world"
requires_tools:
  - greet
estimated_cost_usd: 0.01
---

# Hello world skill

Steps:
1. Greet the user
"""

MINIMAL_SKILL = """\
---
name: minimal
description: just a description, nothing else
---
body here
"""

NO_FRONTMATTER = """\
# Just a markdown file

No frontmatter at all.
"""

BAD_YAML = """\
---
name: bad
description: has bad yaml
activation: [unclosed
---
body
"""

MISSING_DESCRIPTION = """\
---
name: no-desc
activation:
  patterns: ["foo"]
---
body
"""

NON_MAPPING_FRONTMATTER = """\
---
- just
- a
- list
---
body
"""


@pytest.fixture
def skills_dir(tmp_path, monkeypatch):
    d = tmp_path / "skills"
    d.mkdir()
    monkeypatch.setenv("RALPH_SKILLS_DIR", str(d))
    monkeypatch.setenv("RALPH_TELEMETRY_PATH", str(tmp_path / "tel.jsonl"))
    # Disable project skills auto-discovery from cwd
    monkeypatch.setenv("RALPH_PROJECT_SKILLS_DIR", str(tmp_path / "nonexistent"))
    return d


def test_discover_loads_good_skill(skills_dir):
    _write_skill(skills_dir, "hello", GOOD_SKILL)
    loaded = skills.discover()
    assert len(loaded) == 1
    s = loaded[0]
    assert s.name == "hello-world"
    assert s.description == "Says hello to the user"
    assert s.scope == "global"
    assert s.requires_tools == ["greet"]
    assert s.estimated_cost_usd == 0.01
    assert s.activation["patterns"] == ["say hello", "hello world"]


def test_discover_loads_minimal_skill(skills_dir):
    _write_skill(skills_dir, "minimal", MINIMAL_SKILL)
    loaded = skills.discover()
    assert len(loaded) == 1
    assert loaded[0].name == "minimal"
    assert loaded[0].activation == {}
    assert loaded[0].requires_tools == []


def test_discover_skips_no_frontmatter(skills_dir):
    _write_skill(skills_dir, "naked", NO_FRONTMATTER)
    assert skills.discover() == []


def test_discover_skips_bad_yaml(skills_dir):
    _write_skill(skills_dir, "bad", BAD_YAML)
    assert skills.discover() == []


def test_discover_skips_missing_description(skills_dir):
    _write_skill(skills_dir, "nodesc", MISSING_DESCRIPTION)
    assert skills.discover() == []


def test_discover_skips_non_mapping_frontmatter(skills_dir):
    _write_skill(skills_dir, "list_fm", NON_MAPPING_FRONTMATTER)
    assert skills.discover() == []


def test_discover_continues_after_one_broken(skills_dir):
    _write_skill(skills_dir, "a_good", GOOD_SKILL)
    _write_skill(skills_dir, "b_bad", BAD_YAML)
    _write_skill(skills_dir, "c_minimal", MINIMAL_SKILL)
    loaded = skills.discover()
    names = sorted(s.name for s in loaded)
    assert names == ["hello-world", "minimal"]  # b_bad skipped, others kept


def test_discover_sorted_by_name(skills_dir):
    _write_skill(skills_dir, "z_dir", textwrap.dedent("""\
        ---
        name: zebra
        description: z
        ---
    """))
    _write_skill(skills_dir, "a_dir", textwrap.dedent("""\
        ---
        name: alpha
        description: a
        ---
    """))
    names = [s.name for s in skills.discover()]
    assert names == ["alpha", "zebra"]


def test_project_overrides_global(tmp_path, monkeypatch):
    global_dir = tmp_path / "global"
    project_dir = tmp_path / "project"
    global_dir.mkdir()
    project_dir.mkdir()
    monkeypatch.setenv("RALPH_SKILLS_DIR", str(global_dir))
    monkeypatch.setenv("RALPH_PROJECT_SKILLS_DIR", str(project_dir))
    monkeypatch.setenv("RALPH_TELEMETRY_PATH", str(tmp_path / "tel.jsonl"))

    _write_skill(global_dir, "shared", textwrap.dedent("""\
        ---
        name: shared
        description: global version
        ---
    """))
    _write_skill(project_dir, "shared", textwrap.dedent("""\
        ---
        name: shared
        description: project override
        ---
    """))

    loaded = skills.discover()
    assert len(loaded) == 1
    assert loaded[0].description == "project override"
    assert loaded[0].scope == "project"


def test_load_body_returns_content(skills_dir):
    _write_skill(skills_dir, "hello", GOOD_SKILL)
    loaded = skills.discover()
    body = skills.load_body(loaded[0])
    assert "# Hello world skill" in body
    assert "Greet the user" in body
    # frontmatter must NOT leak into body
    assert "---" not in body.split("\n")[0]


def test_match_substring_activation(skills_dir):
    _write_skill(skills_dir, "hello", GOOD_SKILL)
    _write_skill(skills_dir, "minimal", MINIMAL_SKILL)
    loaded = skills.discover()

    # GOOD_SKILL has pattern "say hello"
    matched = skills.match(loaded, "Please SAY HELLO to the user")
    assert [m.name for m in matched] == ["hello-world"]

    # No pattern match
    assert skills.match(loaded, "do something else entirely") == []


def test_match_skill_with_no_patterns(skills_dir):
    _write_skill(skills_dir, "minimal", MINIMAL_SKILL)  # no activation block
    loaded = skills.discover()
    assert skills.match(loaded, "anything goes") == []


def test_system_prompt_line(skills_dir):
    _write_skill(skills_dir, "hello", GOOD_SKILL)
    [s] = skills.discover()
    line = s.system_prompt_line()
    assert line == "- hello-world: Says hello to the user"


def test_telemetry_records_load_and_failures(skills_dir):
    _write_skill(skills_dir, "ok", GOOD_SKILL)
    _write_skill(skills_dir, "broken", BAD_YAML)
    skills.discover()
    events = telemetry.read_tail(50)
    loaded_events = [e for e in events if e["event"] == "skill.loaded"]
    failed_events = [e for e in events if e["event"] == "skill.load_failed"]
    assert any(e.get("skill") == "hello-world" for e in loaded_events)
    assert any(e.get("skill") == "broken" for e in failed_events)
