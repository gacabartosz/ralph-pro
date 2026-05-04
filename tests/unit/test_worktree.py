"""Worktree — git worktree create/cleanup against a temp git repo."""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from ralph.worktree import (
    cleanup_worktree,
    commit_in_worktree,
    create_worktree,
    files_changed_since,
    head_sha,
)


@pytest.fixture
def temp_git_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "-C", str(repo), "init", "-b", "main"], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.email", "test@example.com"],
        check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.name", "Test"],
        check=True, capture_output=True,
    )
    (repo / "README.md").write_text("hello", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-m", "init", "--no-verify"],
        check=True, capture_output=True,
    )
    return repo


def test_create_worktree_makes_branch(temp_git_repo: Path, tmp_path: Path):
    wt = create_worktree(temp_git_repo, "ralph/test", tmp_path / "worktrees")
    assert wt.path.exists()
    assert (wt.path / "README.md").exists()
    branches = subprocess.run(
        ["git", "-C", str(temp_git_repo), "branch", "--list"],
        check=True, capture_output=True, text=True,
    )
    assert "ralph/test" in branches.stdout


def test_commit_in_worktree_returns_sha(temp_git_repo: Path, tmp_path: Path):
    wt = create_worktree(temp_git_repo, "ralph/test2", tmp_path / "worktrees")
    base = head_sha(wt)
    (wt.path / "new.txt").write_text("x", encoding="utf-8")
    sha = commit_in_worktree(wt, "ralph(iter 1): add file")
    assert sha is not None
    assert sha != base
    assert len(sha) == 40


def test_commit_returns_none_when_no_changes(temp_git_repo: Path, tmp_path: Path):
    wt = create_worktree(temp_git_repo, "ralph/test3", tmp_path / "worktrees")
    sha = commit_in_worktree(wt, "noop")
    assert sha is None


def test_files_changed_since_counts(temp_git_repo: Path, tmp_path: Path):
    wt = create_worktree(temp_git_repo, "ralph/test4", tmp_path / "worktrees")
    base = head_sha(wt)
    (wt.path / "a.txt").write_text("1", encoding="utf-8")
    (wt.path / "b.txt").write_text("2", encoding="utf-8")
    commit_in_worktree(wt, "two files")
    assert files_changed_since(wt, base) == 2


def test_cleanup_worktree_removes(temp_git_repo: Path, tmp_path: Path):
    wt = create_worktree(temp_git_repo, "ralph/test5", tmp_path / "worktrees")
    cleanup_worktree(wt)
    assert not wt.path.exists()
