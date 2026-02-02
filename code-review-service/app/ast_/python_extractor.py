"""
Python symbol extraction using the standard ast module.
"""

from __future__ import annotations

import ast
from typing import Any, Sequence

from app.models import SymbolKind
from app.ast_.interfaces import LanguageParser, SymbolExtractor, SymbolInfo


def _get_docstring(node: ast.AST) -> str | None:
    return ast.get_docstring(node)


def _format_args(args: ast.arguments) -> str:
    names = []
    for a in args.posonlyargs:
        names.append(a.arg)
    if args.posonlyargs:
        names.append("/")
    for a in args.args:
        names.append(a.arg)
    if args.vararg:
        names.append("*" + args.vararg.arg)
    for a in args.kwonlyargs:
        names.append(a.arg)
    if args.kwarg:
        names.append("**" + args.kwarg.arg)
    return "(" + ", ".join(names) + ")"


def _decorator_list_str(decorator_list: list) -> list[str]:
    out = []
    for d in decorator_list:
        try:
            out.append(ast.unparse(d))
        except Exception:
            out.append(str(d))
    return out


class PythonLanguageParser(LanguageParser):
    """Parse Python source into ast.AST."""

    def parse(self, source: str, file_path: str = "") -> ast.AST | None:
        try:
            return ast.parse(source, filename=file_path or "<string>")
        except SyntaxError:
            return None

    def supports_file(self, file_path: str) -> bool:
        return file_path.endswith(".py") or file_path.endswith(".pyi")


class _Visitor(ast.NodeVisitor):
    """Collect symbols and track current class for method kind."""

    def __init__(self, file_path: str) -> None:
        self.file_path = file_path
        self.symbols: list[SymbolInfo] = []
        self._current_class: str | None = None

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.symbols.append(
            SymbolInfo(
                name=node.name,
                kind=SymbolKind.CLASS,
                line_start=node.lineno or 0,
                line_end=node.end_lineno or node.lineno or 0,
                signature=node.name,
                docstring=_get_docstring(node),
                decorators=_decorator_list_str(node.decorator_list),
                extra={},
            )
        )
        prev = self._current_class
        self._current_class = node.name
        self.generic_visit(node)
        self._current_class = prev

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        kind = SymbolKind.METHOD if self._current_class else SymbolKind.FUNCTION
        sig = node.name + _format_args(node.args)
        self.symbols.append(
            SymbolInfo(
                name=node.name,
                kind=kind,
                line_start=node.lineno or 0,
                line_end=node.end_lineno or node.lineno or 0,
                signature=sig,
                docstring=_get_docstring(node),
                decorators=_decorator_list_str(node.decorator_list),
                extra={"parent_class": self._current_class},
            )
        )
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        if self._current_class is not None:
            self.generic_visit(node)
            return
        for t in node.targets:
            if isinstance(t, ast.Name) and not any(s.name == t.id for s in self.symbols):
                self.symbols.append(
                    SymbolInfo(
                        name=t.id,
                        kind=SymbolKind.CONSTANT,
                        line_start=node.lineno or 0,
                        line_end=node.end_lineno or node.lineno or 0,
                        signature=t.id,
                        extra={},
                    )
                )
                break
        self.generic_visit(node)


class PythonSymbolExtractor(SymbolExtractor):
    """Extract functions, classes, methods, and important constants from Python AST."""

    def extract(self, ast_node: Any, file_path: str) -> Sequence[SymbolInfo]:
        if ast_node is None or not isinstance(ast_node, ast.AST):
            return []
        v = _Visitor(file_path)
        v.visit(ast_node)
        return v.symbols
