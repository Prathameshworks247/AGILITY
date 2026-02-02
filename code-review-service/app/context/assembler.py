"""
Context assembler: for each review unit, load code for changed symbol and
graph neighbors, produce summarized context (snippets, docstrings), and
estimate token usage with optional pruning.
"""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

from app.models import GraphNode, ReviewUnit, SymbolChange
from app.graph.store import GraphStore


def _estimate_tokens(text: str) -> int:
    """Rough token estimate (~4 chars per token for English/code)."""
    return max(1, len(text) // 4)


def _read_snippet(path: Path, file_path: str, line_start: int | None, line_end: int | None, max_lines: int = 50) -> str:
    """Read a slice of file by line range; cap at max_lines."""
    full = path / file_path
    if not full.exists():
        return ""
    try:
        lines = full.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        return ""
    if not line_start or line_start < 1:
        line_start = 1
    if not line_end or line_end > len(lines):
        line_end = len(lines)
    slice_lines = lines[line_start - 1 : line_end]
    if len(slice_lines) > max_lines:
        slice_lines = slice_lines[: max_lines // 2] + ["..."] + slice_lines[-(max_lines - max_lines // 2 - 1) :]
    return "\n".join(slice_lines)


class ContextAssembler:
    """
    For each review unit (changed symbol + context node IDs), load code from
    head_path, produce snippets and a structured summary, and optionally
    prune to stay within token budget.
    """

    def __init__(self, head_path: Path, max_tokens_per_unit: int = 8000) -> None:
        self.head_path = Path(head_path)
        self.max_tokens_per_unit = max_tokens_per_unit

    def assemble(
        self,
        store: GraphStore,
        symbol_change: SymbolChange,
        context_node_ids: Sequence[str],
        before_snippet: str | None = None,
        after_snippet: str | None = None,
    ) -> ReviewUnit:
        """
        Build a ReviewUnit: changed symbol + context node IDs + before/after
        snippets. Optionally prune context_node_ids to stay under token budget.
        """
        used = 0
        if before_snippet:
            used += _estimate_tokens(before_snippet)
        if after_snippet:
            used += _estimate_tokens(after_snippet)
        included: list[str] = []
        for nid in context_node_ids:
            node = store.get_node(nid)
            if not node:
                continue
            snippet = _read_snippet(
                self.head_path,
                node.file_path,
                (node.extra or {}).get("line_start"),
                (node.extra or {}).get("line_end"),
            )
            if not snippet.strip():
                continue
            used += _estimate_tokens(snippet)
            if used > self.max_tokens_per_unit:
                break
            included.append(nid)
        return ReviewUnit(
            symbol_change=symbol_change,
            context_node_ids=included,
            before_snippet=before_snippet,
            after_snippet=after_snippet,
        )

    def load_snippet_for_node(self, store: GraphStore, node_id: str) -> str:
        """Load code snippet for a single graph node from head_path."""
        node = store.get_node(node_id)
        if not node:
            return ""
        return _read_snippet(
            self.head_path,
            node.file_path,
            (node.extra or {}).get("line_start"),
            (node.extra or {}).get("line_end"),
        )
