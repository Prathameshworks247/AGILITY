"""FastAPI application for the graph-based LLM code review service."""

from __future__ import annotations

import logging
import sys

from fastapi import FastAPI

# Configure logging to stdout so it appears in uvicorn console
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("app")
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
    local_path: str | None = Field(None, description="If set, use this local repo path instead of cloning (for local testing)")
    review_mode: str = Field("batched", description="batched | per_unit | both")


class ReviewResponse(BaseModel):
    """Response from POST /review."""

    pr_ref: PullRequestRef
    summary: str = Field(..., description="PR-level review summary")
    findings: list[ReviewFinding] = Field(default_factory=list)
    status: str = Field("completed", description="completed | partial | failed")
    unit_reviews: list[dict] = Field(default_factory=list, description="Per-unit LLM outputs (when per_unit or both)")
    combined_review: str | None = Field(None, description="Concatenated per-unit review text")


class GraphRequest(BaseModel):
    """Request body for POST /graph (build and return repository graph)."""

    repository_url: str = Field(..., description="Clone URL of the repository")
    head_ref: str = Field(..., description="Ref to build graph from, e.g. main")
    local_path: str | None = Field(None, description="If set, use this local repo path instead of cloning")


class GraphResponse(BaseModel):
    """Response from POST /graph."""

    nodes: list[dict] = Field(default_factory=list, description="Graph nodes (id, kind, file_path, symbol_name, ...)")
    edges: list[dict] = Field(default_factory=list, description="Graph edges (src_id, dst_id, type)")
    stats: dict = Field(default_factory=dict, description="node_count, edge_count")


# --- Endpoints ---


@app.get("/")
def root():
    return {"ok": True, "service": app.title, "version": app.version}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/graph")
async def graph(request: GraphRequest, format: str = "json"):
    """
    Build the repository graph for the given head ref and return nodes + edges.
    Use ?format=html to open an in-browser visualization. Use ?format=dot for raw DOT.
    """
    from app.models import RepositoryRef
    from app.services.git_provider import GitDiffProvider
    from app.graph.python_builder import PythonGraphBuilder

    pr_ref = PullRequestRef(
        repository=RepositoryRef(url=request.repository_url, local_path=request.local_path),
        base_ref=request.head_ref,  # same as head for graph-only
        head_ref=request.head_ref,
    )
    diff_provider = GitDiffProvider(local_path=request.local_path)
    try:
        head_path = diff_provider.get_head_path(pr_ref)
    except Exception as e:
        logger.exception("Failed to checkout head: %s", e)
        raise
    builder = PythonGraphBuilder(head_path)
    store = builder.build()
    nodes = []
    for nid in store.all_node_ids():
        node = store.get_node(nid)
        if node:
            nodes.append({
                "id": node.id,
                "kind": node.kind.value,
                "file_path": node.file_path,
                "symbol_name": node.symbol_name,
                **(node.extra or {}),
            })
    edges = []
    g = store.to_networkx()
    for src, dst, data in g.edges(data=True):
        edges.append({"src_id": src, "dst_id": dst, "type": data.get("type", "")})

    if format == "dot":
        from fastapi.responses import PlainTextResponse
        dot = _graph_to_dot(nodes, edges)
        return PlainTextResponse(dot, media_type="text/vnd.graphviz")

    if format == "html":
        from fastapi.responses import HTMLResponse
        dot = _graph_to_dot(nodes, edges)
        html = _graph_html_page(dot)
        return HTMLResponse(html)

    return GraphResponse(
        nodes=nodes,
        edges=edges,
        stats={"node_count": len(nodes), "edge_count": len(edges)},
    )


def _graph_html_page(dot: str) -> str:
    """HTML page that renders the graph with Viz.js (DOT format)."""
    import json
    dot_json = json.dumps(dot)
    return f'''<!DOCTYPE html>
<html>
<head><title>Repository Graph</title>
<script src="https://cdn.jsdelivr.net/npm/viz.js@2.1.2/viz.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/viz.js@2.1.2/full.render.js"></script>
<style>body{{font-family:sans-serif;margin:1rem}}#graph{{overflow:auto}}</style>
</head>
<body>
<h1>Repository Graph</h1>
<div id="graph"></div>
<script id="dot-data" type="application/json">{dot_json}</script>
<script>
var dot = JSON.parse(document.getElementById("dot-data").textContent);
var viz = new Viz();
viz.renderSVGElement(dot)
  .then(function(el) {{ document.getElementById("graph").appendChild(el); }})
  .catch(function(e) {{ document.getElementById("graph").innerHTML = "<pre>Error: " + e + "</pre>"; }});
</script>
</body>
</html>'''


def _graph_to_dot(nodes: list[dict], edges: list[dict]) -> str:
    """Convert graph to GraphViz DOT format."""
    def esc(s: str) -> str:
        return (s or "").replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")

    lines = ["digraph G {", "  rankdir=LR;", "  node [shape=box, fontsize=10];"]
    for n in nodes:
        label = esc(n.get("symbol_name", n["id"]))
        kind = esc(n.get("kind", ""))
        nid = esc(n["id"])
        lines.append(f'  "{nid}" [label="{label}\\n({kind})"];')
    for e in edges:
        src, dst = esc(e["src_id"]), esc(e["dst_id"])
        t = esc(e.get("type", ""))
        lines.append(f'  "{src}" -> "{dst}" [label="{t}"];')
    lines.append("}")
    return "\n".join(lines)


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

    logger.info(
        "Review request: %s..%s (local_path=%s, mode=%s)",
        request.base_ref,
        request.head_ref,
        request.local_path or "clone",
        request.review_mode,
    )
    pr_ref = PullRequestRef(
        repository=RepositoryRef(
            url=request.repository_url,
            local_path=request.local_path,
        ),
        base_ref=request.base_ref,
        head_ref=request.head_ref,
    )
    try:
        return await run_review(pr_ref, review_mode=request.review_mode)
    except Exception as e:
        logger.exception("Review failed: %s", e)
        raise


async def run_review(pr_ref: PullRequestRef, review_mode: str = "batched") -> ReviewResponse:
    """
    Run the full review pipeline (git, diff, AST, graph, retrieval, context, LLM, aggregate).
    Optionally post summary and findings to VCS (e.g. GitHub).
    """
    from app.services.pipeline import run_pipeline
    from app.vcs.github import GitHubAdapter
    from app.vcs.adapters import findings_to_inline_comments

    summary, findings, status, unit_reviews, combined_review = await run_pipeline(pr_ref, review_mode=review_mode)
    logger.info("Pipeline completed: status=%s, findings=%d", status, len(findings))
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
    return ReviewResponse(
        pr_ref=pr_ref,
        summary=summary,
        findings=findings,
        status=status,
        unit_reviews=unit_reviews,
        combined_review=combined_review,
    )
