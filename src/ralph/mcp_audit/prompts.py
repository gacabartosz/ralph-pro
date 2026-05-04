"""Prompt augmentation for MCP audit mode.

Loads the user-provided prompt and tacks on the live tool inventory + state-file
guidance, so Ralph never has to discover them by trial-and-error.
"""
from __future__ import annotations

from ralph.mcp_audit.client import ToolDescriptor

AUDIT_PREAMBLE = """## Tool inventory (live snapshot from the MCP server)

You are auditing an MCP server with the following tools. Iterate through
them systematically — pick the next unchecked entry from `fix_plan.md`,
exercise that one tool with a sensible sample input, and document findings.

"""


def render_tools_section(tools: list[ToolDescriptor]) -> str:
    lines = [AUDIT_PREAMBLE, f"Total tools: **{len(tools)}**", ""]
    for tool in tools:
        first_line = (tool.description or "").splitlines()[0] if tool.description else ""
        lines.append(f"- `{tool.name}` — {first_line[:120]}")
    return "\n".join(lines) + "\n"


def render_initial_fix_plan(tools: list[ToolDescriptor]) -> str:
    """Build a fix_plan.md seeded with one task per tool + cross-cutting tasks."""
    lines = [
        "# fix_plan.md — MCP audit",
        "",
        "Iterate top-to-bottom. Check off as you go. ONE thing per iteration.",
        "",
        "## Phase 1: Tool surface audit",
    ]
    for tool in tools:
        lines.append(f"- [ ] Audit `{tool.name}`: schema valid, sample input works, error handling sane")
    lines += [
        "",
        "## Phase 2: Cross-cutting checks",
        "- [ ] Verify README status table matches actual tool behavior",
        "- [ ] Run all `examples/*.py` and confirm exit 0 + expected output",
        "- [ ] Check XSD validation results for KEDU envelope",
        "- [ ] Spot-check one happy path E2E (e.g. JDG monthly DRA generation)",
        "",
        "## Phase 3: Issues + coverage",
        "- [ ] Populate `ISSUES.md` with documented WIP gaps",
        "- [ ] Populate `COVERAGE.md` checkmarks",
        "",
        "## Phase 4: Exit",
        "- [ ] When all above are checked AND ISSUES.md has at least the known WIP items —",
        "      output exactly: `EXIT_SIGNAL: true`",
        "",
    ]
    return "\n".join(lines)
