"""
Full review pipeline: diff -> AST diff -> graph -> (per-unit and/or batched) LLM review.

Architecture
============

  1. Diff & checkout
     GitDiffProvider: clone or use local_path, checkout base_ref and head_ref worktrees.
     get_file_changes(base, head) -> list[FileChange] (path, change_type, language).

  2. AST diff (Python only)
     run_ast_diff(file_changes, base_path, head_path) -> list[SymbolChange].
     For each changed .py file: parse base/head, extract symbols (class, function, method, constant),
     semantic diff -> added/removed/modified symbols with line ranges.

  3. Repository graph (head only)
     PythonGraphBuilder(head_path).build() -> GraphStore.
     Nodes: MODULE (per file), CLASS, FUNCTION, METHOD, CONSTANT (per symbol).
     Edges:
       - symbol -> module (IMPORTS: “belongs to”)
       - module -> module (IMPORTS: “A imports B”)
       - function/method -> callee (CALLS, same-file only today)
       - class -> base_class (INHERITS, same-file only)
       - test_module -> target_module (TESTS: test file imports code under test)

  4a. Per-unit path (review_mode in {per_unit, both})
      For each symbol change:
        - Map to graph node; RelevantContextFinder.find([node_id]) does BFS from that node
          (CALLS, IMPORTS, TESTS, INHERITS) with depth limits and scoring -> context_node_ids.
        - ContextAssembler: load before/after snippet for changed symbol + code snippets for
          context_node_ids from head_path; prune by token budget -> ReviewUnit.
      ReviewOrchestrator.run_per_unit(units): one LLM call per unit with that unit’s
      change summary + relevant surrounding code (graph-informed context). Concatenate
      outputs for combined_review.

  4b. Batched path (review_mode in {batched, both})
      Build one prompt: scope (changed files), symbol summary, import graph text
      (_build_import_graph: module->module IMPORTS for changed files), and condensed
      code diffs. Single LLM call -> structured review (header, checklist, comments, summary).

  5. Output
     summary, findings (parsed from LLM), unit_reviews (per-unit only), combined_review (per-unit concatenated).

Graph usage
===========
  - Per-unit: Graph is used fully. BFS from changed symbol pulls in callers, callees,
    import-related modules, tests, and base classes; that context is sent to the LLM.
  - Batched: Only module-level IMPORTS are used (import graph text). CALLS, INHERITS, TESTS
    are not included in the batched prompt (could add a short “call graph” or “tests” summary).
  - Limitation: CALLS and INHERITS are same-file only (no cross-file resolution in the builder).
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Sequence

logger = logging.getLogger("app.pipeline")

from app.models import PullRequestRef, ReviewFinding, ReviewUnit, SymbolChange, SymbolKind
from app.services.diff_provider import DiffProvider
from app.services.git_provider import GitDiffProvider
from app.services.ast_diff_service import run_ast_diff
from app.graph.python_builder import PythonGraphBuilder
from app.graph.store import GraphStore
from app.graph.retrieval import RelevantContextFinder, RetrievalConfig
from app.context.assembler import ContextAssembler
from app.models import EdgeType
from app.context.prompts import build_batched_prompt, SYSTEM_PROMPT
from app.llm.client import LLMClient, get_llm_client
from app.llm.orchestrator import ReviewOrchestrator, _parse_findings_from_response


def _module_id(file_path: str) -> str:
    return file_path.replace("/", ".").replace("\\", ".").replace(".py", "")


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


def _build_import_graph(store: GraphStore, changed_files: set[str]) -> str:
    """Build a concise summary of import relationships for changed modules."""
    lines = []
    seen = set()
    for fid in store.all_node_ids():
        node = store.get_node(fid)
        if not node or node.kind != SymbolKind.MODULE:
            continue
        fp = node.file_path
        if fp not in changed_files:
            continue
        mod_id = node.id
        # Outgoing imports (this file imports X)
        for _, dst, data in store.to_networkx().out_edges(mod_id, data=True):
            if data.get("type") == EdgeType.IMPORTS.value:
                dst_node = store.get_node(dst)
                if dst_node and dst_node.kind == SymbolKind.MODULE:
                    key = (fp, dst_node.file_path)
                    if key not in seen:
                        seen.add(key)
                        lines.append(f"- {fp} imports {dst_node.file_path}")
        # Incoming (X imports this file)
        for src, _, data in store.to_networkx().in_edges(mod_id, data=True):
            if data.get("type") == EdgeType.IMPORTS.value:
                src_node = store.get_node(src)
                if src_node and src_node.kind == SymbolKind.MODULE:
                    key = (src_node.file_path, fp)
                    if key not in seen:
                        seen.add(key)
                        lines.append(f"- {src_node.file_path} imports {fp}")
    return "\n".join(lines[:30]) if lines else "(no cross-file import edges in graph)"


def _build_code_diffs(
    base_path: Path,
    head_path: Path,
    symbol_changes: list[SymbolChange],
    max_lines_total: int = 200,
) -> str:
    """Build condensed diffs for changed symbols, grouped by file."""
    from collections import defaultdict
    by_file: dict[str, list[tuple[str | None, str | None, str]]] = defaultdict(list)
    for sc in symbol_changes:
        if sc.change_type.value == "removed":
            try:
                full = base_path / sc.file_path
                if full.exists():
                    lines = full.read_text(encoding="utf-8", errors="replace").splitlines()
                    start = (sc.line_start or 1) - 1
                    end = min(sc.line_end or start + 1, len(lines))
                    snip = "\n".join(lines[start:end][:25])
                    by_file[sc.file_path].append((snip, None, f"{sc.symbol_name} ({sc.kind.value}) REMOVED"))
            except Exception:
                pass
            continue
        try:
            head_file = head_path / sc.file_path
            if not head_file.exists():
                continue
            lines = head_file.read_text(encoding="utf-8", errors="replace").splitlines()
            start = (sc.line_start or 1) - 1
            end = min(sc.line_end or start + 1, len(lines))
            snip = "\n".join(lines[start:end][:25])
            label = f"{sc.symbol_name} ({sc.kind.value}) {sc.change_type.value}"
            by_file[sc.file_path].append((None, snip, label))
        except Exception:
            pass
    out = []
    total = 0
    for fp in sorted(by_file.keys()):
        if total >= max_lines_total:
            break
        out.append(f"\n### {fp}\n")
        for before, after, label in by_file[fp][:5]:  # max 5 symbols per file
            if total >= max_lines_total:
                break
            out.append(f"--- {label}\n")
            if before:
                out.append("BEFORE:\n```\n" + before + "\n```\n")
                total += before.count("\n") + 1
            if after:
                out.append("AFTER:\n```\n" + after + "\n```\n")
                total += after.count("\n") + 1
    return "\n".join(out) if out else "(no code shown)"


def _dedupe_and_limit_symbols(symbol_changes: list[SymbolChange], max_per_file: int = 5) -> list[SymbolChange]:
    """Keep most important symbols per file, limit total."""
    from collections import defaultdict
    by_file: dict[str, list[SymbolChange]] = defaultdict(list)
    for sc in symbol_changes:
        by_file[sc.file_path].append(sc)
    result = []
    for fp in sorted(by_file.keys()):
        items = by_file[fp]
        # Prefer ADDED, MODIFIED over REMOVED; prefer classes/functions over methods/constants
        kind_order = {SymbolKind.CLASS: 0, SymbolKind.FUNCTION: 1, SymbolKind.METHOD: 2, SymbolKind.CONSTANT: 3}
        items.sort(key=lambda x: (x.change_type.value != "added", kind_order.get(x.kind, 2), x.symbol_name))
        result.extend(items[:max_per_file])
    return result[:40]  # hard cap total


async def run_pipeline(
    pr_ref: PullRequestRef,
    diff_provider: DiffProvider | None = None,
    llm_client: LLMClient | None = None,
    review_mode: str = "batched",
) -> tuple[str, list[ReviewFinding], str, list[dict], str | None]:
    """
    Run the full pipeline. Returns (summary, findings, status).
    review_mode: "batched" | "per_unit" | "both"
    """
    t0 = time.monotonic()
    local_path = getattr(pr_ref.repository, "local_path", None)
    diff_provider = diff_provider or GitDiffProvider(local_path=local_path)
    try:
        file_changes = list(diff_provider.get_file_changes(pr_ref))
        logger.info("Got %d file changes (%.1fs)", len(file_changes), time.monotonic() - t0)
    except Exception as e:
        logger.exception("Failed to get file changes")
        return f"Failed to get file changes: {e}", [], "failed"
    if not file_changes:
        return "No file changes between base and head.", [], "completed"
    t1 = time.monotonic()
    try:
        base_path = diff_provider.get_base_path(pr_ref)
        head_path = diff_provider.get_head_path(pr_ref)
        logger.info("Checkout base/head done (%.1fs)", time.monotonic() - t1)
    except Exception as e:
        logger.exception("Failed to checkout base/head")
        return f"Failed to checkout base/head: {e}", [], "failed"
    t2 = time.monotonic()
    symbol_changes = run_ast_diff(file_changes, base_path, head_path)
    logger.info("AST diff: %d symbol changes (%.1fs)", len(symbol_changes), time.monotonic() - t2)
    if not symbol_changes:
        return f"Detected {len(file_changes)} file(s) changed; no Python symbol-level changes.", [], "completed"

    symbol_changes = _dedupe_and_limit_symbols(symbol_changes)
    logger.info("Limited to %d symbol changes for review", len(symbol_changes))

    t3 = time.monotonic()
    builder = PythonGraphBuilder(head_path)
    store = builder.build()
    logger.info("Graph built: %d nodes (%.1fs)", len(list(store.all_node_ids())), time.monotonic() - t3)

    changed_files = {fc.path for fc in file_changes if getattr(fc, "language", None) == "python"}
    changed_files.update(sc.file_path for sc in symbol_changes)

    llm = llm_client or get_llm_client()
    mode = (review_mode or "batched").lower()
    if mode not in {"batched", "per_unit", "both"}:
        mode = "batched"

    findings: list[ReviewFinding] = []
    unit_reviews: list[dict] = []
    combined_review: str | None = None
    summary: str = ""

    if mode in {"per_unit", "both"}:
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
        orchestrator = ReviewOrchestrator(llm_client=llm, store=store, assembler=assembler)
        unit_reviews, unit_findings = await orchestrator.run_per_unit(units, repo_context="")
        combined_review = "\n\n---\n\n".join(u.get("review", "") for u in unit_reviews if u.get("review")) or ""
        findings.extend(unit_findings)

    if mode in {"batched", "both"}:
        scope_files = sorted(changed_files)
        symbol_summary = [
            f"{sc.file_path} :: {sc.symbol_name} ({sc.kind.value}): {sc.change_type.value}"
            for sc in symbol_changes
        ]
        import_graph = _build_import_graph(store, changed_files)
        code_diffs = _build_code_diffs(base_path, head_path, symbol_changes)
        user_prompt = build_batched_prompt(scope_files, symbol_summary, import_graph, code_diffs)
        logger.info("Starting batched LLM review (1 call)")
        try:
            summary = await llm.complete(SYSTEM_PROMPT, user_prompt)
        except Exception as e:
            logger.exception("LLM review failed: %s", e)
            return f"LLM review failed: {e}", [], "failed", unit_reviews, combined_review
        findings.extend(_parse_findings_from_response(summary, default_file="", default_symbol=""))

    if mode == "per_unit":
        summary = combined_review or "No review output."

    logger.info("Pipeline complete (total %.1fs)", time.monotonic() - t0)
    return summary, findings, "completed", unit_reviews, combined_review
