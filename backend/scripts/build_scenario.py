"""Build a Providence Financial District-style street graph cache.

Tries OSMnx download when available; otherwise writes a realistic synthetic
mesh around downtown Providence, RI coordinates.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

OUT = REPO / "data" / "scenarios" / "providence_fd"

# Downtown Providence bbox (approx Financial District / Kennedy Plaza area)
NORTH, SOUTH = 41.8305, 41.8215
EAST, WEST = -71.4070, -71.4185


def _synthetic_mesh(rows: int = 8, cols: int = 10) -> dict:
    """Grid mesh with slight irregularity to look street-like."""
    nodes = []
    node_id = 0
    id_at = {}
    for r in range(rows):
        for c in range(cols):
            # Skip a few cells to create block irregularities
            if (r, c) in {(2, 3), (5, 7)}:
                continue
            lat = SOUTH + (NORTH - SOUTH) * (r / (rows - 1))
            lng = WEST + (EAST - WEST) * (c / (cols - 1))
            # gentle waviness
            lat += 0.00015 * math.sin(c * 0.7)
            lng += 0.00012 * math.cos(r * 0.9)
            id_at[(r, c)] = node_id
            nodes.append({"id": node_id, "lat": lat, "lng": lng, "row": r, "col": c})
            node_id += 1

    edges = []
    for r in range(rows):
        for c in range(cols):
            if (r, c) not in id_at:
                continue
            u = id_at[(r, c)]
            for dr, dc in ((0, 1), (1, 0)):
                nr, nc = r + dr, c + dc
                if (nr, nc) not in id_at:
                    continue
                v = id_at[(nr, nc)]
                lat1, lng1 = nodes[u]["lat"], nodes[u]["lng"]
                lat2, lng2 = nodes[v]["lat"], nodes[v]["lng"]
                # rough meters
                dy = (lat2 - lat1) * 111_000
                dx = (lng2 - lng1) * 111_000 * math.cos(math.radians(lat1))
                length = max(40.0, math.hypot(dx, dy))
                edges.append({"u": u, "v": v, "length": round(length, 1), "oneway": False})

    return {"nodes": nodes, "edges": edges, "id_at": id_at, "rows": rows, "cols": cols}


def _pick_scenario(graph: dict) -> dict:
    nodes = {n["id"]: n for n in graph["nodes"]}
    # Prefer corners / edges for starts/goals
    by_col = {}
    for n in graph["nodes"]:
        by_col.setdefault(n.get("col", 0), []).append(n)

    def nearest(lat: float, lng: float) -> int:
        return min(
            nodes.values(),
            key=lambda n: (n["lat"] - lat) ** 2 + (n["lng"] - lng) ** 2,
        )["id"]

    depot = nearest(41.8225, -71.4175)
    bank = nearest(41.8295, -71.4085)
    decoy_a_start = nearest(41.8228, -71.4088)
    decoy_a_goal = nearest(41.8290, -71.4170)
    decoy_b_start = nearest(41.8260, -71.4178)
    decoy_b_goal = nearest(41.8255, -71.4075)
    decoy_c_start = nearest(41.8235, -71.4125)
    decoy_c_goal = nearest(41.8285, -71.4120)

    # Checkpoints: every other interior node on a "camera corridor"
    checkpoints = []
    for n in graph["nodes"]:
        r, c = n.get("row", 0), n.get("col", 0)
        if r in (2, 4, 6) and c in (2, 4, 6, 8):
            checkpoints.append(n["id"])
    if len(checkpoints) < 4:
        checkpoints = [n["id"] for n in list(graph["nodes"])[2::5][:8]]

    secret_nodes = checkpoints[len(checkpoints) // 2 : len(checkpoints) // 2 + 2]

    return {
        "name": "Providence Financial District",
        "security_mode": "type_b",
        "cargo_always_secret": True,
        "checkpoints": checkpoints,
        "secret_nodes": secret_nodes,
        "k_paths": 8,
        "max_replan": 16,
        "vehicles": [
            {
                "id": "cargo",
                "role": "cargo",
                "start": depot,
                "goal": bank,
                "start_label": "depot",
                "goal_label": "bank",
            },
            {
                "id": "decoy_a",
                "role": "decoy",
                "start": decoy_a_start,
                "goal": decoy_a_goal,
                "start_label": "east_yard",
                "goal_label": "west_yard",
            },
            {
                "id": "decoy_b",
                "role": "decoy",
                "start": decoy_b_start,
                "goal": decoy_b_goal,
                "start_label": "south_gate",
                "goal_label": "north_gate",
            },
            {
                "id": "decoy_c",
                "role": "decoy",
                "start": decoy_c_start,
                "goal": decoy_c_goal,
                "start_label": "mid_south",
                "goal_label": "mid_north",
            },
        ],
    }


def _try_osm() -> dict | None:
    try:
        import osmnx as ox
        from backend.graph.load_osm import networkx_to_graph_json

        print("Downloading OSM graph for Providence FD bbox…")
        G = ox.graph_from_bbox(
            bbox=(NORTH, SOUTH, EAST, WEST),
            network_type="drive",
            simplify=True,
        )
        data = networkx_to_graph_json(G)
        # tag row/col approximately for checkpoint picking
        lats = [n["lat"] for n in data["nodes"]]
        lngs = [n["lng"] for n in data["nodes"]]
        lat_min, lat_max = min(lats), max(lats)
        lng_min, lng_max = min(lngs), max(lngs)
        for n in data["nodes"]:
            n["row"] = int(round(7 * (n["lat"] - lat_min) / max(1e-9, lat_max - lat_min)))
            n["col"] = int(round(9 * (n["lng"] - lng_min) / max(1e-9, lng_max - lng_min)))
        return data
    except Exception as e:
        print(f"OSM download skipped ({e}); using synthetic mesh.")
        return None


def _add_seed_routes(graph_json: dict, scenario: dict) -> dict:
    """Attach lockstep opaque + leaky seed paths using NetworkX on the saved graph."""
    import networkx as nx
    from backend.graph.model import TransitionSystem
    from backend.planning.opacity import check_type_b

    g = nx.DiGraph()
    for n in graph_json["nodes"]:
        g.add_node(n["id"], lat=n["lat"], lng=n["lng"])
    for e in graph_json["edges"]:
        g.add_edge(e["u"], e["v"], length=e["length"])
        if not e.get("oneway"):
            g.add_edge(e["v"], e["u"], length=e["length"])

    cargo = next(v for v in scenario["vehicles"] if v["role"] == "cargo")
    decoys = [v for v in scenario["vehicles"] if v["role"] == "decoy"]
    spine = nx.shortest_path(g, cargo["start"], cargo["goal"], weight="length")
    cps = spine[1:-1:2] or spine[1:-1]
    scenario["checkpoints"] = cps
    scenario["secret_nodes"] = [cps[len(cps) // 2]] if cps else []

    ts = TransitionSystem.from_networkx(g, checkpoints=set(cps), secret_nodes=set(scenario["secret_nodes"]))

    d0 = decoys[0]
    prefix = nx.shortest_path(g, d0["start"], spine[0], weight="length")
    suffix = nx.shortest_path(g, spine[-1], d0["goal"], weight="length")
    hold = len(prefix) - 1
    cargo_synced = [spine[0]] * hold + list(spine)
    decoy0 = prefix[:-1] + list(spine) + suffix[1:]
    paths = {cargo["id"]: cargo_synced, d0["id"]: decoy0}
    for d in decoys[1:]:
        mid = spine[len(spine) // 2]
        p = (
            nx.shortest_path(g, d["start"], spine[0], weight="length")[:-1]
            + nx.shortest_path(g, spine[0], mid, weight="length")[:-1]
            + nx.shortest_path(g, mid, spine[-1], weight="length")[:-1]
            + nx.shortest_path(g, spine[-1], d["goal"], weight="length")
        )
        paths[d["id"]] = p
    T = max(len(p) for p in paths.values())
    for k, p in list(paths.items()):
        if len(p) < T:
            paths[k] = p + [p[-1]] * (T - len(p))

    leaky = {cargo["id"]: list(spine)}
    for d in decoys:
        # prefer paths that avoid checkpoints (bounded k-shortest)
        try:
            paths_k = []
            for i, c in enumerate(
                nx.shortest_simple_paths(g, d["start"], d["goal"], weight="length")
            ):
                paths_k.append(c)
                if i >= 11:
                    break
            chosen = paths_k[0]
            for c in paths_k:
                if not any(n in cps for n in c):
                    chosen = c
                    break
            else:
                chosen = min(paths_k, key=lambda c: sum(1 for n in c if n in cps))
        except Exception:
            chosen = nx.shortest_path(g, d["start"], d["goal"], weight="length")
        leaky[d["id"]] = chosen

    scenario["seed_opaque"] = paths
    scenario["seed_leaky"] = leaky
    # sanity
    v = check_type_b(ts, paths, cargo["id"])
    if not v.opaque:
        print("Warning: seed_opaque failed Type-B:", v.failures[:3])
    return scenario


def build(use_osm: bool = True) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    graph = _try_osm() if use_osm else None
    if graph is None:
        mesh = _synthetic_mesh()
        graph = {"nodes": mesh["nodes"], "edges": mesh["edges"]}

    scenario = _pick_scenario(graph)
    meta = {
        "id": "providence_fd",
        "name": "Providence Financial District",
        "description": "Cash-in-transit demo district near downtown Providence, RI",
        "center": {"lat": 41.8260, "lng": -71.4125},
        "zoom": 15,
        "bbox": {"north": NORTH, "south": SOUTH, "east": EAST, "west": WEST},
        "source": "osm" if use_osm and graph else "synthetic",
    }

    clean_nodes = [
        {"id": n["id"], "lat": n["lat"], "lng": n["lng"]} for n in graph["nodes"]
    ]
    clean_edges = [
        {
            "u": e["u"],
            "v": e["v"],
            "length": e["length"],
            "oneway": e.get("oneway", False),
        }
        for e in graph["edges"]
    ]
    graph_json = {"nodes": clean_nodes, "edges": clean_edges}
    scenario = _add_seed_routes(graph_json, scenario)

    (OUT / "graph.json").write_text(json.dumps(graph_json, indent=2), encoding="utf-8")
    (OUT / "scenario.json").write_text(json.dumps(scenario, indent=2), encoding="utf-8")
    (OUT / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"Wrote Providence scenario to {OUT} ({len(clean_nodes)} nodes)")
    return OUT


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--no-osm", action="store_true", help="Force synthetic mesh")
    args = p.parse_args()
    build(use_osm=not args.no_osm)
