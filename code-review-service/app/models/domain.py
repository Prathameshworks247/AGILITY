"""Domain models for the graph-based LLM code review system."""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class SymbolKind(str, Enum):
    """Kind of symbol in the code graph."""

    MODULE = "module"
    FUNCTION = "function"
    CLASS = "class"
    METHOD = "method"
    CONSTANT = "constant"
    TEST = "test"


class ChangeType(str, Enum):
    """Type of symbol-level change."""

    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"


class EdgeType(str, Enum):
    """Type of edge in the repository graph."""

    CALLS = "CALLS"
    IMPORTS = "IMPORTS"
    INHERITS = "INHERITS"
    TESTS = "TESTS"
    USES_CONFIG = "USES_CONFIG"


class RepositoryRef(BaseModel):
    """Reference to a repository (clone URL and optional path)."""

    url: str = Field(..., description="Clone URL of the repository")
    default_branch: Optional[str] = Field(None, description="Default branch name, e.g. main")


class PullRequestRef(BaseModel):
    """Reference to a pull request (base and head refs)."""

    repository: RepositoryRef
    base_ref: str = Field(..., description="Base ref or SHA, e.g. main or abc123")
    head_ref: str = Field(..., description="Head ref or SHA, e.g. feature-branch or def456")
    pr_id: Optional[str] = Field(None, description="Provider PR number or identifier")


class FileChange(BaseModel):
    """A single file-level change in a diff."""

    path: str = Field(..., description="Repository-relative file path")
    change_type: str = Field(..., description="added, removed, modified, renamed")
    language: Optional[str] = Field(None, description="Detected or configured language, e.g. python")
    old_path: Optional[str] = Field(None, description="For renames, the previous path")


class SymbolChange(BaseModel):
    """A symbol-level (semantic) change within a file."""

    file_path: str
    symbol_name: str
    kind: SymbolKind
    change_type: ChangeType
    descriptors: Optional[list[str]] = Field(
        None,
        description="Change descriptors, e.g. signature_change, new_branches",
    )
    line_start: Optional[int] = None
    line_end: Optional[int] = None


class GraphNode(BaseModel):
    """Node in the repository graph (symbol or module)."""

    id: str = Field(..., description="Unique node ID, e.g. file_path::symbol_name")
    kind: SymbolKind
    language: str = Field(..., description="e.g. python")
    file_path: str
    symbol_name: str = Field(..., description="Symbol name or module path")
    extra: Optional[dict[str, Any]] = Field(None, description="Extra metadata (line range, decorators, etc.)")


class GraphEdge(BaseModel):
    """Directed edge in the repository graph."""

    src_id: str
    dst_id: str
    type: EdgeType
    extra: Optional[dict[str, Any]] = None


class ReviewUnit(BaseModel):
    """A single unit of review (e.g. a changed function or class) with its context."""

    symbol_change: SymbolChange
    context_node_ids: list[str] = Field(
        default_factory=list,
        description="Graph node IDs of relevant context (callers, callees, tests)",
    )
    before_snippet: Optional[str] = None
    after_snippet: Optional[str] = None


class ReviewFinding(BaseModel):
    """A single finding from the LLM review."""

    severity: str = Field(..., description="info, warn, error")
    category: str = Field(..., description="correctness, security, performance, style")
    location_file: str
    location_line_start: Optional[int] = None
    location_line_end: Optional[int] = None
    symbol: Optional[str] = None
    message: str
    suggested_fix: Optional[str] = None
