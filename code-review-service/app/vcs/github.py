"""
GitHub adapter: post PR review comment, inline comments, and status check
using GitHub API (REST). Requires GITHUB_TOKEN with repo scope.
"""

from __future__ import annotations

import re
from typing import Sequence

import httpx

from app.models import ReviewFinding
from app.vcs.adapters import VCSAdapter, findings_to_inline_comments


def _parse_github_repo(repo_url: str) -> tuple[str, str] | None:
    """Extract owner/repo from URL like https://github.com/owner/repo or git@github.com:owner/repo.git."""
    url = repo_url.rstrip("/").replace(".git", "")
    m = re.search(r"github\.com[/:]([^/]+)/([^/]+)", url)
    if m:
        return m.group(1), m.group(2)
    return None


class GitHubAdapter(VCSAdapter):
    """Post review results to GitHub via REST API."""

    def __init__(self, token: str | None = None) -> None:
        from app.config import get_settings
        import os
        settings = get_settings()
        self.token = token or settings.github_token or os.environ.get("GITHUB_TOKEN")
        self._headers = {"Accept": "application/vnd.github.v3+json", "Authorization": f"Bearer {self.token}"} if self.token else {}

    async def post_review_comment(self, pr_id: str, body: str) -> str | None:
        """Post PR comment. pr_id can be 'owner/repo#number' or we need repo_owner, repo_name, pr_number."""
        if not self.token:
            return None
        parts = pr_id.split("#")
        if len(parts) != 2:
            return None
        repo_slug, number = parts[0], parts[1]
        if "/" not in repo_slug:
            return None
        owner, repo = repo_slug.split("/", 1)
        url = f"https://api.github.com/repos/{owner}/{repo}/issues/{number}/comments"
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(url, json={"body": body}, headers=self._headers)
            if r.status_code >= 400:
                return None
            data = r.json()
            return str(data.get("id", ""))

    async def post_inline_comments(
        self,
        pr_id: str,
        commit_sha: str,
        comments: Sequence[tuple[str, int, str]],
    ) -> bool:
        """Post review with inline comments (create a review)."""
        if not self.token or not comments:
            return False
        parts = pr_id.split("#")
        if len(parts) != 2:
            return False
        owner, repo = parts[0].split("/", 1) if "/" in parts[0] else (None, None)
        if not owner or not repo:
            return False
        pr_number = parts[1]
        # Get PR to find head_sha if not provided
        async with httpx.AsyncClient(timeout=30.0) as client:
            pr_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"
            pr_r = await client.get(pr_url, headers=self._headers)
            if pr_r.status_code >= 400:
                return False
            head_sha = (pr_r.json().get("head", {}) or {}).get("sha") or commit_sha
        events = [{"path": path, "line": line, "body": body} for path, line, body in comments]
        payload = {"commit_id": head_sha, "body": "Graph-based code review", "event": "COMMENT", "comments": events}
        url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/reviews"
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(url, json=payload, headers=self._headers)
            return r.status_code < 400

    async def post_status_check(
        self,
        repo_url: str,
        commit_sha: str,
        status: str,
        description: str,
        target_url: str | None = None,
    ) -> bool:
        """Post status check (pending/success/failure)."""
        if not self.token:
            return False
        parsed = _parse_github_repo(repo_url)
        if not parsed:
            return False
        owner, repo = parsed
        url = f"https://api.github.com/repos/{owner}/{repo}/statuses/{commit_sha}"
        payload = {"state": status, "description": description[:140], "context": "graph-code-review"}
        if target_url:
            payload["target_url"] = target_url
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(url, json=payload, headers=self._headers)
            return r.status_code < 400
