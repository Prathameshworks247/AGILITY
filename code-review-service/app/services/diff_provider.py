"""
Abstraction layer for fetching repository content and computing diffs.
Allows plugging in different VCS backends (Git, GitHub API, GitLab, etc.).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Sequence

from app.models import FileChange, PullRequestRef


class DiffProvider(ABC):
    """Abstract interface for repo checkout and file-level diff."""

    @abstractmethod
    def ensure_repo(self, pr_ref: PullRequestRef) -> Path:
        """
        Clone or fetch the repository and return the path to the repo root.
        Caller can then checkout base/head in worktrees or use provider methods.
        """
        pass

    @abstractmethod
    def get_base_path(self, pr_ref: PullRequestRef) -> Path:
        """Return path to a worktree or directory containing the base revision."""
        pass

    @abstractmethod
    def get_head_path(self, pr_ref: PullRequestRef) -> Path:
        """Return path to a worktree or directory containing the head revision."""
        pass

    @abstractmethod
    def get_file_changes(self, pr_ref: PullRequestRef) -> Sequence[FileChange]:
        """
        Compute file-level diff between base and head.
        Returns list of changed/added/removed/renamed files with paths and change type.
        """
        pass
