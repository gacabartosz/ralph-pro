# ralph-claude-code

> **Ralph Wiggum loop for Claude Code with cost caps, worktree isolation, and MCP audit mode.**
> Pattern: [ghuntley.com/ralph](https://ghuntley.com/ralph/) — `while :; do cat PROMPT.md | claude -p; done` made production-safe.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Status: Alpha](https://img.shields.io/badge/status-alpha-orange.svg)]()

## What it does

- Wraps `claude -p` in a budget-bounded loop (max iterations, max USD, hard timeout).
- Runs each iteration inside an **isolated git worktree** so the host repo is never modified mid-flight.
- Auto-commits each iteration, **never pushes** — push is a human decision.
- Reads `PROMPT.md` + `fix_plan.md` rolling state between iterations (canonical Ralph pattern).
- **Specialized `audit-mcp` mode**: connects to any MCP server over stdio, lists every tool, calls each one, cross-checks against README claims, and writes `TOOLS_AUDIT.md` + `ISSUES.md`.
- Optional OpenTelemetry export (compatible with `claude-code-otel`).

## Why

Three motivations:

1. **Audit your own MCP servers.** When you ship an MCP server, you want a senior-AI-engineer-level audit run end-to-end against the real server. Ralph does it for $5–$20 per pass.
2. **Productionize Ralph.** The community pattern is `while true; do …; done` in bash — fine for hacking, scary for unattended runs. This adds cost cap, circuit breaker, worktree isolation, transcript.
3. **Reusable harness.** The same tool audits any MCP — first beneficiary is `mcp-zus`, but works against `ksef-mcp`, `ezd-puw-mcp`, or any third-party server.

## Quickstart

```bash
git clone https://github.com/gacabartosz/ralph-claude-code.git
cd ralph-claude-code
uv sync --all-extras

# Dry-run smoke test (no API calls):
uv run ralph audit-mcp --dry-run \
    --mcp-cmd "echo fake" \
    --max-iterations 3 --max-cost 1.00

# Real audit of mcp-zus:
uv run ralph audit-mcp \
    --mcp-cmd "uv run --directory /path/to/mcp-zus mcp-zus" \
    --prompt prompts/audit-mcp-zus.md \
    --model claude-opus-4-7 \
    --max-iterations 30 --max-cost 20.00 \
    --branch ralph/audit-mcp-zus
```

## CLI

| Command | What it does |
|---------|--------------|
| `ralph run` | Generic Ralph loop — `--prompt`, `--max-iterations`, `--max-cost` |
| `ralph audit-mcp` | MCP test-harness mode — `--mcp-cmd`, `--prompt`, `--branch` |
| `ralph status <run-id>` | Show current state of a running or finished loop |

## Safety rails

| Rail | Default | Override |
|------|---------|----------|
| Iteration cap | 30 (audit-mcp) | `--max-iterations` |
| Cost cap (USD) | $20 | `--max-cost` |
| Per-iteration timeout | 600s | `--iteration-timeout` |
| Circuit breaker | 3 no-op iters OR 5 error iters | `--no-circuit-breaker` to disable |
| Worktree isolation | yes | `--no-worktree` (NOT recommended) |
| Push to remote | **never** | n/a |
| Allowed tools | safe whitelist | `--allowed-tools` |

## Status: Alpha v0.1.0

Audited and exercised in real runs against `gacabartosz/mcp-zus`. Use with care, watch the budget, read transcripts after each run.

## License

MIT © 2026 Bartosz Gaca

## Credits

Pattern: Geoffrey Huntley — [ghuntley.com/ralph](https://ghuntley.com/ralph/) and [ghuntley.com/loop](https://ghuntley.com/loop/).
Reference impl that informed design: [`frankbria/ralph-claude-code`](https://github.com/frankbria/ralph-claude-code), [`snarktank/ralph`](https://github.com/snarktank/ralph), Anthropic's official `/ralph-loop` plugin.
