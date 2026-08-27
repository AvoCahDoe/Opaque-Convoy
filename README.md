# Opaque Convoy

[![License: MIT](https://img.shields.io/badge/License-MIT-steelblue.svg)](LICENSE)
[![arXiv](https://img.shields.io/badge/arXiv-2605.13134-b31b1b.svg)](https://arxiv.org/abs/2605.13134)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![React](https://img.shields.io/badge/frontend-React%20%2B%20Leaflet-61dafb.svg)](frontend/)
[![FastAPI](https://img.shields.io/badge/backend-FastAPI-009688.svg)](backend/)

**Provably secure route planning for high-value transport** — plan cargo + decoy routes so a checkpoint observer cannot tell which vehicle carries the cargo, with a live map demo and a cost-vs-opacity trade-off.

Based on Type-A / Type-B security from Mitsos et al., [*Security-Aware Planning and Control of Multi-Agent Systems with LTL Tasks*](https://arxiv.org/abs/2605.13134) (arXiv:2605.13134). See [docs/writeup.md](docs/writeup.md) and [CITATION.cff](CITATION.cff).

| | |
|---|---|
| **Author** | Farid El Boubkraoui \<farid.elboubkraoui@w-ays.de\> |
| **Repository** | [AvoCahDoe/Opaque-Convoy](https://github.com/AvoCahDoe/Opaque-Convoy) |
| **License** | MIT |
| **Version** | 1.0.0 |

## Features

- **Type-B opacity** (primary): which-vehicle ambiguity at camera checkpoints
- **Type-A** checker for writeup fidelity (current-state opacity link)
- **LangGraph** Planner → OpacityChecker → replan → TrajectoryRefiner → Explainer
- **OSMnx / NetworkX** road graphs (cached Providence FD + toy grid; OSM rebuild script)
- **React + Leaflet** God / Observer views, route playback, Recharts trade-off curve

## Quick start

### Backend

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r backend/requirements.txt
python backend/scripts/write_toy_scenario.py
python backend/scripts/build_scenario.py --no-osm

# From repo root
export PYTHONPATH=.   # Windows: set PYTHONPATH=.
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

API docs: `http://127.0.0.1:8000/docs`

### Frontend

```bash
cd frontend
cp .env.example .env   # VITE_API_URL=http://127.0.0.1:8000
npm install
npm run dev
```

Open `http://127.0.0.1:5173`. The demo auto-loads an opaque plan; use **Load leaky** / **Plan**, toggle **Observer**, and press **Play**.

### Optional OSM refresh

```bash
pip install osmnx
PYTHONPATH=. python backend/scripts/build_scenario.py   # downloads Providence bbox
```

## Live demo

| Layer | URL |
|---|---|
| Frontend (Vercel) | https://opaque-convoy.vercel.app |
| Backend API (Render) | https://opaque-convoy.onrender.com |
| API docs | https://opaque-convoy.onrender.com/docs |
| Source | https://github.com/AvoCahDoe/Opaque-Convoy |

> Free Render services spin down after ~15 minutes idle; the first request after sleep can take ~30–60s.

## Project layout

```
backend/          FastAPI + LangGraph planning pipeline
frontend/         React (Vite) + Leaflet map demo
data/scenarios/   Cached graphs (toy, Providence FD)
docs/writeup.md   Technical note + citation
CITATION.cff      Citation metadata
```

## Citation

```bibtex
@software{opaque_convoy_2026,
  author = {El Boubkraoui, Farid},
  title  = {Opaque Convoy},
  year   = {2026},
  url    = {https://github.com/AvoCahDoe/Opaque-Convoy}
}
```

Underlying theory:

> Mitsos, G., Dimarogonas, D. V., & Liu, S. (2026). Security-Aware Planning and Control of Multi-Agent Systems with LTL Tasks. arXiv:2605.13134.
