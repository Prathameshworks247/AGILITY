"""
Python semantic diff: compare base vs head symbol tables and produce SymbolChange list.
"""

from __future__ import annotations

from typing import Sequence

from app.models import ChangeType, SymbolChange, SymbolKind
from app.ast_.interfaces import SemanticDiffer, SymbolInfo


def _symbol_key(s: SymbolInfo) -> tuple[str, SymbolKind, str | None]:
    """Key for matching symbols (name, kind, parent_class for methods)."""
    parent = (s.extra or {}).get("parent_class")
    return (s.name, s.kind, parent)


class PythonSemanticDiffer(SemanticDiffer):
    """Compare base vs head symbol tables; produce Added/Removed/Modified with descriptors."""

    def diff(
        self,
        file_path: str,
        base_symbols: Sequence[SymbolInfo],
        head_symbols: Sequence[SymbolInfo],
        base_source: str | None = None,
        head_source: str | None = None,
    ) -> Sequence[SymbolChange]:
        base_by_key = {_symbol_key(s): s for s in base_symbols}
        head_by_key = {_symbol_key(s): s for s in head_symbols}
        changes: list[SymbolChange] = []

        for key, head_s in head_by_key.items():
            base_s = base_by_key.get(key)
            if base_s is None:
                changes.append(
                    SymbolChange(
                        file_path=file_path,
                        symbol_name=head_s.name,
                        kind=head_s.kind,
                        change_type=ChangeType.ADDED,
                        descriptors=["added"],
                        line_start=head_s.line_start,
                        line_end=head_s.line_end,
                    )
                )
                continue
            descriptors = self._compare_symbols(base_s, head_s)
            if descriptors:
                changes.append(
                    SymbolChange(
                        file_path=file_path,
                        symbol_name=head_s.name,
                        kind=head_s.kind,
                        change_type=ChangeType.MODIFIED,
                        descriptors=descriptors,
                        line_start=head_s.line_start,
                        line_end=head_s.line_end,
                    )
                )

        for key, base_s in base_by_key.items():
            if key not in head_by_key:
                changes.append(
                    SymbolChange(
                        file_path=file_path,
                        symbol_name=base_s.name,
                        kind=base_s.kind,
                        change_type=ChangeType.REMOVED,
                        descriptors=["removed"],
                        line_start=base_s.line_start,
                        line_end=base_s.line_end,
                    )
                )

        return changes

    def _compare_symbols(self, base_s: SymbolInfo, head_s: SymbolInfo) -> list[str]:
        """Return list of change descriptors for a modified symbol."""
        descriptors: list[str] = []
        if base_s.signature != head_s.signature:
            descriptors.append("signature_change")
        if base_s.docstring != head_s.docstring:
            descriptors.append("docstring_change")
        if base_s.decorators != head_s.decorators:
            descriptors.append("decorator_change")
        return descriptors
