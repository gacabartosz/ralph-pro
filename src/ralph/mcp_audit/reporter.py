"""Generate audit report skeletons that Ralph fills in across iterations."""
from __future__ import annotations

from pathlib import Path

from ralph.mcp_audit.client import ToolDescriptor

TOOLS_AUDIT_HEADER = """# TOOLS_AUDIT.md — autoaudit findings

| # | Tool | Inputs (sample) | Output snippet | Verdict | Notes |
|---|------|-----------------|----------------|---------|-------|
"""

ISSUES_HEADER = """# ISSUES.md — proposed GitHub issues

(Ralph appends here. We file them manually after review.)

"""

COVERAGE_HEADER = """# COVERAGE.md — which tools are tested

| Tool | Audited | Working | Documented in README |
|------|---------|---------|----------------------|
"""


def init_report_files(worktree_path: Path, tools: list[ToolDescriptor]) -> None:
    """Drop empty TOOLS_AUDIT.md / ISSUES.md / COVERAGE.md skeletons into the worktree."""
    audit = worktree_path / "TOOLS_AUDIT.md"
    if not audit.exists():
        rows = [TOOLS_AUDIT_HEADER]
        for i, tool in enumerate(tools, start=1):
            rows.append(f"| {i} | `{tool.name}` |  |  | ⏳ pending |  |")
        audit.write_text("\n".join(rows) + "\n", encoding="utf-8")

    issues = worktree_path / "ISSUES.md"
    if not issues.exists():
        issues.write_text(ISSUES_HEADER, encoding="utf-8")

    coverage = worktree_path / "COVERAGE.md"
    if not coverage.exists():
        rows = [COVERAGE_HEADER]
        for tool in tools:
            rows.append(f"| `{tool.name}` | ⏳ | ❓ | ❓ |")
        coverage.write_text("\n".join(rows) + "\n", encoding="utf-8")
