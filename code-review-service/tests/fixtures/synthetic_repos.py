"""
Synthetic repo fixtures: simple function changes, multi-hop dependency chains,
and test coverage gaps. Used by the evaluation harness to compare graph-based
vs flat retrieval.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Sequence


def create_simple_dependency_repo(root: Path) -> None:
    """
    Repo with one changed function and a single-level dependency (one callee).
    - foo.py: def bar() -> int; def foo() -> int (calls bar)
    - test_foo.py: imports foo, tests foo()
    """
    root.mkdir(parents=True, exist_ok=True)
    (root / "foo.py").write_text(
        "def bar() -> int:\n    return 42\n\n\ndef foo() -> int:\n    return bar() + 1\n",
        encoding="utf-8",
    )
    (root / "test_foo.py").write_text(
        "from foo import foo\n\n\ndef test_foo() -> None:\n    assert foo() == 43\n",
        encoding="utf-8",
    )


def create_multi_hop_repo(root: Path) -> None:
    """
    Repo with multi-hop dependency chain and cross-module impact.
    - a.py: def a() -> int
    - b.py: from a import a; def b() -> int (calls a)
    - c.py: from b import b; def c() -> int (calls b)
    - test_c.py: tests c()
    """
    root.mkdir(parents=True, exist_ok=True)
    (root / "a.py").write_text("def a() -> int:\n    return 1\n", encoding="utf-8")
    (root / "b.py").write_text(
        "from a import a\n\n\ndef b() -> int:\n    return a() + 1\n",
        encoding="utf-8",
    )
    (root / "c.py").write_text(
        "from b import b\n\n\ndef c() -> int:\n    return b() + 1\n",
        encoding="utf-8",
    )
    (root / "test_c.py").write_text(
        "from c import c\n\n\ndef test_c() -> None:\n    assert c() == 3\n",
        encoding="utf-8",
    )


def create_test_gap_repo(root: Path) -> None:
    """
    Repo with changed code that has no tests (test coverage gap).
    - logic.py: def compute() -> int
    - (no test_logic.py)
    """
    root.mkdir(parents=True, exist_ok=True)
    (root / "logic.py").write_text(
        "def compute() -> int:\n    return 0\n",
        encoding="utf-8",
    )


def fixture_dir() -> Path:
    """Return path to tests/fixtures directory."""
    return Path(__file__).resolve().parent


def get_fixture_repo_path(name: str) -> Path:
    """Return path to a fixture repo (create in a temp dir for eval)."""
    base = fixture_dir() / "repos"
    base.mkdir(parents=True, exist_ok=True)
    path = base / name
    if name == "simple":
        create_simple_dependency_repo(path)
    elif name == "multi_hop":
        create_multi_hop_repo(path)
    elif name == "test_gap":
        create_test_gap_repo(path)
    return path
