"""Candidate route generation for cargo + decoy fleet."""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from typing import Any, Hashable

from backend.graph.model import EPSILON, TransitionSystem
from backend.planning.ltl_tasks import TaskSpec
from backend.planning.opacity import assignment_key, check_type_b


@dataclass
class Assignment:
    paths: dict[str, list[Hashable]]
    costs: dict[str, float]
    total_cost: float
    baseline_cost: float
    extra_cost: float
    excluded: bool = False
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "paths": {k: list(v) for k, v in self.paths.items()},
            "costs": self.costs,
            "total_cost": self.total_cost,
            "baseline_cost": self.baseline_cost,
            "extra_cost": self.extra_cost,
            "meta": self.meta,
        }


def _baseline_cost(ts: TransitionSystem, task: TaskSpec) -> float:
    total = 0.0
    for v in task.vehicles:
        try:
            path = ts.shortest_path(v.start, v.goal)
            total += ts.path_cost(path)
        except Exception:
            pass
    return total


def _pad(path: list[Hashable], length: int) -> list[Hashable]:
    if not path:
        return path
    if len(path) >= length:
        return path[:length]
    return path + [path[-1]] * (length - len(path))


def _type_b_violation_count(
    ts: TransitionSystem, paths: dict[str, list[Hashable]], cargo_id: str
) -> int:
    v = check_type_b(ts, paths, cargo_id, cargo_always_secret=True)
    return len(v.failures)


def _decoy_shadow_score(
    ts: TransitionSystem,
    cargo_path: list[Hashable],
    decoy_path: list[Hashable],
) -> int:
    """Higher = more shared checkpoint observations with cargo (aligned by index)."""
    T = max(len(cargo_path), len(decoy_path))
    c = _pad(cargo_path, T)
    d = _pad(decoy_path, T)
    score = 0
    for t in range(T):
        co = ts.observation.observe(c[t])
        if co == EPSILON:
            continue
        if ts.observation.observe(d[t]) == co:
            score += 2
        # bonus if decoy visits same checkpoint sometime
        if co in {ts.observation.observe(n) for n in decoy_path}:
            score += 1
    return score


def _best_decoy_path(
    ts: TransitionSystem,
    start: Hashable,
    goal: Hashable,
    cargo_path: list[Hashable],
    k: int,
) -> list[Hashable]:
    paths = ts.k_shortest_paths(start, goal, k=max(k, 8))
    if not paths:
        return []
    # Also try paths forced through cargo's visible checkpoints
    waypoints = []
    for n in cargo_path:
        o = ts.observation.observe(n)
        if o != EPSILON and n not in waypoints:
            waypoints.append(n)
    forced: list[list[Hashable]] = []
    for wp in waypoints[:4]:
        try:
            p1 = ts.shortest_path(start, wp)
            p2 = ts.shortest_path(wp, goal)
            forced.append(p1[:-1] + p2)
        except Exception:
            continue
    # Two-waypoint chains for stronger shadowing
    for i in range(len(waypoints) - 1):
        a, b = waypoints[i], waypoints[i + 1]
        try:
            p = (
                ts.shortest_path(start, a)[:-1]
                + ts.shortest_path(a, b)[:-1]
                + ts.shortest_path(b, goal)
            )
            forced.append(p)
        except Exception:
            continue

    candidates = paths + forced
    return max(candidates, key=lambda p: (_decoy_shadow_score(ts, cargo_path, p), -ts.path_cost(p)))


def _insert_holds(path: list[Hashable], holds_at_index: dict[int, int]) -> list[Hashable]:
    """Duplicate path[i] holds_at_index[i] extra times (wait in place)."""
    out: list[Hashable] = []
    for i, n in enumerate(path):
        out.append(n)
        for _ in range(holds_at_index.get(i, 0)):
            out.append(n)
    return out


def synchronize_paths_for_type_b(
    ts: TransitionSystem,
    paths: dict[str, list[Hashable]],
    cargo_id: str,
) -> dict[str, list[Hashable]]:
    """Insert waits so a decoy shares each visible cargo observation in time.

    For each timestep where cargo is visible at observation o, if no decoy
    currently matches, pick a decoy that visits o later/earlier and insert
    holds so their visit times coincide.
    """
    synced = {vid: list(p) for vid, p in paths.items()}
    decoy_ids = [vid for vid in synced if vid != cargo_id]
    if not decoy_ids:
        return synced

    # Multiple alignment passes
    for _ in range(12):
        cargo_path = synced[cargo_id]
        T = max(len(p) for p in synced.values())
        aligned = {vid: _pad(p, T) for vid, p in synced.items()}
        fixed = True
        for t in range(T):
            cargo_obs = ts.observation.observe(aligned[cargo_id][t])
            if cargo_obs == EPSILON:
                continue
            if any(
                ts.observation.observe(aligned[d][t]) == cargo_obs for d in decoy_ids
            ):
                continue
            # Find a decoy that hits this observation at some index
            chosen = None
            decoy_t = None
            for d in decoy_ids:
                for j, n in enumerate(synced[d]):
                    if ts.observation.observe(n) == cargo_obs:
                        chosen, decoy_t = d, j
                        break
                if chosen:
                    break
            if chosen is None:
                continue
            # Align: if decoy reaches obs earlier, hold decoy; if later, hold cargo
            if decoy_t < t:
                # hold decoy at decoy_t for (t - decoy_t) steps
                holds = {decoy_t: t - decoy_t}
                synced[chosen] = _insert_holds(synced[chosen], holds)
                fixed = False
                break
            elif decoy_t > t:
                holds = {t: decoy_t - t}
                # hold cargo (and other decoys already matching? just cargo)
                synced[cargo_id] = _insert_holds(synced[cargo_id], holds)
                fixed = False
                break
        if fixed:
            break
    return synced


