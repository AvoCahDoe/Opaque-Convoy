"""
Opaque Convoy FastAPI backend.

Serves road graphs, opacity-aware convoy plans, and cost/opacity trade-off data.
"""

from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.experiments.cost_opacity_sweep import cost_opacity_sweep
from backend.graph.load_osm import list_scenarios, load_scenario_graph
from backend.planning.ltl_tasks import load_task_spec
from backend.planning.opacity import check_opacity
from backend.pipeline.graph_pipeline import run_pipeline
from backend.scripts.write_toy_scenario import write_toy_scenario

# Ensure toy scenario exists on boot
write_toy_scenario()

app = FastAPI(
    title="Opaque Convoy API",
    description=(
        "Provably secure route planning for high-value transport. "
        "Implements Type-A / Type-B security (arXiv:2605.13134) over OSM-derived "
        "street graphs with a LangGraph planner loop."
    ),
    version="1.0.0",
    contact={
        "name": "Farid El Boubkraoui",
        "email": "farid.elboubkraoui@w-ays.de",
        "url": "https://github.com/AvoCahDoe/Opaque-Convoy",
    },
    license_info={"name": "MIT"},
    openapi_tags=[
        {"name": "health", "description": "Liveness probes"},
        {"name": "scenarios", "description": "Cached road districts and task specs"},
        {"name": "planning", "description": "Opacity-aware convoy planning"},
        {"name": "experiments", "description": "Cost vs opacity sweeps"},
    ],
)

_cors_origins = os.environ.get(
    "CORS_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173,https://*.vercel.app",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class PlanRequest(BaseModel):
    scenario_id: str = Field(default="providence_fd", examples=["providence_fd", "toy"])
    security_mode: str | None = Field(
        default=None, description="type_b | type_a | type_ab"
    )
    use_seed: str | None = Field(
        default=None,
        description="Optional: 'opaque' | 'leaky' to evaluate a seeded assignment",
    )
    use_llm: bool = False


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "opaque-convoy-api", "version": "1.0.0"}


@app.get("/scenarios", tags=["scenarios"])
def get_scenarios() -> list[dict[str, Any]]:
    return list_scenarios()


@app.get("/scenarios/{scenario_id}/graph", tags=["scenarios"])
def get_graph(scenario_id: str) -> dict[str, Any]:
    try:
        ts, scenario = load_scenario_graph(scenario_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    nodes = []
    for n in ts.nodes:
        lat, lng = ts.node_coords(n)
        nodes.append(
            {
                "id": n,
                "lat": lat,
                "lng": lng,
                "checkpoint": n in ts.observation.checkpoints,
                "secret": ts.is_secret(n),
            }
        )
    edges = [{"u": u, "v": v, "length": ts.weight(u, v)} for u, v in ts.graph.edges]
    return {
        "scenario_id": scenario_id,
        "nodes": nodes,
        "edges": edges,
        "scenario": scenario,
        "meta": ts.meta,
        "bounds": _bounds(nodes),
        "stats": {
            "n_nodes": len(nodes),
            "n_edges": len(edges),
            "n_checkpoints": len(ts.observation.checkpoints),
            "n_vehicles": len(scenario.get("vehicles", [])),
        },
    }


def _bounds(nodes: list[dict]) -> dict[str, float]:
    if not nodes:
        return {"north": 0, "south": 0, "east": 0, "west": 0}
    lats = [n["lat"] for n in nodes]
    lngs = [n["lng"] for n in nodes]
    return {
        "north": max(lats),
        "south": min(lats),
        "east": max(lngs),
        "west": min(lngs),
    }


@app.post("/plan", tags=["planning"])
def plan(req: PlanRequest) -> dict[str, Any]:
    try:
        ts, scenario = load_scenario_graph(req.scenario_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    task = load_task_spec(req.scenario_id, scenario)
    if req.security_mode:
        task.security_mode = req.security_mode

    seed_paths = None
    if req.use_seed == "opaque" and "seed_opaque" in scenario:
        seed_paths = scenario["seed_opaque"]
    elif req.use_seed == "leaky" and "seed_leaky" in scenario:
        seed_paths = scenario["seed_leaky"]

    result = run_pipeline(ts, task, seed_paths=seed_paths, use_llm=req.use_llm)
    payload = result.to_dict()
    payload["scenario_id"] = req.scenario_id
    payload["task"] = task.to_dict()
    return payload


@app.get("/scenarios/{scenario_id}/tradeoff", tags=["experiments"])
def tradeoff(
    scenario_id: str,
    fractions: str = Query(default="0,0.25,0.5,0.75,1.0"),
) -> dict[str, Any]:
    try:
        ts, scenario = load_scenario_graph(scenario_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    task = load_task_spec(scenario_id, scenario)
    frac_list = [float(x.strip()) for x in fractions.split(",") if x.strip()]
    points = cost_opacity_sweep(ts, task, checkpoint_fractions=frac_list)
    return {
        "scenario_id": scenario_id,
        "points": points,
        "metric": {
            "x": "checkpoint_fraction",
            "y": "overhead_pct",
            "description": "Extra fleet distance (%) vs shortest-path baseline under Type-B",
        },
    }


@app.post("/scenarios/{scenario_id}/check", tags=["planning"])
def check_seed(scenario_id: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
    """Check opacity of provided or seeded paths."""
    try:
        ts, scenario = load_scenario_graph(scenario_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    body = body or {}
    paths = body.get("paths") or scenario.get("seed_opaque")
    mode = body.get("security_mode", scenario.get("security_mode", "type_b"))
    cargo_id = body.get("cargo_id", "cargo")
    verdict = check_opacity(ts, paths, cargo_id, mode=mode)
    return verdict.to_dict()


def create_app() -> FastAPI:
    return app


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
    )
