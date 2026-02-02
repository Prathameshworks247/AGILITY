"""
Tests for the evaluation harness and pipeline components.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.models import FileChange, PullRequestRef, RepositoryRef, SymbolChange, SymbolKind
from app.ast_.python_extractor import PythonLanguageParser, PythonSymbolExtractor
from app.ast_.python_differ import PythonSemanticDiffer
from app.ast_.interfaces import SymbolInfo
from app.graph.python_builder import PythonGraphBuilder
from app.graph.store import GraphStore
from app.graph.retrieval import RelevantContextFinder, RetrievalConfig
from app.services.ast_diff_service import run_ast_diff


def test_python_symbol_extraction() -> None:
    source = """
def foo() -> int:
    return 1

class Bar:
    def baz(self) -> None:
        pass
"""
    parser = PythonLanguageParser()
    extractor = PythonSymbolExtractor()
    tree = parser.parse(source, "test.py")
    assert tree is not None
    symbols = list(extractor.extract(tree, "test.py"))
    names = [s.name for s in symbols]
    assert "foo" in names
    assert "Bar" in names
    assert "baz" in names
    kinds = {s.name: s.kind for s in symbols}
    assert kinds["foo"] == SymbolKind.FUNCTION
    assert kinds["Bar"] == SymbolKind.CLASS
    assert kinds["baz"] == SymbolKind.METHOD


def test_python_semantic_differ() -> None:
    base_symbols = [
        SymbolInfo("foo", SymbolKind.FUNCTION, 1, 3, "foo()", None),
    ]
    head_symbols = [
        SymbolInfo("foo", SymbolKind.FUNCTION, 1, 4, "foo(x)", None),
    ]
    differ = PythonSemanticDiffer()
    changes = list(differ.diff("f.py", base_symbols, head_symbols))
    assert len(changes) == 1
    assert changes[0].change_type.value == "modified"
    assert "signature_change" in (changes[0].descriptors or [])


def test_graph_builder_simple() -> None:
    from tests.fixtures.synthetic_repos import create_simple_dependency_repo
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        create_simple_dependency_repo(root)
        builder = PythonGraphBuilder(root)
        store = builder.build()
        assert store.node_count() >= 2
        assert store.edge_count() >= 0


def test_eval_harness_run() -> None:
    from tests.eval_harness import run_harness, EvalResult
    results = run_harness(fixture_names=("simple",))
    assert len(results) >= 1
    r = results[0]
    assert isinstance(r, EvalResult)
    assert r.file_changes_count >= 0
    assert r.graph_nodes >= 0
