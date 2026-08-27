"""Weighted transition system abstraction over a road graph."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Hashable

import networkx as nx

# Silent observation (node not at a checkpoint)
EPSILON = "ε"


@dataclass
class ObservationMap:
    """Maps nodes to observation symbols for a passive intruder."""

    checkpoints: set[Hashable]
    # optional: group several nodes into one camera zone
    zone_of: dict[Hashable, str] = field(default_factory=dict)

    def observe(self, node: Hashable) -> str:
        if node not in self.checkpoints:
            return EPSILON
        return self.zone_of.get(node, str(node))

    def project_path(self, path: list[Hashable]) -> list[str]:
        """Project a node path to its observation sequence (including ε)."""
        return [self.observe(n) for n in path]

    def visible_trace(self, path: list[Hashable]) -> list[str]:
        """Observation sequence with silent steps removed (what UI shows)."""
        return [o for o in self.project_path(path) if o != EPSILON]


@dataclass
class TransitionSystem:
    """Finite weighted transition system over road-network nodes."""

    graph: nx.DiGraph
    observation: ObservationMap
    secret_nodes: set[Hashable] = field(default_factory=set)
    meta: dict[str, Any] = field(default_factory=dict)

    @property
    def nodes(self) -> list[Hashable]:
        return list(self.graph.nodes)

    def neighbors(self, node: Hashable) -> list[Hashable]:
        return list(self.graph.successors(node))

    def weight(self, u: Hashable, v: Hashable) -> float:
        data = self.graph.get_edge_data(u, v) or {}
        return float(data.get("length", data.get("weight", 1.0)))

    def path_cost(self, path: list[Hashable]) -> float:
        if len(path) < 2:
            return 0.0
        total = 0.0
        for i in range(len(path) - 1):
            u, v = path[i], path[i + 1]
            if u == v:
                continue  # wait-in-place hold
            total += self.weight(u, v)
        return total

    def is_secret(self, node: Hashable) -> bool:
        return node in self.secret_nodes

    def node_coords(self, node: Hashable) -> tuple[float, float]:
        """Return (lat, lng) for a node."""
        data = self.graph.nodes[node]
        if "lat" in data and "lng" in data:
            return float(data["lat"]), float(data["lng"])
        # OSMnx often uses y=lat, x=lng
        return float(data.get("y", data.get("lat", 0.0))), float(
            data.get("x", data.get("lng", 0.0))
        )

    def shortest_path(self, source: Hashable, target: Hashable) -> list[Hashable]:
        return nx.shortest_path(self.graph, source, target, weight="length")

    def k_shortest_paths(
        self, source: Hashable, target: Hashable, k: int = 5
    ) -> list[list[Hashable]]:
        """Yen-style k-shortest simple paths by length."""
        try:
            gen = nx.shortest_simple_paths(self.graph, source, target, weight="length")
            paths: list[list[Hashable]] = []
            for i, path in enumerate(gen):
                if i >= k:
                    break
                paths.append(list(path))
            return paths
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return []

    @classmethod
    def from_networkx(
        cls,
        graph: nx.DiGraph,
        checkpoints: set[Hashable],
        secret_nodes: set[Hashable] | None = None,
        zone_of: dict[Hashable, str] | None = None,
        meta: dict[str, Any] | None = None,
    ) -> TransitionSystem:
        # Ensure length attribute exists
        g = graph.copy()
        for u, v, data in g.edges(data=True):
            if "length" not in data:
                data["length"] = float(data.get("weight", 1.0))
        obs = ObservationMap(checkpoints=set(checkpoints), zone_of=zone_of or {})
        return cls(
            graph=g,
            observation=obs,
            secret_nodes=set(secret_nodes or []),
            meta=meta or {},
        )
