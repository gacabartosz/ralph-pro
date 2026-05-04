# Mission: full audit of `gacabartosz/mcp-zus`

You are a senior AI engineer auditing the `mcp-zus` MCP server end-to-end.

- **Repo (live):** https://github.com/gacabartosz/mcp-zus
- **Local path:** `/Users/gaca/projects/personal/mcp-zus`
- **Goal:** verify every claim in `mcp-zus/README.md` against real tool behavior, document findings, prepare a list of GitHub issues to file.

## Mode of operation

Each iteration: pick **one** unchecked item from `@fix_plan.md`, do exactly that, update the relevant report files, then exit. **Never** try to fix `mcp-zus`; only audit and document.

## Phase plan

1. **Tool surface audit** — for each MCP tool: confirm the input schema is valid JSON Schema, the description is non-empty and accurate, and the name conforms to `<module>.<action>`.
2. **Per-tool smoke test** — call each tool with a sensible default input. Record:
   - Did it return without error?
   - Does the output match what the tool claims to produce?
   - Are error messages clear when the input is bad?
3. **README cross-check** — open `mcp-zus/README.md`, read the status table, compare each ✅/🟡 claim against actual behavior. Flag mismatches.
4. **XSD validation deep dive** — call `kedu.build_dra` with a minimal payload. Pass output through `kedu.validate`. Document the EXACT XSD errors that come back (we know inner sections I-XIV are WIP).
5. **OK-WUD live test** — build an OK-WUD XML for a court (`kod=S`); validate against `okwud_2020_12_29.xsd`.
6. **Crypto BYO flow** — `crypto.prepare_signing_payload` → fake-sign with a placeholder signature → `crypto.attach_signature` → re-parse → confirm `<ds:Signature>` element exists.
7. **Examples sanity check** — run `examples/jdg_monthly_dra.py`, `examples/register_employee.py`, `examples/okwud_kazus.py`. Each should exit 0.

## State files (in your worktree)

- `@fix_plan.md` — priority-sorted to-do; check off as you go.
- `@TOOLS_AUDIT.md` — append-only audit table (one row per tool).
- `@ISSUES.md` — proposed GitHub issues (markdown).
- `@COVERAGE.md` — checkmark matrix per tool.

## How to call MCP tools

The MCP server is launched via stdio with this exact command (already used by the Ralph harness for tool discovery):

```bash
uv run --directory /Users/gaca/projects/personal/mcp-zus mcp-zus
```

To exercise a tool yourself, write a tiny Python helper inside the worktree that uses the `mcp` SDK or raw JSON-RPC over stdio (initialize → notifications/initialized → tools/call). Do NOT modify `mcp-zus` source — only call into it.

## Rules

- **Do ONE thing per iteration.** Don't batch.
- **DO NOT IMPLEMENT PLACEHOLDER OR SIMPLE IMPLEMENTATIONS.** Audit only.
- **No fixes.** If a tool misbehaves, document it in `ISSUES.md` and move on.
- **Stay inside the worktree.** Never touch other repos or push to remote.
- **Use real MCP calls.** When you need to exercise a tool, run a one-shot stdio script that initializes + tools/call. Don't invent behavior.
- **Cite your evidence.** Every TOOLS_AUDIT row must reference the exact stderr/stdout snippet you observed.

## Exit criterion

When **all** of the following are true:

- Every tool from the MCP `tools/list` has a row in `TOOLS_AUDIT.md` with a verdict (✅ working / 🟡 partial / ❌ broken).
- All four examples have been run and recorded.
- `ISSUES.md` documents at least the known WIP gaps (KEDU inner sections, PUE selectors, EWD/OK-WUD live calls).
- `COVERAGE.md` is fully filled in.
- README claims are cross-checked against reality.

…output exactly the line: `EXIT_SIGNAL: true` and stop.
