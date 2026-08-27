"""Cost vs opacity (checkpoint density) sweep experiment."""

from __future__ import annotations

from typing import Any

from backend.graph.model import ObservationMap, TransitionSystem
from backend.planning.ltl_tasks import TaskSpec
from backend.planning.opacity import check_opacity
from backend.planning.planner import all_assignments
from backend.pipeline.graph_pipeline import run_pipeline


def cost_opacity_sweep(
    ts: TransitionSystem,
    task: TaskSpec,
    *,
    checkpoint_fractions: list[float] | None = None,
    candidate_checkpoints: list | None = None,
) -> list[dict[str, Any]]:
    """Sweep observer checkpoint density; record extra cost of secure plans.

    For each fraction f of candidate checkpoints enabled, run the pipeline and
    record whether a Type-B secure plan was found and its cost overhead.
    """
    checkpoint_fractions = checkpoint_fractions or [0.0, 0.25, 0.5, 0.75, 1.0]
    candidates = list(candidate_checkpoints or task.checkpoints or list(ts.observation.checkpoints))
    if not candidates:
        # fall back to a sampling of nodes
        candidates = list(ts.nodes)[:: max(1, len(ts.nodes) // 12)][:12]

    baseline_assignments = all_assignments(ts, task, limit=1)
    baseline_cost = (
        baseline_assignments[0].baseline_cost if baseline_assignments else 0.0
    )

    results: list[dict[str, Any]] = []
    n = len(candidates)

    for frac in checkpoint_fractions:
        k = max(0, int(round(frac * n)))
        active = set(candidates[:k]) if k else set()

        # Temporarily swap observation map
        original_obs = ts.observation
        ts.observation = ObservationMap(checkpoints=active, zone_of=dict(original_obs.zone_of))

        # Also update task checkpoints for clarity
        task_copy_checkpoints = list(active)
        original_cp = task.checkpoints
        task.checkpoints = task_copy_checkpoints

        result = run_pipeline(ts, task, use_llm=False)

        # Evaluate shortest (insecure) assignment opacity under this observer
        insecure = baseline_assignments[0] if baseline_assignments else None
        insecure_opaque = False
        if insecure:
            v = check_opacity(
                ts,
                insecure.paths,
                task.cargo.vehicle_id,
                mode=task.security_mode,
                cargo_always_secret=task.cargo_always_secret,
            )
            insecure_opaque = v.opaque

        total = result.assignment.total_cost if result.assignment else None
        extra = result.assignment.extra_cost if result.assignment else None
        overhead_pct = (
            100.0 * extra / baseline_cost if (extra is not None and baseline_cost > 0) else None
        )

        results.append(
            {
                "checkpoint_fraction": frac,
                "n_checkpoints": len(active),
                "checkpoints": [str(c) for c in sorted(active, key=str)],
                "secure_found": result.opaque,
                "total_cost_m": total,
                "baseline_cost_m": baseline_cost,
                "extra_cost_m": extra,
                "overhead_pct": overhead_pct,
                "shortest_already_opaque": insecure_opaque,
                "iterations": result.iterations,
            }
        )

        ts.observation = original_obs
        task.checkpoints = original_cp

    return results
