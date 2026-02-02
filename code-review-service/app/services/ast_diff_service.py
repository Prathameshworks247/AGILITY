"""
Orchestrates AST parsing, symbol extraction, and semantic diff for changed files.
"""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

from app.models import ChangeType, FileChange, SymbolChange
from app.ast_.interfaces import LanguageParser, SemanticDiffer, SymbolExtractor
from app.ast_.python_extractor import PythonLanguageParser, PythonSymbolExtractor
from app.ast_.python_differ import PythonSemanticDiffer


def get_python_parser() -> tuple[LanguageParser, SymbolExtractor, SemanticDiffer]:
    return PythonLanguageParser(), PythonSymbolExtractor(), PythonSemanticDiffer()


def run_ast_diff(
    file_changes: Sequence[FileChange],
    base_path: Path,
    head_path: Path,
) -> list[SymbolChange]:
    """
    For each changed file that we support (Python), parse base and head,
    extract symbols, run semantic diff. Returns flattened list of SymbolChange.
    """
    parser, extractor, differ = get_python_parser()
    all_changes: list[SymbolChange] = []
    for fc in file_changes:
        if fc.change_type == "removed":
            # Can still have symbol removals if we parse base only
            base_file = base_path / fc.path
            if not base_file.exists():
                continue
            try:
                base_src = base_file.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            base_ast = parser.parse(base_src, fc.path)
            if base_ast is None:
                continue
            base_symbols = list(extractor.extract(base_ast, fc.path))
            for s in base_symbols:
                all_changes.append(
                    SymbolChange(
                        file_path=fc.path,
                        symbol_name=s.name,
                        kind=s.kind,
                        change_type=ChangeType.REMOVED,
                        descriptors=["removed"],
                        line_start=s.line_start,
                        line_end=s.line_end,
                    )
                )
            continue
        if fc.change_type == "added":
            head_file = head_path / fc.path
            if not head_file.exists():
                continue
            try:
                head_src = head_file.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            head_ast = parser.parse(head_src, fc.path)
            if head_ast is None:
                continue
            head_symbols = list(extractor.extract(head_ast, fc.path))
            for s in head_symbols:
                all_changes.append(
                    SymbolChange(
                        file_path=fc.path,
                        symbol_name=s.name,
                        kind=s.kind,
                        change_type=ChangeType.ADDED,
                        descriptors=["added"],
                        line_start=s.line_start,
                        line_end=s.line_end,
                    )
                )
            continue
        # modified (or renamed): diff base vs head
        if not parser.supports_file(fc.path):
            continue
        base_file = base_path / fc.path
        head_file = head_path / fc.path
        if not head_file.exists():
            continue
        try:
            head_src = head_file.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        base_src = None
        if base_file.exists():
            try:
                base_src = base_file.read_text(encoding="utf-8", errors="replace")
            except Exception:
                pass
        base_ast = parser.parse(base_src or "", fc.path) if base_src else None
        head_ast = parser.parse(head_src, fc.path)
        if head_ast is None:
            continue
        base_symbols = list(extractor.extract(base_ast, fc.path)) if base_ast else []
        head_symbols = list(extractor.extract(head_ast, fc.path))
        file_changes_sym = differ.diff(fc.path, base_symbols, head_symbols, base_src, head_src)
        all_changes.extend(file_changes_sym)
    return all_changes
