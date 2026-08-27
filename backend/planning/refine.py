"""Discrete node routes → timed lat/lng trajectories."""

from __future__ import annotations

from typing import Any, Hashable

from backend.graph.model import TransitionSystem


DEFAULT_SPEED_MPS = 8.0  # ~29 km/h urban convoy pace


def refine_route(
    ts: TransitionSystem,
    path: list[Hashable],
    *,
    speed_mps: float = DEFAULT_SPEED_MPS,
    vehicle_id: str = "",
    role: str = "",
) -> dict[str, Any]:
    """Interpolate a discrete path into a timed polyline."""
    if not path:
        return {
            "vehicle_id": vehicle_id,
            "role": role,
            "nodes": [],
            "waypoints": [],
            "duration_s": 0.0,
            "distance_m": 0.0,
        }

    waypoints: list[dict[str, float]] = []
    t = 0.0
    lat0, lng0 = ts.node_coords(path[0])
    waypoints.append({"lat": lat0, "lng": lng0, "t": 0.0, "node": path[0]})

    for i in range(len(path) - 1):
        u, v = path[i], path[i + 1]
        if u == v:
            # wait-in-place: small dwell time
            t += 5.0
            waypoints.append(
                {"lat": waypoints[-1]["lat"], "lng": waypoints[-1]["lng"], "t": t, "node": v}
            )
            continue
        length = ts.weight(u, v)
        dt = length / max(speed_mps, 0.1)
        t += dt
        lat, lng = ts.node_coords(v)
        waypoints.append({"lat": lat, "lng": lng, "t": t, "node": v})

    return {
        "vehicle_id": vehicle_id,
        "role": role,
        "nodes": list(path),
        "waypoints": waypoints,
        "duration_s": t,
        "distance_m": ts.path_cost(path),
    }


def refine_routes(
    ts: TransitionSystem,
    paths: dict[str, list[Hashable]],
    roles: dict[str, str] | None = None,
    *,
    speed_mps: float = DEFAULT_SPEED_MPS,
) -> list[dict[str, Any]]:
    roles = roles or {}
    return [
        refine_route(
            ts,
            path,
            speed_mps=speed_mps,
            vehicle_id=vid,
            role=roles.get(vid, ""),
        )
        for vid, path in paths.items()
    ]
