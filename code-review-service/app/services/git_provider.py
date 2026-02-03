"""
Git-based DiffProvider: clone, worktrees, and file-level diff via git.
"""

from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Sequence

logger = logging.getLogger("app.git_provider")

from app.config import get_settings, get_extension_to_language
from app.models import FileChange, PullRequestRef
from app.services.diff_provider import DiffProvider


class GitDiffProvider(DiffProvider):
    """DiffProvider implementation using local git clone and worktrees."""

    def __init__(self, checkout_root: Path | None = None, local_path: str | Path | None = None):
        self.checkout_root = checkout_root or get_settings().repo_checkout_root
        self.checkout_root = Path(self.checkout_root)
        self.checkout_root.mkdir(parents=True, exist_ok=True)
        self._local_path = Path(local_path) if local_path else None
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

    def _extract_branch(self, ref: str) -> str | None:
        """Extract branch name from ref (e.g., 'main~5' -> 'main', 'origin/main~10' -> 'main').
        
        Returns None if the ref appears to be a commit SHA (not a branch name).
        """
        # Remove ~N, ^N, @{N} suffixes
        branch = re.split(r"[~^@]", ref)[0]
        # Strip origin/ prefix for fetch (we fetch branch name, not origin/branch)
        if branch.startswith("origin/"):
            branch = branch[7:]
        # If it looks like a commit SHA (7-40 hex chars), return None
        if re.fullmatch(r"[0-9a-fA-F]{7,40}", branch):
            return None
        return branch

    def ensure_repo(self, pr_ref: PullRequestRef) -> Path:
        # Use local path when provided (for local testing without cloning)
        local = getattr(pr_ref.repository, "local_path", None) or self._local_path
        if local:
            p = Path(local).resolve()
            if p.exists() and (p / ".git").exists():
                logger.info("Using local repo: %s", p)
                return p

        url = pr_ref.repository.url
        slug = self._repo_slug(url)
        repo_path = self.checkout_root / slug

        # Check if any ref is a commit SHA (needs full history)
        refs = [pr_ref.base_ref, pr_ref.head_ref]
        has_commit_sha = any(self._extract_branch(ref) is None for ref in refs)
        
        if not repo_path.exists():
            logger.info("Cloning %s -> %s", url, repo_path)
            if has_commit_sha:
                # Clone full history for commit SHA refs
                subprocess.run(
                    ["git", "clone", url, str(repo_path)],
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=300,
                )
            else:
                # Clone with enough depth for relative refs like main~5
                subprocess.run(
                    ["git", "clone", "--depth", "100", url, str(repo_path)],
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
        else:
            if has_commit_sha:
                # Unshallow if we have commit SHAs
                subprocess.run(
                    ["git", "fetch", "--unshallow"],
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
            # Fetch the branches (not commit SHAs)
            branches_to_fetch = set()
            for ref in refs:
                branch = self._extract_branch(ref)
                if branch:
                    branches_to_fetch.add(branch)
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
        # Skip fetch when using local repo (not under checkout_root)
        if str(repo_path.resolve()).startswith(str(self.checkout_root.resolve())):
            branch = self._extract_branch(ref)
            if branch:
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
            # Log stderr for debugging; caller may surface it
            raise RuntimeError(
                f"git diff failed: {out.stderr or 'unknown error'}"
            )
        # -z gives NUL-separated: STATUS\0PATH\0 (per git diff docs)
        buf = out.stdout
        i = 0
        while i < len(buf):
            status_end = buf.find("\0", i)
            if status_end == -1:
                break
            status = buf[i:status_end].strip()
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