def generate_coordinated_assignment(
    ts: TransitionSystem,
    task: TaskSpec,
    exclusions: set[tuple] | None = None,
) -> Assignment | None:
    """Build Type-B-aware plans by lockstepping a decoy along the cargo spine."""
    exclusions = exclusions or set()
    cargo = task.cargo
    cargo_paths = ts.k_shortest_paths(cargo.start, cargo.goal, k=task.k_paths)
    if not cargo_paths:
        return None

    baseline = _baseline_cost(ts, task)
    best: Assignment | None = None
    decoys = task.decoys
    if not decoys:
        return None

    for spine in cargo_paths:
        # Primary decoy locksteps the spine
        d0 = decoys[0]
        try:
            prefix = ts.shortest_path(d0.start, spine[0])
            suffix = ts.shortest_path(spine[-1], d0.goal)
        except Exception:
            continue
        hold = len(prefix) - 1
        cargo_synced = [spine[0]] * hold + list(spine)
        decoy0_path = prefix[:-1] + list(spine) + suffix[1:]

        paths: dict[str, list[Hashable]] = {
            cargo.vehicle_id: cargo_synced,
            d0.vehicle_id: decoy0_path,
        }
        ok = True
        for decoy in decoys[1:]:
            mid = spine[len(spine) // 2]
            try:
                p = (
                    ts.shortest_path(decoy.start, spine[0])[:-1]
                    + ts.shortest_path(spine[0], mid)[:-1]
                    + ts.shortest_path(mid, spine[-1])[:-1]
                    + ts.shortest_path(spine[-1], decoy.goal)
                )
            except Exception:
                dp = _best_decoy_path(ts, decoy.start, decoy.goal, spine, task.k_paths)
                if not dp:
                    ok = False
                    break
                p = dp
            paths[decoy.vehicle_id] = p
        if not ok:
            continue

        paths = synchronize_paths_for_type_b(ts, paths, cargo.vehicle_id)
        key = assignment_key(paths)
        if key in exclusions:
            continue
        costs = {vid: ts.path_cost(p) for vid, p in paths.items()}
        total = sum(costs.values())
        viol = _type_b_violation_count(ts, paths, cargo.vehicle_id)
        cand = Assignment(
            paths=paths,
            costs=costs,
            total_cost=total,
            baseline_cost=baseline,
            extra_cost=max(0.0, total - baseline),
            meta={"coordinated": True, "type_b_violations": viol},
        )
        if best is None or (viol, total) < (
            best.meta.get("type_b_violations", 99),
            best.total_cost,
        ):
            best = cand
            if viol == 0:
                return best

    return best


def generate_assignment(
    ts: TransitionSystem,
    task: TaskSpec,
    exclusions: set[tuple] | None = None,
    *,
    prefer_opaque_hint: bool = True,
) -> Assignment | None:
    """Next joint path assignment not in exclusions.

    Tries coordinated (Type-B-aware) generation first, then falls back to
    Cartesian product of k-shortest paths ordered by cost then violations.
    """
    exclusions = exclusions or set()

    if prefer_opaque_hint and task.security_mode.lower() in (
        "type_b",
        "type_ab",
        "b",
        "ab",
    ):
        # Try several coordinated variants by excluding previous bests
        coord = generate_coordinated_assignment(ts, task, exclusions)
        if coord is not None:
            return coord

    per_vehicle: dict[str, list[list[Hashable]]] = {}
    for v in task.vehicles:
        paths = ts.k_shortest_paths(v.start, v.goal, k=task.k_paths)
        if not paths:
            return None
        per_vehicle[v.vehicle_id] = paths

    vehicle_ids = [v.vehicle_id for v in task.vehicles]
    path_lists = [per_vehicle[vid] for vid in vehicle_ids]
    baseline = _baseline_cost(ts, task)
    cargo_id = task.cargo.vehicle_id

    candidates: list[Assignment] = []
    for combo in itertools.product(*path_lists):
        paths = {vid: list(combo[i]) for i, vid in enumerate(vehicle_ids)}
        key = assignment_key(paths)
        if key in exclusions:
            continue
        costs = {vid: ts.path_cost(p) for vid, p in paths.items()}
        total = sum(costs.values())
        viol = _type_b_violation_count(ts, paths, cargo_id)
        candidates.append(
            Assignment(
                paths=paths,
                costs=costs,
                total_cost=total,
                baseline_cost=baseline,
                extra_cost=max(0.0, total - baseline),
                meta={"type_b_violations": viol},
            )
        )

    if not candidates:
        return None

    candidates.sort(key=lambda a: (a.meta.get("type_b_violations", 99), a.total_cost))
    return candidates[0]


def all_assignments(
    ts: TransitionSystem,
    task: TaskSpec,
    limit: int = 50,
) -> list[Assignment]:
    """Enumerate up to `limit` assignments sorted by security then cost."""
    exclusions: set[tuple] = set()
    results: list[Assignment] = []
    for _ in range(limit):
        a = generate_assignment(ts, task, exclusions)
        if a is None:
            break
        exclusions.add(assignment_key(a.paths))
        results.append(a)
    return results
