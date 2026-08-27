"""Toy 3x3 grid scenario for unit tests and local smoke demos."""

from __future__ import annotations

import json
from pathlib import Path

# Grid layout (node ids):
#  0 — 1 — 2
#  |   |   |
#  3 — 4 — 5
#  |   |   |
#  6 — 7 — 8
#
# Checkpoints at 1, 4, 7 (middle column = cameras)
# Cargo: 0 → 8 via secrets near center
# Decoys cover the same camera column

NODES = [
    {"id": i, "lat": 41.825 + (2 - i // 3) * 0.002, "lng": -71.415 + (i % 3) * 0.003}
    for i in range(9)
]

EDGES = []
for r in range(3):
    for c in range(3):
        u = r * 3 + c
        if c < 2:
            EDGES.append({"u": u, "v": u + 1, "length": 100.0, "oneway": False})
        if r < 2:
            EDGES.append({"u": u, "v": u + 3, "length": 100.0, "oneway": False})


def write_toy_scenario(root: Path | None = None) -> Path:
    root = root or Path(__file__).resolve().parents[2] / "data" / "scenarios" / "toy"
    root.mkdir(parents=True, exist_ok=True)

    graph = {"nodes": NODES, "edges": EDGES}
    scenario = {
        "name": "Toy Grid",
        "security_mode": "type_b",
        "cargo_always_secret": True,
        "checkpoints": [1, 4, 7],
        "secret_nodes": [4],
        "k_paths": 8,
        "max_replan": 20,
        "vehicles": [
            {
                "id": "cargo",
                "role": "cargo",
                "start": 0,
                "goal": 8,
                "start_label": "depot",
                "goal_label": "bank",
            },
            {
                "id": "decoy_a",
                "role": "decoy",
                "start": 2,
                "goal": 6,
                "start_label": "north",
                "goal_label": "south",
            },
            {
                "id": "decoy_b",
                "role": "decoy",
                "start": 6,
                "goal": 2,
                "start_label": "south",
                "goal_label": "north",
            },
        ],
        # Pre-seeded routes for demo without planner
        "seed_opaque": {
            "cargo": [0, 1, 4, 7, 8],
            "decoy_a": [2, 1, 4, 7, 6],
            "decoy_b": [6, 7, 4, 1, 2],
        },
        "seed_leaky": {
            "cargo": [0, 3, 4, 5, 8],
            "decoy_a": [2, 5, 8, 7, 6],
            "decoy_b": [6, 3, 0, 1, 2],
        },
    }
    meta = {
        "id": "toy",
        "name": "Toy Grid (3×3)",
        "description": "Synthetic grid for opacity unit tests and fast demos",
        "center": {"lat": 41.825, "lng": -71.412},
        "zoom": 15,
    }

    (root / "graph.json").write_text(json.dumps(graph, indent=2), encoding="utf-8")
    (root / "scenario.json").write_text(json.dumps(scenario, indent=2), encoding="utf-8")
    (root / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return root


if __name__ == "__main__":
    path = write_toy_scenario()
    print(f"Wrote toy scenario to {path}")
