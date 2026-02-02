"""
Graph-based retrieval: traverse from changed symbols to collect relevant context
(callers, callees, tests) with configurable depth and ranking.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Sequence

from app.models import EdgeType, GraphNode, SymbolKind
from app.graph.store import GraphStore


@dataclass
class RetrievalConfig:
    """Config for graph traversal and ranking."""

    depth_calls: int = 2
    depth_imports: int = 1
    depth_tests: int = 1
    max_nodes_per_unit: int = 30
    edge_weights: dict[EdgeType, float] | None = None  # higher = prefer


def _default_weights() -> dict[EdgeType, float]:
    return {
        EdgeType.TESTS: 1.5,
        EdgeType.CALLS: 1.0,
        EdgeType.IMPORTS: 0.8,
        EdgeType.INHERITS: 0.7,
        EdgeType.USES_CONFIG: 0.5,
    }


class RelevantContextFinder:
    """
    Given a list of changed symbol node IDs, traverse the graph (BFS) with
    configurable depth per edge type, score candidates by distance and type,
    and return a ranked list of node IDs to include as context.
    """

    def __init__(self, store: GraphStore, config: RetrievalConfig | None = None) -> None:
        self.store = store
        self.config = config or RetrievalConfig()
        self._weights = self.config.edge_weights or _default_weights()

    def find(
        self,
        changed_node_ids: Sequence[str],
    ) -> list[str]:
        """
        Return list of node IDs: changed nodes plus relevant context (callers,
        callees, tests), ranked by score, capped at max_nodes_per_unit.
        """
        if not changed_node_ids:
            return []
        seeds = set(changed_node_ids)
        # BFS with (node_id, depth, edge_type_used)
        scores: dict[str, float] = {}
        queue: deque[tuple[str, int, EdgeType | None]] = deque((nid, 0, None) for nid in seeds)
        for nid in seeds:
            scores[nid] = 2.0  # seed bonus
        seen = set(seeds)
        depth_limits = {
            EdgeType.CALLS: self.config.depth_calls,
            EdgeType.IMPORTS: self.config.depth_imports,
            EdgeType.TESTS: self.config.depth_tests,
            EdgeType.INHERITS: self.config.depth_calls,
            EdgeType.USES_CONFIG: self.config.depth_imports,
        }
        while queue:
            node_id, depth, in_edge_type = queue.popleft()
            node = self.store.get_node(node_id)
            if not node:
                continue
            for edge_type in EdgeType:
                max_d = depth_limits.get(edge_type, 1)
                if depth >= max_d:
                    continue
                w = self._weights.get(edge_type, 0.5)
                # Outgoing: callees, imports
                for out_id in self.store.neighbors_out(node_id, edge_type):
                    if out_id not in seen:
                        seen.add(out_id)
                        scores[out_id] = scores.get(out_id, 0) + w / (depth + 1)
                        queue.append((out_id, depth + 1, edge_type))
                # Incoming: callers, tests (who calls this / which tests use this)
                for in_id in self.store.neighbors_in(node_id, edge_type):
                    if in_id not in seen:
                        seen.add(in_id)
                        scores[in_id] = scores.get(in_id, 0) + w / (depth + 1)
                        queue.append((in_id, depth + 1, edge_type))
        # Prefer tests and hotspots (many inbound calls)
        for nid in scores:
            node = self.store.get_node(nid)
            if node and (node.kind == SymbolKind.TEST or (node.extra or {}).get("is_test_file")):
                scores[nid] += 0.5
            in_degree = len(self.store.neighbors_in(nid))
            if in_degree > 2:
                scores[nid] += 0.3
        sorted_ids = sorted(scores.keys(), key=lambda x: -scores[x])
        return sorted_ids[: self.config.max_nodes_per_unit]
