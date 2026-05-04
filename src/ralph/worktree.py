"""Git worktree management — isolates each Ralph run from the host repo."""
from __future__ import annotations

import logging
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger(__name__)


class WorktreeError(RuntimeError):
    pass


@dataclass(slots=True)
class Worktree:
    """One git worktree dedicated to a Ralph run."""

    path: Path
    branch: str
    base_repo: Path


def create_worktree(base_repo: Path, branch: str, worktree_root: Path) -> Worktree:
    """Create a new worktree at <worktree_root>/<branch_safe>/ on a fresh branch.

    The branch is created from HEAD of the base repo. If a worktree already exists
    at the target path, raise — we never overwrite.
    """
    if not (base_repo / ".git").exists():
        raise WorktreeError(f"{base_repo} is not a git repository (no .git)")

    branch_safe = branch.replace("/", "_").replace(" ", "_")
    target = worktree_root / branch_safe

    if target.exists():
        raise WorktreeError(f"worktree path already exists: {target}")

    worktree_root.mkdir(parents=True, exist_ok=True)

    # Use -b to create the branch fresh; if branch exists already, fall back.
    cmd = ["git", "-C", str(base_repo), "worktree", "add", "-b", branch, str(target)]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        if "already exists" in (e.stderr or ""):
            cmd_existing = ["git", "-C", str(base_repo), "worktree", "add", str(target), branch]
            subprocess.run(cmd_existing, check=True, capture_output=True, text=True)
        else:
            raise WorktreeError(f"git worktree add failed: {e.stderr}") from e

    log.info("created worktree at %s on branch %s", target, branch)
    return Worktree(path=target, branch=branch, base_repo=base_repo)


def cleanup_worktree(wt: Worktree, *, force: bool = False) -> None:
    """Remove the worktree from git and delete its directory.

    Use `force=True` to discard uncommitted changes.
    """
    cmd = ["git", "-C", str(wt.base_repo), "worktree", "remove", str(wt.path)]
    if force:
        cmd.append("--force")
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        log.warning("git worktree remove failed (%s); deleting dir manually", e.stderr.strip())
        if wt.path.exists():
            shutil.rmtree(wt.path, ignore_errors=True)
        # Best-effort prune.
        subprocess.run(
            ["git", "-C", str(wt.base_repo), "worktree", "prune"],
            check=False,
            capture_output=True,
        )


def commit_in_worktree(wt: Worktree, message: str) -> str | None:
    """git add -A && git commit -m <message>. Returns commit SHA or None if nothing to commit."""
    add = subprocess.run(
        ["git", "-C", str(wt.path), "add", "-A"],
        check=True, capture_output=True, text=True,
    )
    del add  # silence linter
    status = subprocess.run(
        ["git", "-C", str(wt.path), "status", "--porcelain"],
        check=True, capture_output=True, text=True,
    )
    if not status.stdout.strip():
        return None  # nothing staged

    subprocess.run(
        ["git", "-C", str(wt.path), "commit", "-m", message, "--no-verify"],
        check=True, capture_output=True, text=True,
    )
    sha = subprocess.run(
        ["git", "-C", str(wt.path), "rev-parse", "HEAD"],
        check=True, capture_output=True, text=True,
    )
    return sha.stdout.strip()


def files_changed_since(wt: Worktree, base_sha: str) -> int:
    """Count files changed in worktree relative to a given commit SHA."""
    res = subprocess.run(
        ["git", "-C", str(wt.path), "diff", "--name-only", base_sha],
        check=True, capture_output=True, text=True,
    )
    lines = [line for line in res.stdout.splitlines() if line.strip()]
    return len(lines)


def head_sha(wt: Worktree) -> str:
    res = subprocess.run(
        ["git", "-C", str(wt.path), "rev-parse", "HEAD"],
        check=True, capture_output=True, text=True,
    )
    return res.stdout.strip()
