"""
Full review pipeline: diff -> AST diff -> graph -> retrieval -> context -> LLM -> aggregate.
"""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

from app.models import FileChange, PullRequestRef, ReviewFinding, ReviewUnit, SymbolChange, SymbolKind
from app.services.diff_provider import DiffProvider
from app.services.git_provider import GitDiffProvider
from app.services.ast_diff_service import run_ast_diff
from app.graph.python_builder import PythonGraphBuilder
from app.graph.store import GraphStore
from app.graph.retrieval import RelevantContextFinder, RetrievalConfig
from app.context.assembler import ContextAssembler
from app.context.prompts import change_summary_bullets_for_unit, format_review_unit_for_prompt
from app.llm.client import LLMClient, get_llm_client
from app.llm.orchestrator import ReviewOrchestrator


def _symbol_change_to_node_id(store: GraphStore, change: SymbolChange) -> str:
    """Map SymbolChange to graph node ID. For methods, graph uses ClassName.method_name."""
    candidate = f"{change.file_path}::{change.symbol_name}"
    if store.get_node(candidate):
        return candidate
    if change.kind == SymbolKind.METHOD:
        for nid in store.all_node_ids():
            node = store.get_node(nid)
            if node and node.file_path == change.file_path and node.symbol_name.endswith("." + change.symbol_name):
                return nid
    return candidate


def _load_before_after(
    base_path: Path,
    head_path: Path,
    file_path: str,
    line_start: int | None,
    line_end: int | None,
    max_lines: int = 40,
) -> tuple[str | None, str | None]:
    def read_slice(root: Path) -> str:
        full = root / file_path
        if not full.exists():
            return ""
        try:
            lines = full.read_text(encoding="utf-8", errors="replace").splitlines()
        except Exception:
            return ""
        if not line_start or line_start < 1:
            return ""
        end = line_end or line_start
        slice_lines = lines[line_start - 1 : end]
        if len(slice_lines) > max_lines:
            slice_lines = slice_lines[: max_lines // 2] + ["..."] + slice_lines[-(max_lines - max_lines // 2 - 1) :]
        return "\n".join(slice_lines)
    return read_slice(base_path), read_slice(head_path)


async def run_pipeline(
    pr_ref: PullRequestRef,
    diff_provider: DiffProvider | None = None,
    llm_client: LLMClient | None = None,
) -> tuple[str, list[ReviewFinding], str]:
    """
    Run the full pipeline. Returns (summary, findings, status).
    """
    diff_provider = diff_provider or GitDiffProvider()
    try:
        file_changes = list(diff_provider.get_file_changes(pr_ref))
    except Exception as e:
        return f"Failed to get file changes: {e}", [], "failed"
    if not file_changes:
        return "No file changes between base and head.", [], "completed"
    try:
        base_path = diff_provider.get_base_path(pr_ref)
        head_path = diff_provider.get_head_path(pr_ref)
    except Exception as e:
        return f"Failed to checkout base/head: {e}", [], "failed"
    symbol_changes = run_ast_diff(file_changes, base_path, head_path)
    if not symbol_changes:
        return f"Detected {len(file_changes)} file(s) changed; no Python symbol-level changes.", [], "completed"
    builder = PythonGraphBuilder(head_path)
    store = builder.build()
    finder = RelevantContextFinder(store, RetrievalConfig())
    assembler = ContextAssembler(head_path)
    units: list[ReviewUnit] = []
    for sc in symbol_changes:
        node_id = _symbol_change_to_node_id(store, sc)
        context_ids = finder.find([node_id])
        before, after = _load_before_after(
            base_path, head_path,
            sc.file_path, sc.line_start, sc.line_end,
        )
        unit = assembler.assemble(store, sc, context_ids, before_snippet=before, after_snippet=after)
        units.append(unit)
    llm = llm_client or get_llm_client()
    orchestrator = ReviewOrchestrator(llm_client=llm, store=store, assembler=assembler)
    summary, findings = await orchestrator.run(units, repo_context="")
    return summary, findings, "completed"
