"""Unit tests for Type-A / Type-B opacity on the toy grid."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from backend.graph.load_osm import load_scenario_graph
from backend.planning.opacity import check_type_a, check_type_b, check_opacity
from backend.planning.planner import generate_assignment
from backend.planning.ltl_tasks import load_task_spec
from backend.scripts.write_toy_scenario import write_toy_scenario


@pytest.fixture(scope="module")
def toy():
    write_toy_scenario()
    ts, scenario = load_scenario_graph("toy")
    task = load_task_spec("toy", scenario)
    return ts, scenario, task


def test_type_b_opaque_seed(toy):
    ts, scenario, _ = toy
    paths = scenario["seed_opaque"]
    verdict = check_type_b(ts, paths, "cargo", cargo_always_secret=True)
    assert verdict.opaque, verdict.failures


def test_type_b_leaky_seed(toy):
    ts, scenario, _ = toy
    paths = scenario["seed_leaky"]
    verdict = check_type_b(ts, paths, "cargo", cargo_always_secret=True)
    assert not verdict.opaque
    assert len(verdict.failures) > 0


def test_check_opacity_dispatch(toy):
    ts, scenario, _ = toy
    paths = scenario["seed_opaque"]
    v = check_opacity(ts, paths, "cargo", mode="type_b")
    assert v.opaque
    assert v.type_b_ok is True


def test_planner_returns_assignment(toy):
    ts, _, task = toy
    a = generate_assignment(ts, task, exclusions=set())
    assert a is not None
    assert "cargo" in a.paths
    assert a.total_cost > 0


def test_type_a_runs(toy):
    ts, scenario, _ = toy
    paths = scenario["seed_opaque"]
    # Type-A may or may not pass depending on copy paths; just ensure it runs
    verdict = check_type_a(ts, paths, "cargo")
    assert verdict.mode == "type_a"
    assert isinstance(verdict.opaque, bool)
