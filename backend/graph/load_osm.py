"""Load cached road graphs and scenario metadata."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import networkx as nx

from .model import TransitionSystem

# Repo root: backend/graph/load_osm.py -> ../../
REPO_ROOT = Path(__file__).resolve().parents[2]
SCENARIOS_DIR = REPO_ROOT / "data" / "scenarios"


def list_scenarios() -> list[dict[str, Any]]:
    """List available scenario directories with metadata."""
    results: list[dict[str, Any]] = []
    if not SCENARIOS_DIR.exists():
        return results
    for path in sorted(SCENARIOS_DIR.iterdir()):
        if not path.is_dir():
            continue
        meta_path = path / "meta.json"
        meta: dict[str, Any] = {"id": path.name, "name": path.name}
        if meta_path.exists():
            meta.update(json.loads(meta_path.read_text(encoding="utf-8")))
        meta["id"] = path.name
        results.append(meta)
    return results


def _graph_from_json(data: dict[str, Any]) -> nx.DiGraph:
    g = nx.DiGraph()
    for node in data.get("nodes", []):
        nid = node["id"]
        attrs = {k: v for k, v in node.items() if k != "id"}
        g.add_node(nid, **attrs)
    for edge in data.get("edges", []):
        u, v = edge["u"], edge["v"]
        attrs = {k: v for k, v in edge.items() if k not in ("u", "v")}
        if "length" not in attrs:
            attrs["length"] = float(attrs.get("weight", 1.0))
        g.add_edge(u, v, **attrs)
        # undirected roads: add reverse if not one-way
        if not attrs.get("oneway", False):
            g.add_edge(v, u, **attrs)
    return g


def load_scenario_graph(scenario_id: str) -> tuple[TransitionSystem, dict[str, Any]]:
    """Load a TransitionSystem and scenario JSON for the given id."""
    base = SCENARIOS_DIR / scenario_id
    if not base.exists():
        raise FileNotFoundError(f"Scenario not found: {scenario_id}")

    graph_path = base / "graph.json"
    scenario_path = base / "scenario.json"
    meta_path = base / "meta.json"

    graph_data = json.loads(graph_path.read_text(encoding="utf-8"))
    scenario = json.loads(scenario_path.read_text(encoding="utf-8"))
    meta = {}
    if meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))

    g = _graph_from_json(graph_data)
    checkpoints = set(scenario.get("checkpoints", []))
    secret_nodes = set(scenario.get("secret_nodes", []))
    zone_of = {int(k) if str(k).isdigit() else k: v for k, v in scenario.get("zones", {}).items()}
    # normalize checkpoint/secret ids to match graph node types
    node_sample = next(iter(g.nodes), None)
    if isinstance(node_sample, int):
        checkpoints = {int(c) for c in checkpoints}
        secret_nodes = {int(s) for s in secret_nodes}
    else:
        checkpoints = {str(c) for c in checkpoints}
        secret_nodes = {str(s) for s in secret_nodes}

    ts = TransitionSystem.from_networkx(
        g,
        checkpoints=checkpoints,
        secret_nodes=secret_nodes,
        zone_of=zone_of,
        meta={"scenario_id": scenario_id, **meta},
    )
    return ts, scenario


def download_osm_bbox(
    north: float,
    south: float,
    east: float,
    west: float,
    network_type: str = "drive",
) -> nx.MultiDiGraph:
    """Download an OSM street network for a bounding box (requires osmnx + network)."""
    import osmnx as ox

    return ox.graph_from_bbox(
        bbox=(north, south, east, west),
        network_type=network_type,
    )


def networkx_to_graph_json(g: nx.Graph) -> dict[str, Any]:
    """Serialize a NetworkX graph (possibly MultiDiGraph from OSMnx) to our JSON schema."""
    # Simplify to DiGraph with aggregated length
    simple = nx.DiGraph()
    for n, data in g.nodes(data=True):
        simple.add_node(
            int(n) if not isinstance(n, str) else n,
            lat=float(data.get("y", data.get("lat", 0))),
            lng=float(data.get("x", data.get("lng", 0))),
        )

    for u, v, data in g.edges(data=True):
        uid = int(u) if not isinstance(u, str) else u
        vid = int(v) if not isinstance(v, str) else v
        length = float(data.get("length", 1.0))
        oneway = bool(data.get("oneway", False))
        if simple.has_edge(uid, vid):
            # keep shortest parallel edge
            if length < simple[uid][vid]["length"]:
                simple[uid][vid]["length"] = length
        else:
            simple.add_edge(uid, vid, length=length, oneway=oneway)

    return {
        "nodes": [
            {"id": n, "lat": d["lat"], "lng": d["lng"]}
            for n, d in simple.nodes(data=True)
        ],
        "edges": [
            {"u": u, "v": v, "length": d["length"], "oneway": d.get("oneway", False)}
            for u, v, d in simple.edges(data=True)
        ],
    }
