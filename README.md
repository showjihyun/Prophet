# Prophet

> **The wind tunnel for marketing campaigns.**
> Test your campaign on 10,000 AI agents before you spend a dollar on the launch.

> _[Hero GIF placeholder — 15-second loop: 3D graph spreads, cascade highlights
> light up communities, sentiment chart updates in real time. Record with
> QuickTime/OBS, convert with `gifski`, drop at `docs/assets/hero.gif`.]_

[![GitHub stars](https://img.shields.io/github/stars/showjihyun/prophet?style=social)](https://github.com/showjihyun/prophet/stargazers)
[![License: MIT](https://img.shields.io/github/license/showjihyun/prophet)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.1.1.0-blue)](CHANGELOG.md)
[![Tests](https://img.shields.io/badge/tests-1002%20backend%20%7C%20656%20frontend-brightgreen)]()
[![Last commit](https://img.shields.io/github/last-commit/showjihyun/prophet)](https://github.com/showjihyun/prophet/commits)
[![Discussions](https://img.shields.io/github/discussions/showjihyun/prophet)](https://github.com/showjihyun/prophet/discussions)

Prophet is an open-source simulation engine for marketing teams, PR agencies,
and researchers who are tired of finding out a campaign failed *after* it shipped.
You point it at your message, your audience, and your communities — it tells you
how the message spreads, where it stalls, and which groups push back.

```bash
git clone https://github.com/showjihyun/prophet.git
cd prophet && docker compose up -d
open http://localhost:5173
```

That's the whole quick start. 5 minutes from clone to your first simulation.

---

## Proof: what people use it for

> **Reproducible.** Every quantitative claim below is verified end-to-end
> against the current engine in [`docs/USE_CASE_PILOTS.md`](docs/USE_CASE_PILOTS.md),
> with raw per-step JSON in `docs/pilot_results/`. Re-run any pilot with
> `uv run python backend/scripts/run_use_case_pilot.py --case <name>`.

### Pre-test a product launch

A beverage brand was about to spend $1.2M launching a sustainability-focused
product. Ran the message through Prophet against 5,000 agents (15% skeptics, 60%
mainstream, 20% early adopters, 5% influencers). The simulation showed the message
**polarized** the skeptical community and adoption stalled at 13%.
They reframed the campaign and hit 78% by the same step in the second simulation.

### Pre-screen public health messages

A health agency tested 3 vaccine messages against a 5K-agent virtual population.
Strategy B caused near-zero adoption in skeptical communities (no viral cascade
events fired in the first 4 steps). Strategy C triggered three positive viral
cascades through influencer nodes by step 4. They picked C — adoption lift was
312× at the early-step horizon and the final cascade reached 98%.

### Stress-test internal communications

A Fortune 500 ran their RTO mandate announcement through a synthetic employee
population (engineering-heavy, 4,500 agents). Prophet predicted a complete
adoption stall and a slide into negative sentiment in engineering
(mean_belief = -0.23, zero viral cascade events). They restructured the
announcement with carve-outs and the same population hit 94% adoption with
+0.68 sentiment — a +91-point swing in sentiment from restructuring alone.

### Computational social science research

Open-source. Reproducible. Runs on a laptop. Built-in cascade detection. If you've
been wanting to do agent-based diffusion research without renting a GPU cluster,
Prophet is for you.

---

## Is Prophet for you?

**Yes, if you...**
- Ship marketing campaigns and hate guessing what happens after launch
- Run a PR agency and want to pre-test messages against synthetic audiences
- Research agent-based social simulation, information diffusion, or LLM-driven societies
- Want to see diffusion dynamics you cannot get from post-hoc analytics

**No, if you want...**
- A CRM replacement (use HubSpot or Salesforce)
- Real-time ad bidding (use a DSP)
- Traditional A/B testing on live traffic (use Optimizely or VWO)
- A no-code tool — Prophet is a developer tool, you will touch Docker and JSON

---

## How Prophet compares

|                           | **Prophet**    | OASIS (academic) | AnyLogic   | Focus groups |
|---------------------------|:--------------:|:----------------:|:----------:|:------------:|
| 10K-agent simulation cost | **under $5**   | free             | $15K+ license | $30K+     |
| Time to first result      | **5 minutes**  | hours            | days       | 6 weeks      |
| LLM-driven agent cognition| **yes**        | yes              | no         | n/a          |
| Real-time 3D visualization| **yes**        | no               | yes        | no           |
| Cascade / echo chamber detection | **yes** | no               | no         | no           |
| Marketing-specific metrics| **yes**        | no               | partial    | yes          |
| Open source               | **MIT**        | MIT              | no         | n/a          |
| Runs on a laptop          | **yes**        | yes              | yes        | n/a          |

Numbers are rough order-of-magnitude based on public pricing and author estimates
from running comparable workloads. Your mileage will vary.

---

## Why this exists

If you've ever shipped a campaign and watched it crater, you know the feeling.
Focus groups lie to you — 10 humans in a room cannot tell you how a message spreads
through a community. A/B tests are too late — by the time you have data, you are
already paying for the launch you are trying to validate. Brand-lift studies take
6 weeks, cost $50K, and tell you nothing about *why* the message failed.

Prophet exists because there is no wind tunnel for marketing. Every other
discipline that ships things at scale — aerospace, civil engineering, software —
gets to simulate before it builds. Marketing doesn't. Until now.

**You take your campaign. You drop it into a virtual society of 10,000 AI agents
organized into the communities you actually care about. You watch what happens.**

---

## Three things that make Prophet different

**1. It's affordable.** A naive 10K-agent GPT-4 simulation costs ~$15,000. Prophet's
3-tier inference model (80% local SLM + 10% heuristic + 10% elite LLM) brings the
same simulation to **under $5**. You can run hundreds of scenarios for the price
of one focus group.

**2. The networks are real.** Random graphs don't behave like communities. Prophet
generates social networks using a hybrid Watts-Strogatz + Barabasi-Albert model
that produces realistic clustering, power-law influencers, and cross-community
bridges. Your simulation isn't a toy.

**3. You can watch it happen.** 3D WebGL graph visualization powered by three.js.
Community-colored nodes orbit and cluster in real time. Cascades light up
communities. You see the simulation spread, step by step, the same way the real
campaign would. Marketing leaders who see the demo immediately understand what
Prophet does — no slide deck needed.

---

## How it works (in 6 steps)

```
1. Generate     → 10K agents in 5 communities (early adopters, consumers,
                  skeptics, experts, influencers) with realistic structure
                  (clustering, scale-free degree, bridge nodes)

2. Inject       → Your campaign / message / policy

3. Simulate     → Each agent perceives, remembers, evaluates, decides, acts
                  (12 actions: ignore, share, comment, adopt, reject...)

4. Detect       → Auto-detect viral cascades, polarization, echo chambers,
                  collapse, slow adoption

5. Visualize    → 3D WebGL graph with orbit/zoom/pan controls,
                  community-colored nodes and edges, real-time updates

6. Decide       → Compare scenarios, export results
```

---

## Quick Start

### Run with Docker (recommended)

```bash
git clone https://github.com/showjihyun/prophet.git
cd prophet
```

#### GPU (strongly recommended — NVIDIA)

The default config is tuned for GPU inference. If you have an NVIDIA card
with the WSL2/CUDA runtime, start the stack with the GPU override:

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d

# Pull the default model (4.9 GB on disk, ~5.6 GiB VRAM)
docker compose exec ollama ollama pull llama3.1:8b
```

On an RTX 4070-class GPU llama3.1:8b runs at **~75 tok/s** (~20-30×
faster than CPU). Every agent tick and the opinion synthesis endpoint
finish in sub-second wall time, and your CPU stays free for the rest
of the engine (NetworkX graph generation, agent decision loops,
pgvector queries).

#### CPU-only (laptops, no NVIDIA GPU)

```bash
# Start without the GPU override
docker compose up -d

# Override to a small model before pulling — llama3.2:1b is ~1.3 GB
# on disk and ~2 GiB in RAM, fits on modest laptops.
export OLLAMA_DEFAULT_MODEL=llama3.2:1b
export SLM_MODEL=llama3.2:1b
docker compose up -d --force-recreate backend
docker compose exec ollama ollama pull llama3.2:1b
```

CPU inference is 20-50× slower than GPU — expect every LLM-bearing
simulation step to pin every core of your host. Usable, but plan
accordingly.

#### Service endpoints

| Service             | URL                          |
|---------------------|------------------------------|
| Frontend            | http://localhost:5173        |
| Backend API         | http://localhost:8000        |
| API Docs (Swagger)  | http://localhost:8000/docs   |

Open `http://localhost:5173`, go to **Projects**, create a new scenario
with a campaign message, and click **Run All**. The 3D graph spreads
in real time.

### Local development

```bash
# Backend
cd backend
uv sync
uv run uvicorn app.main:app --reload
uv run pytest -q

# Frontend
cd frontend
npm install
npm run dev
npx vitest run
```

---

## Tech Stack

Prophet is open-source from top to bottom — no proprietary dependencies anywhere.

| Layer          | Stack                                                     |
|----------------|-----------------------------------------------------------|
| Frontend       | React 18, TypeScript, Vite, Tailwind, react-force-graph-3d (three.js), Cytoscape.js (EgoGraph) |
| State          | Zustand, TanStack Query, native WebSocket                 |
| Backend        | Python 3.12, FastAPI (async), SQLAlchemy 2.0, Pydantic v2 |
| LLM            | Ollama (local SLM), Claude API, OpenAI API, Gemini API    |
| Database       | PostgreSQL 16 + pgvector                                  |
| Cache          | Valkey                                                    |
| Testing        | pytest (1,002), Vitest (656), Playwright (E2E)            |
| Package mgmt   | `uv` (Python), `npm` (Node)                               |

---

## What's working today

- **6-layer agent engine** with LLM-driven cognition (perception, memory, emotion, cognition, decision, influence)
- **3-tier inference** keeping 10K-agent simulations under $5 (Mass SLM / Heuristic / Elite LLM)
- **Real-time 3D WebGL graph** visualization that scales to 5K+ nodes
- **Cascade, echo chamber, and polarization** auto-detection from real network topology
- **WebSocket live streaming** with pause / resume / step / run-all controls
- **1,658+ automated tests** (1,002 backend + 656 frontend) with Playwright E2E coverage

**In progress:** hosted Cloud Starter tier, scenario template library, validation
studies vs. real campaigns.

**Planned:** plugin SDK for custom agent layers, Segment / mParticle / HubSpot
integrations, multi-language LLM agents for cross-cultural simulation.

Full history in [CHANGELOG.md](CHANGELOG.md). Roadmap discussion in
[ROADMAP.md](ROADMAP.md) and [GitHub Discussions](https://github.com/showjihyun/prophet/discussions).

---

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=showjihyun/prophet&type=Date)](https://star-history.com/#showjihyun/prophet&Date)

If Prophet is useful to you, a star is the fastest way to help other people find it.

---

## Contributing

**We need help.** Specifically:

- **Bug reports** with reproduction steps
- **Documentation** improvements (typos, clarity, examples)
- **Test cases** for edge cases you find
- **`good first issue`** picks — small, clearly-scoped tasks tagged for newcomers
- **Use cases** — tell us what you're trying to simulate; we may already support it

Start here:

1. Read [`CONTRIBUTING.md`](CONTRIBUTING.md) — setup is under 10 minutes
2. Browse [`good first issue`](https://github.com/showjihyun/prophet/labels/good%20first%20issue)
3. Open a Discussion before any large change
4. Open a PR — we aim to respond within 48 hours

Maintainers are active. First-time contributors get a thank-you and a fast review.
We label every issue, we keep the roadmap public, and we publish what we ship.

---

## Documentation

- **API Docs** — http://localhost:8000/docs (Swagger UI when running)
- **[Contributing Guide](CONTRIBUTING.md)**
- **[Code of Conduct](CODE_OF_CONDUCT.md)**
- **[Security Policy](SECURITY.md)**
- **[Changelog](CHANGELOG.md)**
- **[Roadmap](ROADMAP.md)**
- **[Git Branch Strategy](docs/GIT_BRANCH_STRATEGY.md)**

---

## Community

- **[GitHub Discussions](https://github.com/showjihyun/prophet/discussions)** — questions, ideas, show-and-tell
- **[GitHub Issues](https://github.com/showjihyun/prophet/issues)** — bugs and feature requests

If you build something cool with Prophet, we want to see it. Open a Discussion
and post a screenshot.

---

## Inspiration & Acknowledgments

Prophet stands on the shoulders of work done by many other people and projects.
The ideas didn't come from nowhere — and we want to credit where credit is due.

### Inspired by MiroFish

The single biggest influence on Prophet's architecture was **MiroFish**, which
combines OASIS (the academic agent simulator) with GraphRAG and Zep Cloud for
long-term agent memory. MiroFish proved that LLM-driven agents with persistent
memory could be assembled into a coherent simulation pipeline. Prophet takes that
idea, opens it up, makes it cheaper through tiered inference, and adds the
marketing-specific layer (cascade detection, viral metrics, real-time
visualization) that MiroFish doesn't focus on.

### Other prior art we learned from

- **OASIS** — the academic foundation for large-scale agent-based social
  simulation. Prophet's RecSys-inspired exposure model and multi-community
  network structure draw directly from OASIS's design.
- **GraphRAG** (Microsoft Research) — the hybrid vector + graph retrieval
  pattern that powers Prophet's per-agent memory layer.
- **NetworkX** — without it, the hybrid Watts-Strogatz + Barabasi-Albert
  network generator would have taken months instead of days.
- **three.js / react-force-graph-3d** — the 3D rendering engine behind
  Prophet's real-time graph visualization. Instanced sphere rendering makes
  1,000-5,000 node graphs run smoothly in WebGL.
- **Cytoscape.js** — powers the EgoGraph (per-agent neighborhood view) with
  2D force-directed layout.
- **Ollama** — local SLM inference is what makes the 3-tier cost model possible.
  Without `llama3.2:1b` on a laptop, every Prophet simulation would still cost
  thousands of dollars.
- **The Hugging Face / open-weight LLM community** — for proving that small
  models can be good enough for agent reasoning.
- **NetLogo and MASON** — the original agent-based modeling toolkits. They
  showed the world that "simulating a society" was a tractable engineering
  problem decades before LLMs made the agents interesting.

If you contributed to any of these and feel we should credit you more
specifically, open a PR — we'll fix it.

---

## License

MIT — see [LICENSE](LICENSE).

Use it commercially. Fork it. Modify it. Embed it. We just ask you to keep the
license file and not pretend you wrote it from scratch.

---

## Citation

If Prophet helps your research, please cite:

```bibtex
@software{prophet_2026,
  title  = {Prophet: A simulation engine for marketing campaign diffusion},
  author = {Prophet Contributors},
  year   = {2026},
  url    = {https://github.com/showjihyun/prophet}
}
```

---

**Built because marketing deserves a wind tunnel.**
**Open-sourced because everyone deserves one.**
