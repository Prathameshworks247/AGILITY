"""FastAPI application for the graph-based LLM code review service."""

from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel, Field

from app.config import get_settings
from app.models import PullRequestRef, ReviewFinding

app = FastAPI(
    title="Graph-based LLM Code Review Service",
    version="0.1.0",
    description="AST-level semantic changes, repository graph traversal, and focused LLM context for impact-aware code review.",
)


# --- Request/response schemas for API ---


class PRWebhookPayload(BaseModel):
    """Payload for POST /webhooks/pr (provider-agnostic shape)."""

    repository_url: str = Field(..., description="Clone URL of the repository")
    base_ref: str = Field(..., description="Base ref or SHA")
    head_ref: str = Field(..., description="Head ref or SHA")
    pr_id: str | None = Field(None, description="Provider PR identifier")


class ReviewRequest(BaseModel):
    """Request body for POST /review (manual trigger)."""

    repository_url: str = Field(..., description="Clone URL of the repository")
    base_ref: str = Field(..., description="Base ref or SHA")
    head_ref: str = Field(..., description="Head ref or SHA")


class ReviewResponse(BaseModel):
    """Response from POST /review."""

    pr_ref: PullRequestRef
    summary: str = Field(..., description="PR-level review summary")
    findings: list[ReviewFinding] = Field(default_factory=list)
    status: str = Field("completed", description="completed | partial | failed")


# --- Endpoints ---


@app.get("/")
def root():
    return {"ok": True, "service": app.title, "version": app.version}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/webhooks/pr")
async def webhook_pr(payload: PRWebhookPayload):
    """
    Receive PR events from GitHub/GitLab/Bitbucket.
    Validates webhook (if secret configured), then enqueues or runs review.
    """
    settings = get_settings()
    if settings.webhook_secret:
        # In a full implementation we would validate X-Hub-Signature-256 etc.
        pass
    # For now, trigger review synchronously (same as POST /review)
    from app.models import RepositoryRef

    pr_ref = PullRequestRef(
        repository=RepositoryRef(url=payload.repository_url),
        base_ref=payload.base_ref,
        head_ref=payload.head_ref,
        pr_id=payload.pr_id,
    )
    # Delegate to review pipeline (stub until later todos)
    result = await run_review(pr_ref)
    return result


@app.post("/review", response_model=ReviewResponse)
async def review(request: ReviewRequest):
    """
    Manually trigger a review for the given base/head refs.
    Clones/checks out repo, computes semantic diff, builds graph, retrieves context, runs LLM.
    """
    from app.models import RepositoryRef

    pr_ref = PullRequestRef(
        repository=RepositoryRef(url=request.repository_url),
        base_ref=request.base_ref,
        head_ref=request.head_ref,
    )
    return await run_review(pr_ref)


async def run_review(pr_ref: PullRequestRef) -> ReviewResponse:
    """
    Run the full review pipeline (git, diff, AST, graph, retrieval, context, LLM, aggregate).
    Optionally post summary and findings to VCS (e.g. GitHub).
    """
    from app.services.pipeline import run_pipeline
    from app.vcs.github import GitHubAdapter
    from app.vcs.adapters import findings_to_inline_comments

    summary, findings, status = await run_pipeline(pr_ref)
    if pr_ref.pr_id and get_settings().github_token:
        try:
            import re
            adapter = GitHubAdapter()
            pr_id = pr_ref.pr_id
            if "#" not in pr_id and pr_ref.repository.url:
                m = re.search(r"github\.com[/:]([^/]+)/([^/]+)", pr_ref.repository.url.rstrip("/").replace(".git", ""))
                if m:
                    pr_id = f"{m.group(1)}/{m.group(2)}#{pr_id}"
            await adapter.post_review_comment(pr_id, summary)
            # Inline comments need commit_sha; use head_ref if it's a SHA
            head_sha = pr_ref.head_ref if len(pr_ref.head_ref) == 40 else None
            if head_sha:
                comments = findings_to_inline_comments(findings)
                if comments:
                    await adapter.post_inline_comments(pr_id, head_sha, comments)
                await adapter.post_status_check(
                    pr_ref.repository.url,
                    head_sha,
                    "success" if status == "completed" else "failure",
                    summary[:140] if summary else "Review completed",
                )
        except Exception:
            pass
    return ReviewResponse(pr_ref=pr_ref, summary=summary, findings=findings, status=status)
