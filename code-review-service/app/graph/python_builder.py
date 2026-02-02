"""
Build repository graph from Python source at head revision.
Nodes: modules, functions, classes, methods, tests. Edges: CALLS, IMPORTS, INHERITS, TESTS.
"""

from __future__ import annotations

import ast
import os
from pathlib import Path
from typing import Sequence

from app.models import EdgeType, GraphEdge, GraphNode, SymbolKind
from app.ast_.python_extractor import PythonLanguageParser, PythonSymbolExtractor
from app.graph.store import GraphStore


def _node_id(file_path: str, symbol_name: str, kind: SymbolKind, parent_class: str | None = None) -> str:
    if kind == SymbolKind.MODULE:
        return file_path.replace(os.sep, ".").replace(".py", "")
    if parent_class:
        return f"{file_path}::{parent_class}.{symbol_name}"
    return f"{file_path}::{symbol_name}"


def _module_id(file_path: str) -> str:
    return file_path.replace(os.sep, ".").replace(".py", "")


class _CallVisitor(ast.NodeVisitor):
    """Collect function/method call names (simple names only)."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    def visit_Call(self, node: ast.Call) -> None:
        name = None
        if isinstance(node.func, ast.Name):
            name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            try:
                name = ast.unparse(node.func)
            except Exception:
                name = getattr(node.func.attr, "attr", str(node.func.attr))
        if name:
            self.calls.append(name)
        self.generic_visit(node)


class _ImportVisitor(ast.NodeVisitor):
    """Collect import module names and aliases."""

    def __init__(self) -> None:
        self.imports: list[tuple[str, str | None]] = []  # (module_or_name, alias)

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self.imports.append((alias.name, alias.asname))
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = node.module or ""
        for alias in node.names:
            self.imports.append((f"{module}.{alias.name}" if module else alias.name, alias.asname))
        self.generic_visit(node)


def _is_test_file(file_path: str) -> bool:
    name = Path(file_path).name
    return name.startswith("test_") and name.endswith(".py") or name.endswith("_test.py")


class PythonGraphBuilder:
    """Build GraphStore from Python files under head_path."""

    def __init__(self, head_path: Path, language: str = "python") -> None:
        self.head_path = Path(head_path)
        self.language = language
        self.parser = PythonLanguageParser()
        self.extractor = PythonSymbolExtractor()
        self.store = GraphStore()

    def build(self, include_tests: bool = True) -> GraphStore:
        """Scan head_path for .py files, parse, add nodes and edges."""
        for py_path in self.head_path.rglob("*.py"):
            rel = py_path.relative_to(self.head_path)
            file_path = str(rel).replace("\\", "/")
            try:
                src = py_path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            tree = self.parser.parse(src, file_path)
            if tree is None:
                continue
            self._process_file(file_path, tree, src, include_tests)
        return self.store

    def _process_file(self, file_path: str, tree: ast.AST, source: str, include_tests: bool) -> None:
        symbols = list(self.extractor.extract(tree, file_path))
        module_id = _module_id(file_path)
        is_test = _is_test_file(file_path)

        # Module node
        self.store.add_node(
            GraphNode(
                id=module_id,
                kind=SymbolKind.MODULE,
                language=self.language,
                file_path=file_path,
                symbol_name=module_id,
                extra={"is_test_file": is_test},
            )
        )

        for s in symbols:
            kind = s.kind
            parent = (s.extra or {}).get("parent_class")
            nid = _node_id(file_path, s.name, kind, parent)
            node = GraphNode(
                id=nid,
                kind=kind,
                language=self.language,
                file_path=file_path,
                symbol_name=s.name,
                extra={"line_start": s.line_start, "line_end": s.line_end, "parent_class": parent},
            )
            self.store.add_node(node)
            self.store.add_edge(GraphEdge(src_id=nid, dst_id=module_id, type=EdgeType.IMPORTS))

            if kind == SymbolKind.CLASS:
                # INHERITS: base classes
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef) and node.name == s.name:
                        for base in node.bases:
                            base_name = None
                            if isinstance(base, ast.Name):
                                base_name = base.id
                            elif isinstance(base, ast.Attribute):
                                try:
                                    base_name = ast.unparse(base)
                                except Exception:
                                    base_name = getattr(base, "attr", None)
                            if base_name:
                                base_id = f"{file_path}::{base_name}"
                                if self.store.get_node(base_id):
                                    self.store.add_edge(GraphEdge(src_id=nid, dst_id=base_id, type=EdgeType.INHERITS))
                        break
            if kind == SymbolKind.METHOD or kind == SymbolKind.FUNCTION:
                # CALLS: get call names from function body
                call_visitor = _CallVisitor()
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        if node.name == s.name:
                            call_visitor.visit(node)
                            break
                for call_name in call_visitor.calls:
                    # Try to link to a known symbol in this file or leave as dangling (we don't resolve cross-file yet)
                    target_id = f"{file_path}::{call_name}"
                    if self.store.get_node(target_id):
                        self.store.add_edge(GraphEdge(src_id=nid, dst_id=target_id, type=EdgeType.CALLS))
                    # Also link to module if it's an import
                    if self.store.get_node(module_id):
                        pass  # already have IMPORTS from symbol to module

            if is_test and include_tests:
                # TESTS: test file -> imported modules (test imports code under test)
                import_visitor = _ImportVisitor()
                import_visitor.visit(tree)
                for imp_name, _ in import_visitor.imports:
                    # Normalize to module path (e.g. from foo.bar import baz -> foo.bar)
                    base_module = imp_name.split(".")[0] if "." in imp_name else imp_name
                    # Find a node for that module (we have module nodes only by file path)
                    for nid_iter in self.store.all_node_ids():
                        node_obj = self.store.get_node(nid_iter)
                        if node_obj and node_obj.kind == SymbolKind.MODULE and (
                            base_module in node_obj.symbol_name or node_obj.symbol_name.endswith("." + base_module)
                        ):
                            self.store.add_edge(GraphEdge(src_id=module_id, dst_id=nid_iter, type=EdgeType.TESTS))
                            break

        # IMPORTS edges: from this module to imported modules
        import_visitor = _ImportVisitor()
        import_visitor.visit(tree)
        for imp_name, _ in import_visitor.imports:
            # Resolve to a known module node if we have one
            other_module_id = imp_name.replace("/", ".").replace(".py", "")
            if "." in other_module_id:
                other_module_id = other_module_id.split(".")[0]
            for nid_iter in self.store.all_node_ids():
                node_obj = self.store.get_node(nid_iter)
                if node_obj and node_obj.kind == SymbolKind.MODULE and (
                    other_module_id in nid_iter or nid_iter.endswith("." + other_module_id)
                ):
                    self.store.add_edge(GraphEdge(src_id=module_id, dst_id=nid_iter, type=EdgeType.IMPORTS))
                    break
