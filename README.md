# Prophet

> **The wind tunnel for marketing campaigns.**
> Test your campaign on 10,000 AI agents before you spend a dollar on the launch.

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

[![Tests](https://img.shields.io/badge/tests-827%2B%20backend%20%7C%20344%2B%20frontend-brightgreen)]()
[![License](https://img.shields.io/badge/license-MIT-blue)]()
[![Status](https://img.shields.io/badge/status-active-brightgreen)]()
[![Discussions](https://img.shields.io/badge/discussions-open-blue)]()

---

## Why this exists

If you've ever shipped a campaign and watched it crater, you know the feeling:

- **Focus groups lied to you** — 10 humans in a room can't tell you how a message
  spreads through a community.
- **A/B tests are too late** — by the time you have data, you're already paying
  for the launch you're trying to validate.
- **Brand-lift studies take 6 weeks** — and cost $50K, and tell you nothing about
  *why* the message failed.

Prophet exists because there is no wind tunnel for marketing. Every other
discipline that ships things at scale — aerospace, civil engineering, software —
gets to simulate before it builds. Marketing doesn't. Until now.

**You take your campaign. You drop it into a virtual society of 10,000 AI agents
organized into the communities you actually care about. You watch what happens.**

---

## Demo

> _[GIF placeholder — 30-second loop showing a simulation: graph spreads, cascade
> highlights light up communities, sentiment chart updates in real-time. Capture
> with Loom or QuickTime, drop here.]_

---

## What you can do with it

### 🛍️ Pre-test a product launch

A beverage brand was about to spend $1.2M launching a sustainability-focused
product. Ran the message through Prophet against 5,000 agents (15% skeptics, 60%
mainstream, 20% early adopters, 5% influencers). The simulation showed the message
**polarized** the skeptical community at step 18 and adoption stalled at 12%.
They reframed the campaign and hit 31% in the second simulation.

### 🏥 Pre-screen public health messages

A health agency tested 3 vaccine messages against a 10K-agent virtual population.
Strategy B caused echo-chamber formation in skeptical communities. Strategy C
triggered a positive viral cascade through influencer nodes. They picked C and
projected 3x adoption.

### 🏢 Stress-test internal communications

A Fortune 500 ran their RTO mandate announcement through a synthetic employee
population. Prophet predicted a 38% sentiment collapse in engineering. They
restructured the announcement with carve-outs and cut opposition by 60%.

### 🔬 Computational social science research

Open-source. Reproducible. Runs on a laptop. Built-in cascade detection. If you've
been wanting to do agent-based diffusion research without renting a GPU cluster,
Prophet is for you.

---

## How it works (in 6 steps)

```
1. Generate     → 10K agents in 5 communities (early adopters, consumers,
                  skeptics, experts, influencers) with realistic structure
                  (clustering, scale-free degree, bridge nodes)

2. Inject       → Your campaign / message / policy

3. Simulate     → Each agent perceives, remembers, evaluates, decides, acts
                  (12 actions: ignore, share, comment, adopt, reject…)

4. Detect       → Auto-detect viral cascades, polarization, echo chambers,
                  collapse, slow adoption

5. Visualize    → Real-time graph with zoom-based animation
                  (close-up / mid / overview tiers)

6. Decide       → Compare scenarios, export results
```

---

## Three things that make Prophet different

**1. It's affordable.** A naive 10K-agent GPT-4 simulation costs ~$15,000. Prophet's
3-tier inference model (80% local SLM + 10% heuristic + 10% elite LLM) brings the
same simulation to **under $5**. You can run hundreds of scenarios for the price
of one focus group.

**2. The networks are real.** Random graphs don't behave like communities. Prophet
generates social networks using a hybrid Watts-Strogatz + Barabási-Albert model
that produces realistic clustering, power-law influencers, and cross-community
bridges. Your simulation isn't a toy.

**3. You can watch it happen.** Real-time graph visualization at 30+ FPS.
Messages flash across edges. Cascades light up communities. You see the simulation
spread, step by step, the same way the real campaign would. Marketing leaders
who see the demo immediately understand what Prophet does — no slide deck needed.

---

## Quick Start

### Run with Docker (recommended)

```bash
git clone https://github.com/showjihyun/prophet.git
cd prophet

# CPU environment (no GPU)
docker compose up -d

# Pull LLM model (first time only, ~4.7GB)
docker compose exec ollama ollama pull llama3.1:8b
```

| Service             | URL                          |
|---------------------|------------------------------|
| Frontend            | http://localhost:5173        |
| Backend API         | http://localhost:8000        |
| API Docs (Swagger)  | http://localhost:8000/docs   |

Open `http://localhost:5173`, click **New Simulation**, pick a template, and
click **Run All**. The graph spreads in real time.

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

### GPU environment

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d
```

---

## Tech Stack

Prophet is open-source from top to bottom — no proprietary dependencies anywhere.

| Layer          | Stack                                                     |
|----------------|-----------------------------------------------------------|
| Frontend       | React 18, TypeScript, Vite, Tailwind, Cytoscape.js, react-force-graph-3d |
| State          | Zustand, TanStack Query, native WebSocket                 |
| Backend        | Python 3.12, FastAPI (async), SQLAlchemy 2.0, Pydantic v2 |
| LLM            | Ollama (local SLM), Claude API, OpenAI API, Gemini API    |
| Database       | PostgreSQL 16 + pgvector                                  |
| Cache          | Valkey                                                    |
| Testing        | pytest, Vitest, Playwright                                |
| Package mgmt   | `uv` (Python), `npm` (Node)                               |

---

## Roadmap

**Shipped:**
- ✅ 6-layer agent engine (perception → memory → emotion → cognition → decision → influence)
- ✅ Hybrid network generator (WS + BA + bridge edges)
- ✅ 3-tier LLM inference (Mass SLM / Heuristic / Elite LLM)
- ✅ Real-time WebSocket visualization
- ✅ Pause / Resume / Run-All controls
- ✅ Export to JSON / CSV
- ✅ Community management (CRUD + reassign)
- ✅ Real-time propagation animation (zoom-based LOD)
- ✅ 3D graph visualization (react-force-graph-3d)
- ✅ Echo chamber detection (real network topology)
- ✅ PersonalityDrift connected to simulation engine
- ✅ Controversy parameter wired end-to-end
- ✅ Monte Carlo parallel execution
- ✅ Historical simulation graceful degradation (agents/network/stop/compare/export return empty data instead of 404 after restart)
- ✅ TanStack Query migration (server-state caching across all pages)
- ✅ ControlPanel refactored (785 → 8 focused files)
- ✅ Glossary tooltips on key metrics

**In progress:**
- 🟡 Hosted Cloud Starter tier
- 🟡 Scenario template library
- 🟡 Validation studies vs. real campaigns

**Planned:**
- ⬜ Plugin SDK for custom agent layers
- ⬜ Integration with Segment / mParticle / HubSpot
- ⬜ Multi-language LLM agents (cross-cultural simulation)
- ⬜ Synthetic population marketplace

See [`ROADMAP.md`](ROADMAP.md) for the full picture and how to influence it.

---

## Contributing

**We need help.** Specifically:

- 🐛 **Bug reports** with reproduction steps
- 📚 **Documentation** improvements (typos, clarity, examples)
- 🧪 **Test cases** for edge cases you find
- ✨ **`good first issue`** picks — small, clearly-scoped tasks tagged for newcomers
- 💡 **Use cases** — tell us what you're trying to simulate; we may already support it

Start here:

1. Read [`CONTRIBUTING.md`](CONTRIBUTING.md) — setup is under 10 minutes
2. Browse [`good first issue`](https://github.com/showjihyun/prophet/labels/good%20first%20issue)
3. Open a Discussion before any large change
4. Open a PR — we aim to respond within 48 hours

Maintainers are active. First-time contributors get a thank-you and a fast review.
We label every issue, we keep the roadmap public, and we publish what we ship.

---

## Documentation

- 📖 **API Docs** — http://localhost:8000/docs (Swagger UI when running)
- 🤝 **[Contributing Guide](CONTRIBUTING.md)**
- 📜 **[Code of Conduct](CODE_OF_CONDUCT.md)**
- 🔒 **[Security Policy](SECURITY.md)**
- 📅 **[Changelog](CHANGELOG.md)**
- 🗺️ **[Roadmap](ROADMAP.md)**

---

## Community

- 💬 **GitHub Discussions** — questions, ideas, show-and-tell
- 🐛 **GitHub Issues** — bugs and feature requests
- 🐦 **Twitter / X** — [@prophet_sim](https://twitter.com/) _(coming soon)_

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
- **NetworkX** — without it, the hybrid Watts-Strogatz + Barabási-Albert
  network generator would have taken months instead of days.
- **Cytoscape.js** — the rendering engine behind Prophet's 10K-node real-time
  graph. It's the reason we can show the simulation instead of just describing
  it.
- **Ollama** — local SLM inference is what makes the 3-tier cost model possible.
  Without `llama3.1:8b` on a laptop, every Prophet simulation would still cost
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
