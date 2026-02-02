"""
Git-based DiffProvider: clone, worktrees, and file-level diff via git.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Sequence

from app.config import get_settings, get_extension_to_language
from app.models import FileChange, PullRequestRef
from app.services.diff_provider import DiffProvider


class GitDiffProvider(DiffProvider):
    """DiffProvider implementation using local git clone and worktrees."""

    def __init__(self, checkout_root: Path | None = None):
        self.checkout_root = checkout_root or get_settings().repo_checkout_root
        self.checkout_root = Path(self.checkout_root)
        self.checkout_root.mkdir(parents=True, exist_ok=True)
        self._ext_to_lang = get_extension_to_language()

    def _repo_slug(self, url: str) -> str:
        """Derive a directory name from repo URL (e.g. owner_repo)."""
        url = url.rstrip("/")
        if url.endswith(".git"):
            url = url[:-4]
        parts = url.replace(":", "/").split("/")
        if len(parts) >= 2:
            return "_".join(parts[-2:])
        return re.sub(r"[^\w\-]", "_", parts[-1] if parts else "repo")

    def _extract_branch(self, ref: str) -> str:
        """Extract branch name from ref (e.g., 'main~5' -> 'main', 'feature' -> 'feature')."""
        # Remove ~N, ^N, @{N} suffixes
        branch = re.split(r"[~^@]", ref)[0]
        return branch

    def ensure_repo(self, pr_ref: PullRequestRef) -> Path:
        url = pr_ref.repository.url
        slug = self._repo_slug(url)
        repo_path = self.checkout_root / slug
        if not repo_path.exists():
            # Clone with enough depth for relative refs like main~5
            subprocess.run(
                ["git", "clone", "--depth", "100", url, str(repo_path)],
                check=True,
                capture_output=True,
                text=True,
                timeout=120,
            )
        else:
            # Fetch the branches (not relative refs like main~5)
            branches_to_fetch = set()
            for ref in [pr_ref.base_ref, pr_ref.head_ref]:
                branches_to_fetch.add(self._extract_branch(ref))
            for branch in branches_to_fetch:
                subprocess.run(
                    ["git", "fetch", "--depth", "100", "origin", branch],
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
        return repo_path

    def get_base_path(self, pr_ref: PullRequestRef) -> Path:
        repo_path = self.ensure_repo(pr_ref)
        worktree_base = self.checkout_root / f"{self._repo_slug(pr_ref.repository.url)}_base"
        self._ensure_worktree(repo_path, worktree_base, pr_ref.base_ref)
        return worktree_base

    def get_head_path(self, pr_ref: PullRequestRef) -> Path:
        repo_path = self.ensure_repo(pr_ref)
        worktree_head = self.checkout_root / f"{self._repo_slug(pr_ref.repository.url)}_head"
        self._ensure_worktree(repo_path, worktree_head, pr_ref.head_ref)
        return worktree_head

    def _ensure_worktree(self, repo_path: Path, worktree_path: Path, ref: str) -> None:
        # Fetch the branch (not relative refs)
        branch = self._extract_branch(ref)
        subprocess.run(
            ["git", "fetch", "--depth", "100", "origin", branch],
            cwd=repo_path,
            capture_output=True,
            text=True,
        )
        if worktree_path.exists():
            # Update existing worktree
            subprocess.run(
                ["git", "checkout", "--force", ref],
                cwd=worktree_path,
                capture_output=True,
                text=True,
            )
            return
        # Create new worktree - first remove any stale worktree entry
        subprocess.run(
            ["git", "worktree", "prune"],
            cwd=repo_path,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            ["git", "worktree", "add", "--detach", str(worktree_path), ref],
            cwd=repo_path,
            check=True,
            capture_output=True,
            text=True,
        )

    def get_file_changes(self, pr_ref: PullRequestRef) -> Sequence[FileChange]:
        repo_path = self.ensure_repo(pr_ref)
        result: list[FileChange] = []
        out = subprocess.run(
            [
                "git",
                "diff",
                "--name-status",
                "-z",
                pr_ref.base_ref,
                pr_ref.head_ref,
            ],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if out.returncode != 0:
            return result
        # -z gives NUL-separated: STATUS\tPATH [\tPATH]
        buf = out.stdout
        i = 0
        while i < len(buf):
            status_end = buf.find("\t", i)
            if status_end == -1:
                break
            status = buf[i:status_end]
            i = status_end + 1
            path_end = buf.find("\0", i)
            if path_end == -1:
                path_end = len(buf)
            path1 = buf[i:path_end].strip()
            i = path_end + 1
            if status in ("A", "M", "D", "R", "C") and path1:
                change_type = {"A": "added", "M": "modified", "D": "removed", "R": "renamed", "C": "copied"}.get(
                    status, "modified"
                )
                old_path = None
                if status in ("R", "C") and i < len(buf):
                    next_nul = buf.find("\0", i)
                    if next_nul != -1:
                        old_path = buf[i:next_nul].strip()
                        i = next_nul + 1
                lang = self._ext_to_lang.get(Path(path1).suffix.lstrip("."))
                result.append(
                    FileChange(
                        path=path1,
                        change_type=change_type,
                        language=lang,
                        old_path=old_path or None,
                    )
                )
        return result
