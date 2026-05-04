"""mcp_audit.prompts + reporter helpers."""
from __future__ import annotations

from pathlib import Path

from ralph.mcp_audit.client import ToolDescriptor
from ralph.mcp_audit.prompts import render_initial_fix_plan, render_tools_section
from ralph.mcp_audit.reporter import init_report_files


def _tools() -> list[ToolDescriptor]:
    return [
        ToolDescriptor(name="kedu.build_dra", description="Build DRA", input_schema={}),
        ToolDescriptor(name="okwud.list_kody_instytucji", description="List codes", input_schema={}),
    ]


def test_render_tools_section_lists_all():
    section = render_tools_section(_tools())
    assert "kedu.build_dra" in section
    assert "okwud.list_kody_instytucji" in section
    assert "Total tools: **2**" in section


def test_render_initial_fix_plan_seeds_one_per_tool():
    plan = render_initial_fix_plan(_tools())
    assert plan.count("- [ ] Audit `") == 2
    assert "EXIT_SIGNAL: true" in plan


def test_init_report_files_creates_skeletons(tmp_path: Path):
    init_report_files(tmp_path, _tools())
    assert (tmp_path / "TOOLS_AUDIT.md").exists()
    assert (tmp_path / "ISSUES.md").exists()
    assert (tmp_path / "COVERAGE.md").exists()
    assert "kedu.build_dra" in (tmp_path / "TOOLS_AUDIT.md").read_text(encoding="utf-8")
    assert "kedu.build_dra" in (tmp_path / "COVERAGE.md").read_text(encoding="utf-8")
