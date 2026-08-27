"""LangGraph planning pipeline: Planner → OpacityChecker → Refiner → Explainer."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Hashable, Literal, TypedDict

from backend.graph.model import TransitionSystem
from backend.planning.ltl_tasks import TaskSpec
from backend.planning.opacity import (
    OpacityVerdict,
    assignment_key,
    check_opacity,
)
from backend.planning.planner import Assignment, generate_assignment
from backend.planning.refine import refine_routes


class PipelineState(TypedDict, total=False):
    iteration: int
    exclusions: list  # list of assignment keys (as lists for JSON-friendliness)
    assignment: dict[str, Any] | None
    verdict: dict[str, Any] | None
    trajectories: list[dict[str, Any]]
    explanation: str
    status: str
    failures_log: list[str]


@dataclass
class PipelineResult:
    status: str
    opaque: bool
    assignment: Assignment | None
    verdict: OpacityVerdict | None
    trajectories: list[dict[str, Any]]
    explanation: str
    iterations: int
    failures_log: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "opaque": self.opaque,
            "assignment": self.assignment.to_dict() if self.assignment else None,
            "verdict": self.verdict.to_dict() if self.verdict else None,
            "trajectories": self.trajectories,
            "explanation": self.explanation,
            "iterations": self.iterations,
            "failures_log": self.failures_log,
        }


def _template_explanation(
    task: TaskSpec,
    verdict: OpacityVerdict | None,
    assignment: Assignment | None,
    iterations: int,
) -> str:
    if verdict is None or assignment is None:
        return (
            "No secure assignment found within the replan budget. "
            "Try fewer checkpoints or more decoy path diversity."
        )
    mode = task.security_mode
    extra_pct = (
        100.0 * assignment.extra_cost / assignment.baseline_cost
        if assignment.baseline_cost > 0
        else 0.0
    )
    if verdict.opaque:
        return (
            f"Found a {mode.replace('_', '-')} secure convoy plan after {iterations} "
            f"planner iteration(s). Total fleet distance is {assignment.total_cost:.0f} m "
            f"({extra_pct:.1f}% above the shortest-path baseline of "
            f"{assignment.baseline_cost:.0f} m). "
            f"At every observed checkpoint where the cargo vehicle is visible, "
            f"at least one decoy produces the same observation, so a passive "
            f"camera observer cannot uniquely identify the cargo carrier."
        )
    return (
        f"Security check failed under {mode}: "
        + "; ".join(verdict.failures[:3])
        + ("…" if len(verdict.failures) > 3 else "")
    )


def _llm_explanation(template: str, verdict: OpacityVerdict | None) -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return template
    try:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)
        prompt = (
            "You explain secure convoy routing to a technical audience in 3-4 sentences. "
            "Do not invent formal claims beyond the facts given.\n\n"
            f"Base summary:\n{template}\n\n"
            f"Verdict JSON:\n{verdict.to_dict() if verdict else {}}"
        )
        msg = client.messages.create(
            model="claude-3-5-haiku-latest",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(
            block.text for block in msg.content if getattr(block, "type", "") == "text"
        )
        return text.strip() or template
    except Exception:
        return template


def run_pipeline(
    ts: TransitionSystem,
    task: TaskSpec,
    *,
    seed_paths: dict[str, list[Hashable]] | None = None,
    use_llm: bool = True,
) -> PipelineResult:
    """Run Planner → OpacityChecker loop, then refine + explain.

    Uses LangGraph when available; falls back to an equivalent imperative loop.
    """
    roles = {v.vehicle_id: v.role for v in task.vehicles}
    cargo_id = task.cargo.vehicle_id
    exclusions: set[tuple] = set()
    failures_log: list[str] = []
    last_verdict: OpacityVerdict | None = None
    last_assignment: Assignment | None = None

    # Optional: evaluate a seed first
    if seed_paths:
        last_verdict = check_opacity(
            ts,
            seed_paths,
            cargo_id,
            mode=task.security_mode,
            cargo_always_secret=task.cargo_always_secret,
        )
        costs = {vid: ts.path_cost(p) for vid, p in seed_paths.items()}
        baseline = sum(
            ts.path_cost(ts.shortest_path(v.start, v.goal)) for v in task.vehicles
        )
        total = sum(costs.values())
        last_assignment = Assignment(
            paths=seed_paths,
            costs=costs,
            total_cost=total,
            baseline_cost=baseline,
            extra_cost=max(0.0, total - baseline),
            meta={"seeded": True},
        )
        traj = refine_routes(ts, seed_paths, roles)
        expl = _template_explanation(task, last_verdict, last_assignment, 0)
        if use_llm:
            expl = _llm_explanation(expl, last_verdict)
        # Always return seeded assignments for demo (opaque or leaky)
        return PipelineResult(
            status="ok" if last_verdict.opaque else "leaky",
            opaque=last_verdict.opaque,
            assignment=last_assignment,
            verdict=last_verdict,
            trajectories=traj,
            explanation=expl,
            iterations=0,
        )

    def _imperative() -> PipelineResult:
        nonlocal last_verdict, last_assignment
        for i in range(1, task.max_replan + 1):
            assignment = generate_assignment(ts, task, exclusions)
            if assignment is None:
                break
            last_assignment = assignment
            verdict = check_opacity(
                ts,
                assignment.paths,
                cargo_id,
                mode=task.security_mode,
                cargo_always_secret=task.cargo_always_secret,
            )
            last_verdict = verdict
            if verdict.opaque:
                traj = refine_routes(ts, assignment.paths, roles)
                expl = _template_explanation(task, verdict, assignment, i)
                if use_llm:
                    expl = _llm_explanation(expl, verdict)
                return PipelineResult(
                    status="ok",
                    opaque=True,
                    assignment=assignment,
                    verdict=verdict,
                    trajectories=traj,
                    explanation=expl,
                    iterations=i,
                    failures_log=failures_log,
                )
            exclusions.add(assignment_key(assignment.paths))
            failures_log.extend(verdict.failures[:2])

        expl = _template_explanation(task, last_verdict, last_assignment, task.max_replan)
        traj = (
            refine_routes(ts, last_assignment.paths, roles) if last_assignment else []
        )
        return PipelineResult(
            status="failed",
            opaque=False,
            assignment=last_assignment,
            verdict=last_verdict,
            trajectories=traj,
            explanation=expl,
            iterations=task.max_replan,
            failures_log=failures_log,
        )

    # Prefer LangGraph state machine when importable
    try:
        return _run_langgraph(
            ts, task, exclusions, failures_log, roles, cargo_id, use_llm
        )
    except Exception:
        return _imperative()


def _run_langgraph(
    ts: TransitionSystem,
    task: TaskSpec,
    exclusions: set[tuple],
    failures_log: list[str],
    roles: dict[str, str],
    cargo_id: str,
    use_llm: bool,
) -> PipelineResult:
    from langgraph.graph import END, StateGraph

    state: dict[str, Any] = {
        "iteration": 0,
        "exclusions": [],
        "assignment": None,
        "verdict": None,
        "trajectories": [],
        "explanation": "",
        "status": "running",
        "failures_log": list(failures_log),
        "_excl": set(exclusions),
        "_last_assignment": None,
        "_last_verdict": None,
    }

    def planner_node(s: dict) -> dict:
        excl = s.get("_excl", set())
        assignment = generate_assignment(ts, task, excl)
        s["iteration"] = int(s.get("iteration", 0)) + 1
        if assignment is None:
            s["status"] = "exhausted"
            s["assignment"] = None
            return s
        s["_last_assignment"] = assignment
        s["assignment"] = assignment.to_dict()
        return s

    def opacity_node(s: dict) -> dict:
        assignment: Assignment | None = s.get("_last_assignment")
        if assignment is None:
            s["status"] = "failed"
            return s
        verdict = check_opacity(
            ts,
            assignment.paths,
            cargo_id,
            mode=task.security_mode,
            cargo_always_secret=task.cargo_always_secret,
        )
        s["_last_verdict"] = verdict
        s["verdict"] = verdict.to_dict()
        if not verdict.opaque:
            excl = s.get("_excl", set())
            excl.add(assignment_key(assignment.paths))
            s["_excl"] = excl
            fl = list(s.get("failures_log", []))
            fl.extend(verdict.failures[:2])
            s["failures_log"] = fl
            s["status"] = "replan"
        else:
            s["status"] = "pass"
        return s

    def refine_node(s: dict) -> dict:
        assignment: Assignment | None = s.get("_last_assignment")
        if assignment:
            s["trajectories"] = refine_routes(ts, assignment.paths, roles)
        s["status"] = "ok"
        return s

    def explain_node(s: dict) -> dict:
        assignment = s.get("_last_assignment")
        verdict = s.get("_last_verdict")
        expl = _template_explanation(
            task, verdict, assignment, int(s.get("iteration", 0))
        )
        if use_llm:
            expl = _llm_explanation(expl, verdict)
        s["explanation"] = expl
        return s

    def route_after_opacity(s: dict) -> Literal["refine", "planner", "end"]:
        if s.get("status") == "pass":
            return "refine"
        if s.get("status") == "exhausted":
            return "end"
        if int(s.get("iteration", 0)) >= task.max_replan:
            return "end"
        return "planner"

    g = StateGraph(dict)
    g.add_node("planner", planner_node)
    g.add_node("opacity", opacity_node)
    g.add_node("refine", refine_node)
    g.add_node("explain", explain_node)
    g.set_entry_point("planner")
    g.add_edge("planner", "opacity")
    g.add_conditional_edges(
        "opacity",
        route_after_opacity,
        {"refine": "refine", "planner": "planner", "end": "explain"},
    )
    g.add_edge("refine", "explain")
    g.add_edge("explain", END)

    app = g.compile()
    final = app.invoke(state)

    assignment = final.get("_last_assignment")
    verdict = final.get("_last_verdict")
    opaque = bool(verdict and verdict.opaque)
    status = "ok" if opaque else "failed"
    if not final.get("explanation"):
        final["explanation"] = _template_explanation(
            task, verdict, assignment, int(final.get("iteration", 0))
        )
    # If we ended without refine, still produce trajectories for last attempt
    traj = final.get("trajectories") or []
    if not traj and assignment:
        traj = refine_routes(ts, assignment.paths, roles)

    return PipelineResult(
        status=status,
        opaque=opaque,
        assignment=assignment,
        verdict=verdict,
        trajectories=traj,
        explanation=final.get("explanation", ""),
        iterations=int(final.get("iteration", 0)),
        failures_log=list(final.get("failures_log", [])),
    )
