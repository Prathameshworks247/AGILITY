"""
In-memory graph store using networkx.
Holds GraphNode and GraphEdge data; supports traversal for retrieval.
"""

from __future__ import annotations

from typing import Any, Iterator

import networkx as nx

from app.models import EdgeType, GraphEdge, GraphNode


class GraphStore:
    """In-memory directed graph of repository symbols and relationships."""

    def __init__(self) -> None:
        self._g: nx.DiGraph = nx.DiGraph()
        self._nodes: dict[str, GraphNode] = {}

    def add_node(self, node: GraphNode) -> None:
        self._nodes[node.id] = node
        self._g.add_node(
            node.id,
            kind=node.kind.value,
            language=node.language,
            file_path=node.file_path,
            symbol_name=node.symbol_name,
            **(node.extra or {}),
        )

    def add_edge(self, edge: GraphEdge) -> None:
        if edge.src_id in self._nodes and edge.dst_id in self._nodes:
            self._g.add_edge(edge.src_id, edge.dst_id, type=edge.type.value, **(edge.extra or {}))

    def get_node(self, node_id: str) -> GraphNode | None:
        return self._nodes.get(node_id)

    def neighbors_out(self, node_id: str, edge_type: EdgeType | None = None) -> list[str]:
        """Successors (outgoing edges). Optionally filter by edge type."""
        if node_id not in self._g:
            return []
        out = []
        for _, dst, data in self._g.out_edges(node_id, data=True):
            if edge_type is None or data.get("type") == edge_type.value:
                out.append(dst)
        return out

    def neighbors_in(self, node_id: str, edge_type: EdgeType | None = None) -> list[str]:
        """Predecessors (incoming edges). Optionally filter by edge type."""
        if node_id not in self._g:
            return []
        out = []
        for src, _, data in self._g.in_edges(node_id, data=True):
            if edge_type is None or data.get("type") == edge_type.value:
                out.append(src)
        return out

    def all_node_ids(self) -> Iterator[str]:
        return iter(self._nodes)

    def node_count(self) -> int:
        return len(self._nodes)

    def edge_count(self) -> int:
        return self._g.number_of_edges()

    def to_networkx(self) -> nx.DiGraph:
        return self._g
