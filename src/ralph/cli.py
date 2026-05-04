"""ralph CLI — Typer entry point."""
from __future__ import annotations

import asyncio
import logging
import shlex
import sys
import uuid
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from ralph.config import DEFAULT_ALLOWED_TOOLS, RunConfig
from ralph.loop import RunStatus
from ralph.loop import run as run_loop
from ralph.mcp_audit.client import McpStdioClient
from ralph.mcp_audit.prompts import render_initial_fix_plan, render_tools_section
from ralph.mcp_audit.reporter import init_report_files

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)

app = typer.Typer(
    name="ralph",
    help="Ralph Wiggum loop for Claude Code (https://ghuntley.com/ralph/)",
    no_args_is_help=True,
    add_completion=False,
)
console = Console(stderr=True)


@app.command(name="run")
def cmd_run(
    prompt: Path = typer.Option(..., "--prompt", help="Path to PROMPT.md"),
    repo: Path = typer.Option(Path.cwd(), "--repo", help="Repo to work in (must be git)"),
    model: str = typer.Option("claude-opus-4-7", "--model"),
    max_iterations: int = typer.Option(30, "--max-iterations"),
    max_cost: float = typer.Option(20.0, "--max-cost"),
    iteration_timeout: int = typer.Option(600, "--iteration-timeout"),
    branch: str | None = typer.Option(None, "--branch"),
    no_worktree: bool = typer.Option(False, "--no-worktree"),
    keep: bool = typer.Option(False, "--keep"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    completion_signal: str = typer.Option("EXIT_SIGNAL: true", "--completion-signal"),
):
    """Generic Ralph loop — prompt-driven, no MCP specialization."""
    run_id = _gen_run_id()
    config = RunConfig(
        run_id=run_id,
        repo_path=repo.resolve(),
        prompt_path=prompt.resolve(),
        max_iterations=max_iterations,
        max_cost_usd=max_cost,
        iteration_timeout_s=iteration_timeout,
        model=model,
        branch_name=branch,
        use_worktree=not no_worktree,
        keep_worktree_on_success=keep,
        dry_run=dry_run,
        completion_signal=completion_signal,
    )
    result = run_loop(config)
    _print_result(result)
    raise typer.Exit(code=0 if result.status == RunStatus.COMPLETE else 1)


@app.command(name="audit-mcp")
def cmd_audit_mcp(
    mcp_cmd: str = typer.Option(..., "--mcp-cmd", help="Shell command that spawns the MCP server (stdio)"),
    prompt: Path = typer.Option(..., "--prompt", help="Path to PROMPT.md"),
    repo: Path = typer.Option(Path.cwd(), "--repo"),
    model: str = typer.Option("claude-opus-4-7", "--model"),
    max_iterations: int = typer.Option(30, "--max-iterations"),
    max_cost: float = typer.Option(20.0, "--max-cost"),
    iteration_timeout: int = typer.Option(600, "--iteration-timeout"),
    branch: str | None = typer.Option(None, "--branch"),
    keep: bool = typer.Option(False, "--keep"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    completion_signal: str = typer.Option("EXIT_SIGNAL: true", "--completion-signal"),
    skip_tool_discovery: bool = typer.Option(False, "--skip-tool-discovery", help="Skip live MCP tools/list call"),
):
    """Audit an MCP server end-to-end with a Ralph loop."""
    run_id = _gen_run_id("audit")
    mcp_cmd_list = shlex.split(mcp_cmd)

    config = RunConfig(
        run_id=run_id,
        repo_path=repo.resolve(),
        prompt_path=prompt.resolve(),
        max_iterations=max_iterations,
        max_cost_usd=max_cost,
        iteration_timeout_s=iteration_timeout,
        model=model,
        branch_name=branch or f"ralph/audit-{run_id}",
        keep_worktree_on_success=keep,
        dry_run=dry_run,
        completion_signal=completion_signal,
        mcp_cmd=mcp_cmd_list,
    )

    if not skip_tool_discovery and not dry_run:
        console.print(f"[cyan]Discovering tools from MCP server: {mcp_cmd}[/cyan]")
        try:
            tools = asyncio.run(_discover_tools(mcp_cmd_list))
            console.print(f"[green]Found {len(tools)} tools.[/green]")
        except Exception as exc:  # noqa: BLE001
            console.print(f"[yellow]Tool discovery failed ({exc}); continuing without inventory.[/yellow]")
            tools = []
    else:
        tools = []

    if tools:
        # Augment prompt with live inventory; write augmented copy alongside the run.
        config.resolved_output_dir.mkdir(parents=True, exist_ok=True)
        augmented = (
            prompt.read_text(encoding="utf-8")
            + "\n\n"
            + render_tools_section(tools)
        )
        augmented_path = config.resolved_output_dir / "PROMPT.augmented.md"
        augmented_path.write_text(augmented, encoding="utf-8")
        config = config.model_copy(update={"prompt_path": augmented_path})

        # Pre-seed fix_plan.md and report skeletons inside the (future) worktree —
        # we'll do it again after worktree creation; State.initialize is idempotent.

    result = run_loop(config)

    # If we have tools and the worktree was created — drop reports skeletons.
    if tools and result.worktree_path:
        wt_path = Path(result.worktree_path)
        if wt_path.exists():
            init_report_files(wt_path, tools)
            (wt_path / "fix_plan.md").write_text(render_initial_fix_plan(tools), encoding="utf-8")

    _print_result(result)
    raise typer.Exit(code=0 if result.status == RunStatus.COMPLETE else 1)


@app.command(name="status")
def cmd_status(
    run_dir: Path = typer.Argument(..., help="Path to .ralph-runs/<run-id>/"),
):
    """Inspect a (running or finished) Ralph run."""
    transcript = run_dir / "transcript.jsonl"
    if not transcript.exists():
        console.print(f"[red]No transcript found at {transcript}[/red]")
        raise typer.Exit(code=1)

    import json as _json

    rows = []
    total_cost = 0.0
    for line in transcript.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            r = _json.loads(line)
        except _json.JSONDecodeError:
            continue
        rows.append(r)
        total_cost += float(r.get("cost_usd", 0.0))

    table = Table(title=f"Ralph run: {run_dir.name}")
    table.add_column("#", justify="right")
    table.add_column("cost ($)", justify="right")
    table.add_column("dur (s)", justify="right")
    table.add_column("files Δ", justify="right")
    table.add_column("rc", justify="right")
    table.add_column("summary")
    for r in rows:
        table.add_row(
            str(r.get("iteration", "?")),
            f"{r.get('cost_usd', 0):.4f}",
            f"{r.get('duration_s', 0):.1f}",
            str(r.get("files_changed", 0)),
            str(r.get("return_code", "?")),
            (r.get("summary") or "")[:80],
        )
    console.print(table)
    console.print(f"[bold]Iterations: {len(rows)}, total cost: ${total_cost:.4f}[/bold]")


async def _discover_tools(cmd: list[str]):
    client = McpStdioClient(cmd)
    await client.start()
    try:
        return await client.list_tools()
    finally:
        await client.stop()


def _gen_run_id(prefix: str = "run") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _print_result(result) -> None:
    color = {
        RunStatus.COMPLETE: "green",
        RunStatus.ITERATIONS_EXHAUSTED: "yellow",
        RunStatus.COST_EXHAUSTED: "yellow",
        RunStatus.NO_OP_STREAK: "yellow",
        RunStatus.ERROR_STREAK: "red",
        RunStatus.INTERRUPTED: "red",
        RunStatus.FAILED: "red",
    }.get(result.status, "white")
    console.print(f"[bold {color}]Status: {result.status.value}[/bold {color}]")
    console.print(f"  iterations:    {result.iterations}")
    console.print(f"  total cost:    ${result.total_cost_usd:.4f}")
    console.print(f"  branch:        {result.branch}")
    console.print(f"  worktree:      {result.worktree_path}")
    console.print(f"  output:        {result.output_dir}")
    console.print(f"  message:       {result.final_message}")


# Silence unused-import warning for type referenced via DEFAULT_ALLOWED_TOOLS.
_ = DEFAULT_ALLOWED_TOOLS

if __name__ == "__main__":
    app()
