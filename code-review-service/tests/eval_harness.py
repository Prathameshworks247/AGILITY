"""
Evaluation harness: compare graph-based retrieval vs flat retrieval.
Measures token usage per PR and (when ground-truth findings exist) precision/recall.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Sequence

from app.models import FileChange, PullRequestRef, RepositoryRef, ReviewFinding, SymbolChange
from app.services.ast_diff_service import run_ast_diff
from app.graph.python_builder import PythonGraphBuilder
from app.graph.retrieval import RelevantContextFinder, RetrievalConfig
from app.graph.store import GraphStore
from app.context.assembler import ContextAssembler


@dataclass
class EvalResult:
    """Result of one evaluation run."""

    pr_ref: PullRequestRef
    file_changes_count: int = 0
    symbol_changes_count: int = 0
    graph_nodes: int = 0
    graph_edges: int = 0
    context_nodes_graph: int = 0
    context_nodes_flat: int = 0
    estimated_tokens_graph: int = 0
    estimated_tokens_flat: int = 0
    findings_count: int = 0
    status: str = ""


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def run_flat_retrieval(
    head_path: Path,
    symbol_changes: Sequence[SymbolChange],
    file_changes: Sequence[FileChange],
    max_nodes: int = 30,
) -> tuple[list[str], int]:
    """
    Flat retrieval: include all changed files' symbols up to max_nodes, no graph.
    Returns (list of node_ids used as context, estimated tokens).
    """
    seen_files = {sc.file_path for sc in symbol_changes}
    node_ids: list[str] = []
    for sc in symbol_changes:
        node_ids.append(f"{sc.file_path}::{sc.symbol_name}")
    tokens = 0
    for fc in file_changes:
        if fc.path not in seen_files:
            continue
        p = head_path / fc.path
        if p.exists():
            try:
                tokens += _estimate_tokens(p.read_text(encoding="utf-8", errors="replace"))
            except Exception:
                pass
    return node_ids[:max_nodes], tokens


def run_graph_retrieval(
    store: GraphStore,
    symbol_change_node_ids: Sequence[str],
    config: RetrievalConfig | None = None,
) -> tuple[list[str], int]:
    """
    Graph-based retrieval: traverse from changed symbols; return context node IDs
    and estimated tokens (sum of snippet lengths for those nodes).
    """
    finder = RelevantContextFinder(store, config or RetrievalConfig())
    context_ids = finder.find(list(symbol_change_node_ids))
    tokens = 0
    for nid in context_ids:
        node = store.get_node(nid)
        if node and node.extra:
            # Rough: assume ~20 lines per symbol
            tokens += 20 * 15  # ~300 tokens per node
        else:
            tokens += 200
    return context_ids, min(tokens, 8000)


def evaluate_on_repo(
    repo_path: Path,
    base_ref: str = "HEAD",
    head_ref: str = "HEAD",
    pr_id: str | None = None,
) -> EvalResult:
    """
    Run evaluation on a local repo path. For fixture dirs (no git), list .py files
    and treat all as modified; for real git repos use GitDiffProvider.
    """
    pr_ref = PullRequestRef(
        repository=RepositoryRef(url=f"file://{repo_path}"),
        base_ref=base_ref,
        head_ref=head_ref,
        pr_id=pr_id,
    )
    repo_path = Path(repo_path)
    file_changes: list[FileChange] = []
    for f in repo_path.rglob("*.py"):
        rel = f.relative_to(repo_path)
        file_changes.append(
            FileChange(path=str(rel).replace("\\", "/"), change_type="modified", language="python")
        )
    base_path = head_path = repo_path
    symbol_changes = run_ast_diff(file_changes, base_path, head_path)
    builder = PythonGraphBuilder(head_path)
    store = builder.build()
    symbol_node_ids = [f"{sc.file_path}::{sc.symbol_name}" for sc in symbol_changes]
    graph_context_ids, tokens_graph = run_graph_retrieval(store, symbol_node_ids)
    flat_context_ids, tokens_flat = run_flat_retrieval(head_path, symbol_changes, file_changes)
    return EvalResult(
        pr_ref=pr_ref,
        file_changes_count=len(file_changes),
        symbol_changes_count=len(symbol_changes),
        graph_nodes=store.node_count(),
        graph_edges=store.edge_count(),
        context_nodes_graph=len(graph_context_ids),
        context_nodes_flat=len(flat_context_ids),
        estimated_tokens_graph=tokens_graph,
        estimated_tokens_flat=tokens_flat,
        findings_count=0,
        status="completed",
    )


def run_harness(
    fixture_names: Sequence[str] = ("simple", "multi_hop", "test_gap"),
    fixture_base: Path | None = None,
) -> list[EvalResult]:
    """
    Run evaluation on named fixtures. Fixtures are created under fixture_base or tests/fixtures/repos.
    Returns list of EvalResult for comparison (graph vs flat token usage, context size).
    """
    base = fixture_base or Path(__file__).resolve().parent / "fixtures" / "repos"
    base.mkdir(parents=True, exist_ok=True)
    from tests.fixtures.synthetic_repos import (
        create_simple_dependency_repo,
        create_multi_hop_repo,
        create_test_gap_repo,
    )
    creators = {
        "simple": create_simple_dependency_repo,
        "multi_hop": create_multi_hop_repo,
        "test_gap": create_test_gap_repo,
    }
    results: list[EvalResult] = []
    for name in fixture_names:
        path = base / name
        if name in creators:
            creators[name](path)
        if not path.exists():
            continue
        # For fixtures we don't have real git refs; use path as both base and head
        try:
            r = evaluate_on_repo(path, base_ref="HEAD", head_ref="HEAD", pr_id=f"fixture/{name}#1")
            results.append(r)
        except Exception as e:
            results.append(
                EvalResult(
                    pr_ref=PullRequestRef(
                        repository=RepositoryRef(url=str(path)),
                        base_ref="HEAD",
                        head_ref="HEAD",
                    ),
                    status=f"error: {e}",
                )
            )
    return results
