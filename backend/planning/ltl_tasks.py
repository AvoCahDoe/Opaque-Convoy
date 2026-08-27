"""Hardcoded LTL-style reachability task specs for cargo + decoys."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Hashable


@dataclass
class VehicleTask:
    vehicle_id: str
    role: str  # "cargo" | "decoy"
    start: Hashable
    goal: Hashable
    # Atomic propositions satisfied along the route (informational)
    formula: str = ""


@dataclass
class TaskSpec:
    """Scenario task: one cargo + N decoys with reachability LTL."""

    scenario_id: str
    vehicles: list[VehicleTask]
    checkpoints: list[Hashable] = field(default_factory=list)
    secret_nodes: list[Hashable] = field(default_factory=list)
    security_mode: str = "type_b"  # "type_a" | "type_b" | "type_ab"
    # Cargo is considered "secret carrier" for the whole trip (Type-B framing)
    cargo_always_secret: bool = True
    max_replan: int = 12
    k_paths: int = 6

    @property
    def cargo(self) -> VehicleTask:
        for v in self.vehicles:
            if v.role == "cargo":
                return v
        raise ValueError("No cargo vehicle in task spec")

    @property
    def decoys(self) -> list[VehicleTask]:
        return [v for v in self.vehicles if v.role == "decoy"]

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "vehicles": [
                {
                    "vehicle_id": v.vehicle_id,
                    "role": v.role,
                    "start": v.start,
                    "goal": v.goal,
                    "formula": v.formula,
                }
                for v in self.vehicles
            ],
            "checkpoints": list(self.checkpoints),
            "secret_nodes": list(self.secret_nodes),
            "security_mode": self.security_mode,
            "cargo_always_secret": self.cargo_always_secret,
            "max_replan": self.max_replan,
            "k_paths": self.k_paths,
        }


def _reachability_ltl(start_label: str, goal_label: str) -> str:
    """◇ goal ∧ □(start → ◇ goal) style informal formula string."""
    return f"◇{goal_label}  (reachability from {start_label})"


def load_task_spec(scenario_id: str, scenario: dict[str, Any]) -> TaskSpec:
    """Build TaskSpec from scenario.json content."""
    vehicles: list[VehicleTask] = []
    for v in scenario.get("vehicles", []):
        role = v["role"]
        start, goal = v["start"], v["goal"]
        label_start = v.get("start_label", "start")
        label_goal = v.get("goal_label", "goal")
        vehicles.append(
            VehicleTask(
                vehicle_id=v["id"],
                role=role,
                start=start,
                goal=goal,
                formula=_reachability_ltl(label_start, label_goal),
            )
        )
    return TaskSpec(
        scenario_id=scenario_id,
        vehicles=vehicles,
        checkpoints=list(scenario.get("checkpoints", [])),
        secret_nodes=list(scenario.get("secret_nodes", [])),
        security_mode=scenario.get("security_mode", "type_b"),
        cargo_always_secret=bool(scenario.get("cargo_always_secret", True)),
        max_replan=int(scenario.get("max_replan", 12)),
        k_paths=int(scenario.get("k_paths", 6)),
    )
