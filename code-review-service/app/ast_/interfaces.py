"""
Generic interfaces for language parsers, symbol extraction, and semantic diff.
Allows adding TS/JS later via tree-sitter or tsserver.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Sequence

from app.models import SymbolChange, SymbolKind


class SymbolInfo:
    """Generic symbol info extracted from source (language-agnostic view)."""

    __slots__ = ("name", "kind", "line_start", "line_end", "signature", "docstring", "decorators", "extra")

    def __init__(
        self,
        name: str,
        kind: SymbolKind,
        line_start: int = 0,
        line_end: int = 0,
        signature: str | None = None,
        docstring: str | None = None,
        decorators: Sequence[str] | None = None,
        extra: dict[str, Any] | None = None,
    ):
        self.name = name
        self.kind = kind
        self.line_start = line_start
        self.line_end = line_end
        self.signature = signature
        self.docstring = docstring
        self.decorators = list(decorators) if decorators else []
        self.extra = dict(extra) if extra else {}

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SymbolInfo):
            return False
        return (
            self.name == other.name
            and self.kind == other.kind
            and self.signature == other.signature
        )


class LanguageParser(ABC):
    """Parse source code into a language-specific AST (opaque to caller)."""

    @abstractmethod
    def parse(self, source: str, file_path: str = "") -> Any:
        """Return AST or parse tree. Type is implementation-defined."""
        pass

    @abstractmethod
    def supports_file(self, file_path: str) -> bool:
        """Return True if this parser handles the given file."""
        pass


class SymbolExtractor(ABC):
    """Extract symbol table from parsed AST."""

    @abstractmethod
    def extract(self, ast: Any, file_path: str) -> Sequence[SymbolInfo]:
        """Return list of symbols (functions, classes, methods, constants) for the file."""
        pass


class SemanticDiffer(ABC):
    """Compare base and head symbol tables and produce SymbolChange list."""

    @abstractmethod
    def diff(
        self,
        file_path: str,
        base_symbols: Sequence[SymbolInfo],
        head_symbols: Sequence[SymbolInfo],
        base_source: str | None = None,
        head_source: str | None = None,
    ) -> Sequence[SymbolChange]:
        """
        Compare base vs head symbols and return added/removed/modified changes.
        Optional base_source/head_source for computing change descriptors.
        """
        pass
