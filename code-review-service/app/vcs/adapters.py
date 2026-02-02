"""
Abstract interface for VCS providers and GitHub adapter: post review comments,
summary comment, and status check.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Sequence

from app.models import ReviewFinding


class VCSAdapter(ABC):
    """Abstract interface for posting review results to a VCS provider."""

    @abstractmethod
    async def post_review_comment(self, pr_id: str, body: str) -> str | None:
        """Post a single comment (e.g. PR summary). Returns comment ID or None."""
        pass

    @abstractmethod
    async def post_inline_comments(
        self,
        pr_id: str,
        commit_sha: str,
        comments: Sequence[tuple[str, int, str]],
    ) -> bool:
        """Post inline comments (file_path, line, body). Returns success."""
        pass

    @abstractmethod
    async def post_status_check(
        self,
        repo_url: str,
        commit_sha: str,
        status: str,
        description: str,
        target_url: str | None = None,
    ) -> bool:
        """Post status check (pending/success/failure). Returns success."""
        pass


def findings_to_inline_comments(findings: Sequence[ReviewFinding]) -> list[tuple[str, int, str]]:
    """Convert ReviewFinding list to (file_path, line, body) for inline comments."""
    out: list[tuple[str, int, str]] = []
    for f in findings:
        line = f.location_line_start or f.location_line_end or 1
        body = f"[{f.severity}] {f.message}"
        if f.suggested_fix:
            body += f"\n\n**Suggested fix:** {f.suggested_fix}"
        out.append((f.location_file, line, body))
    return out
