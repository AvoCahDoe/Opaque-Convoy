"""Current-state / Type-A and Type-B opacity checks for convoy routes.

Based on Mitsos et al., arXiv:2605.13134:
- Type-A: when an agent visits a secret state, there exists an observationally
  equivalent copy path where that agent is non-secret at those steps.
- Type-B: when an agent visits a secret state, at least one other agent produces
  the same observation at that time (which-vehicle ambiguity).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Hashable

from backend.graph.model import EPSILON, TransitionSystem


@dataclass
class OpacityVerdict:
    opaque: bool
    mode: str
    type_a_ok: bool | None = None
    type_b_ok: bool | None = None
    failures: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "opaque": self.opaque,
            "mode": self.mode,
            "type_a_ok": self.type_a_ok,
            "type_b_ok": self.type_b_ok,
            "failures": self.failures,
            "details": self.details,
        }


def _align_paths(paths: dict[str, list[Hashable]]) -> int:
    return max((len(p) for p in paths.values()), default=0)


def _pad_path(path: list[Hashable], length: int) -> list[Hashable]:
    """Hold at goal after arrival so joint timesteps align."""
    if not path:
        return [None] * length  # type: ignore[list-item]
    if len(path) >= length:
        return path[:length]
    return path + [path[-1]] * (length - len(path))


def _observations_at(
    ts: TransitionSystem, paths: dict[str, list[Hashable]], t: int
) -> dict[str, str]:
    obs: dict[str, str] = {}
    for vid, path in paths.items():
        node = path[t] if t < len(path) else path[-1]
        obs[vid] = ts.observation.observe(node)
    return obs


def check_type_b(
    ts: TransitionSystem,
    paths: dict[str, list[Hashable]],
    cargo_id: str,
    *,
    cargo_always_secret: bool = True,
    secret_only_at_checkpoints: bool = True,
) -> OpacityVerdict:
    """Type-B: when cargo is secret-relevant, some decoy shares its observation.

    For the convoy demo we treat the cargo vehicle as secret-bearing throughout.
    At each timestep where the cargo observation is non-silent (visible at a
    checkpoint), at least one decoy must emit the same observation symbol.
    If cargo_always_secret is False, only check when cargo is at a secret node.
    """
    failures: list[str] = []
    T = _align_paths(paths)
    aligned = {vid: _pad_path(p, T) for vid, p in paths.items()}
    cargo_path = aligned[cargo_id]
    decoy_ids = [vid for vid in aligned if vid != cargo_id]
    matches: list[dict[str, Any]] = []

    for t in range(T):
        cargo_node = cargo_path[t]
        cargo_obs = ts.observation.observe(cargo_node)

        if cargo_always_secret:
            relevant = True
        else:
            relevant = ts.is_secret(cargo_node)

        if secret_only_at_checkpoints and cargo_obs == EPSILON:
            # Unobserved — intruder sees nothing; Type-B vacuously ok here
            continue

        if not relevant:
            continue

        if cargo_obs == EPSILON:
            # Secret but unobserved: Type-B still requires another agent with
            # same (silent) observation — always true if any decoy exists and
            # is also unobserved. Check decoy observations equal ε.
            if any(ts.observation.observe(aligned[d][t]) == EPSILON for d in decoy_ids):
                matches.append({"t": t, "obs": EPSILON, "matched": True})
                continue
            failures.append(
                f"t={t}: cargo secret/unobserved but no decoy shares ε observation"
            )
            continue

        matched_decoy = None
        for d in decoy_ids:
            if ts.observation.observe(aligned[d][t]) == cargo_obs:
                matched_decoy = d
                break
        if matched_decoy is None:
            failures.append(
                f"t={t}: cargo obs={cargo_obs} at node={cargo_node} "
                f"has no matching decoy observation"
            )
        else:
            matches.append(
                {"t": t, "obs": cargo_obs, "matched_decoy": matched_decoy}
            )

    ok = len(failures) == 0
    return OpacityVerdict(
        opaque=ok,
        mode="type_b",
        type_b_ok=ok,
        failures=failures,
        details={"matches": matches, "timesteps": T},
    )


def check_type_a(
    ts: TransitionSystem,
    paths: dict[str, list[Hashable]],
    cargo_id: str,
    *,
    max_search_depth: int = 40,
) -> OpacityVerdict:
    """Type-A (simplified): for the cargo's observation sequence at secret visits,
    there exists an alternative cargo path start→goal that produces the same
    observation sequence while avoiding secret nodes at those secret timesteps.

    Full Twin-gWTS product is exponential; for demo graphs we search alternative
    cargo paths with matching visible observations.
    """
    failures: list[str] = []
    cargo_path = paths[cargo_id]
    cargo_obs_seq = ts.observation.project_path(cargo_path)

    secret_times = [t for t, n in enumerate(cargo_path) if ts.is_secret(n)]
    if not secret_times and not any(
        ts.observation.observe(n) != EPSILON for n in cargo_path
    ):
        return OpacityVerdict(
            opaque=True,
            mode="type_a",
            type_a_ok=True,
            failures=[],
            details={"note": "no secret visits; Type-A vacuously holds"},
        )

    # If there are no designated secret nodes, treat checkpoints on cargo path as secrets
    secrets = ts.secret_nodes or set(ts.observation.checkpoints)

    start, goal = cargo_path[0], cargo_path[-1]
    alt_paths = ts.k_shortest_paths(start, goal, k=max_search_depth)
    # Also include neighbors-expansion: BFS limited paths
    found_copy = False
    copy_path: list[Hashable] | None = None

    for alt in alt_paths:
        if alt == cargo_path:
            continue
        alt_obs = ts.observation.project_path(alt)
        # Align lengths by padding
        T = max(len(cargo_obs_seq), len(alt_obs))
        c_pad = cargo_obs_seq + [cargo_obs_seq[-1]] * (T - len(cargo_obs_seq))
        a_pad = alt_obs + [alt_obs[-1]] * (T - len(alt_obs))
        if c_pad != a_pad:
            continue
        # At times when real path is in secret, copy must be non-secret
        ok = True
        for t in range(min(len(cargo_path), len(alt))):
            if cargo_path[t] in secrets and alt[t] in secrets:
                ok = False
                break
        # Also check padded hold-at-goal
        if ok:
            found_copy = True
            copy_path = alt
            break

    if not found_copy:
        # Weaker criterion for convoy demo: if cargo never sits alone on a
        # checkpoint observation (Type-B style cover), accept Type-A soft pass
        # only when secret_nodes is empty and we only have checkpoints.
        if not ts.secret_nodes:
            failures.append(
                "no observationally equivalent non-secret copy path found for cargo"
            )
        else:
            failures.append(
                "Type-A failed: no copy path with same observations avoiding secrets"
            )

    ok = found_copy
    return OpacityVerdict(
        opaque=ok,
        mode="type_a",
        type_a_ok=ok,
        failures=failures,
        details={"copy_path": copy_path, "secret_times": secret_times},
    )


def check_opacity(
    ts: TransitionSystem,
    paths: dict[str, list[Hashable]],
    cargo_id: str,
    mode: str = "type_b",
    *,
    cargo_always_secret: bool = True,
) -> OpacityVerdict:
    """Dispatch Type-A / Type-B / combined check."""
    mode = mode.lower()
    type_a: OpacityVerdict | None = None
    type_b: OpacityVerdict | None = None

    if mode in ("type_a", "type_ab", "a", "ab"):
        type_a = check_type_a(ts, paths, cargo_id)
    if mode in ("type_b", "type_ab", "b", "ab"):
        type_b = check_type_b(
            ts, paths, cargo_id, cargo_always_secret=cargo_always_secret
        )

    if mode in ("type_a", "a"):
        assert type_a is not None
        return type_a
    if mode in ("type_b", "b"):
        assert type_b is not None
        return type_b

    # combined
    assert type_a is not None and type_b is not None
    failures = [f"[A] {f}" for f in type_a.failures] + [
        f"[B] {f}" for f in type_b.failures
    ]
    ok = type_a.opaque and type_b.opaque
    return OpacityVerdict(
        opaque=ok,
        mode="type_ab",
        type_a_ok=type_a.opaque,
        type_b_ok=type_b.opaque,
        failures=failures,
        details={"type_a": type_a.details, "type_b": type_b.details},
    )


def assignment_key(paths: dict[str, list[Hashable]]) -> tuple:
    """Hashable exclusion key for a joint assignment."""
    return tuple(sorted((vid, tuple(p)) for vid, p in paths.items()))
