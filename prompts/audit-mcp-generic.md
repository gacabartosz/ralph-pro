# Mission: audit an arbitrary MCP server

You are auditing an MCP server end-to-end. The live tool inventory is appended below.

## Mode of operation

Each iteration: pick the topmost unchecked task from `@fix_plan.md`, do ONE thing, update `@TOOLS_AUDIT.md` / `@ISSUES.md` / `@COVERAGE.md`, exit.

## Per-tool smoke template

For every tool:

1. Read the input schema in the inventory.
2. Construct a minimal valid input (use safe defaults; nothing destructive).
3. Call the tool via the MCP server (stdio JSON-RPC).
4. Record: success/fail, output snippet, observation.
5. If fail: document in `ISSUES.md` (no fix attempt).

## State files

- `@fix_plan.md` — priority-sorted to-do.
- `@TOOLS_AUDIT.md` — one row per tool.
- `@ISSUES.md` — proposed issues (markdown).
- `@COVERAGE.md` — checkbox matrix.

## Rules

- ONE thing per iteration.
- No code changes to the server under audit.
- No external network calls except as the tool requires.
- Cite stderr/stdout evidence in every `TOOLS_AUDIT.md` row.

## Exit

When every tool has a verdict and `ISSUES.md` is populated, output: `EXIT_SIGNAL: true`.
