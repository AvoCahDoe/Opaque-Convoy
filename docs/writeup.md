# Opaque Convoy — Technical Note

## Problem

Cash-in-transit and high-value convoy operators want routes where a passive observer—who sees vehicles only at public checkpoints (cameras, toll gates)—cannot infer **which** vehicle carries the valuable cargo. Ad-hoc decoys help; this project makes the guarantee explicit and measures its travel-cost overhead.

## Security notions (arXiv:2605.13134)

We follow Mitsos, Dimarogonas, and Liu, *Security-Aware Planning and Control of Multi-Agent Systems with LTL Tasks* (arXiv:2605.13134).

Each agent moves on a finite weighted transition system abstracted from a street graph. An observation map \(H\) returns a checkpoint id at observed nodes and \(\varepsilon\) (silent) elsewhere.

**Type-B security (primary convoy guarantee).** Whenever the cargo vehicle is in a secret-relevant context at time \(j\) and emits a non-silent observation \(y\), there exists another vehicle \(k\) with \(H_k(j) = y\). The intruder therefore cannot uniquely attribute the observed presence to the cargo carrier.

**Type-A security (also implemented).** When an agent visits a secret state, there must exist an observationally equivalent copy path on which that agent is non-secret at those steps—linking to classical current-state opacity.

Type-B is the default in the demo because the product claim is *which-vehicle* ambiguity, not merely *whether* a secret region was visited.

## Pipeline

1. **Planner** — generate cargo routes (k-shortest) and lockstep a decoy along the cargo spine through shared checkpoints; remaining decoys cover mid-corridor waypoints. Failed assignments are excluded and the planner retries.
2. **OpacityChecker** — evaluate Type-B (and optionally Type-A) on the joint discrete paths.
3. **TrajectoryRefiner** — convert node sequences to timed lat/lng polylines (constant urban speed; wait-in-place holds for temporal alignment).
4. **Explainer** — template summary; optional Anthropic Claude rewrite if `ANTHROPIC_API_KEY` is set.

Orchestration uses a LangGraph state machine (`Planner → OpacityChecker ⇄ replan → Refiner → Explainer`) with an imperative fallback.

## Cost–opacity trade-off

Sweeping checkpoint density and re-planning under Type-B yields a curve of **extra fleet distance vs. shortest-path baseline**. Sparse cameras are cheap to satisfy; denser observers force longer coordinated detours or synchronized waits.

## What this adds beyond the paper

- Application to **real street-graph routing** (OSMnx-ready cache; Providence FD demo district).
- **Quantified security–cost trade-off** for a non-specialist audience.
- Interactive **observer view** that hides cargo identity and only shows vehicles at checkpoints.

## Natural next steps

- Continuous dynamics / double-integrator refinement (paper’s open direction).
- Full Twin-gWTS construction for Type-A at larger agent counts.
- Multiple live observer models (sparse cameras vs dense mesh) as UI presets.

## Citation

> Mitsos, G., Dimarogonas, D. V., & Liu, S. (2026). Security-Aware Planning and Control of Multi-Agent Systems with LTL Tasks. arXiv:2605.13134.
