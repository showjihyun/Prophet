<div align="center">

<!-- Hero banner placeholder — record a 15-s loop of the 3D graph spreading,
     convert with gifski, and drop at docs/assets/hero.gif -->
<img src="docs/assets/hero.gif" alt="Prophet — 3D social simulation spreading in real time" width="720" onerror="this.style.display='none'"/>

# 🔮 Prophet

### The wind tunnel for marketing campaigns

**Test your campaign on 10,000 AI agents before you spend a dollar on the launch.**

[![GitHub stars](https://img.shields.io/github/stars/showjihyun/prophet?style=for-the-badge&logo=github&color=f5c518)](https://github.com/showjihyun/prophet/stargazers)
[![License: MIT](https://img.shields.io/github/license/showjihyun/prophet?style=for-the-badge&color=blue)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.1.1.0-8a2be2?style=for-the-badge)](CHANGELOG.md)
[![Last commit](https://img.shields.io/github/last-commit/showjihyun/prophet?style=for-the-badge&color=28a745)](https://github.com/showjihyun/prophet/commits)

[![Python](https://img.shields.io/badge/python-3.12+-3776ab?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-61dafb?logo=react&logoColor=white)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5-3178c6?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Docker](https://img.shields.io/badge/Docker-ready-2496ed?logo=docker&logoColor=white)](https://www.docker.com/)
[![Tests](https://img.shields.io/badge/tests-1031_BE_%7C_736_FE-brightgreen)]()

<br/>

**[🚀 Quick Start](#-quick-start)** ·
**[✨ Features](#-features)** ·
**[🎯 Use Cases](#-use-cases)** ·
**[📊 Comparison](#-how-prophet-compares)** ·
**[📖 Docs](#-documentation)** ·
**[🤝 Contributing](#-contributing)**

</div>

<br/>

```bash
git clone https://github.com/showjihyun/prophet.git
cd prophet && docker compose up -d
open http://localhost:5173
```

**That's it.** 5 minutes from clone to your first simulation. No API keys required to start — Prophet runs fully locally on a laptop.

---

## 💡 Why Prophet?

Focus groups lie — 10 humans in a room cannot tell you how a message spreads through a community.
A/B tests are too late — by the time you have data, you're already paying for the launch.
Brand-lift studies take 6 weeks, cost $50K, and tell you nothing about *why* a message failed.

Every discipline that ships things at scale — **aerospace, civil engineering, software** — gets to simulate before it builds. Marketing doesn't. **Until now.**

> **You take your campaign. You drop it into a virtual society of 10,000 AI agents organized into the communities you actually care about. You watch what happens.**

---

## ✨ Features

<table>
<tr>
<td width="33%" valign="top">

### 🧠 6-Layer Agent Engine
Each agent perceives, remembers, feels, cognizes, decides, and influences — powered by LLM cognition with persistent per-agent memory.

</td>
<td width="33%" valign="top">

### 💰 Under $5 per run
3-tier inference (80% local SLM + 10% heuristic + 10% elite LLM) keeps 10K-agent simulations radically cheap. A naive GPT-4 run costs ~$15K.

</td>
<td width="33%" valign="top">

### 🌐 Realistic networks
Hybrid Watts-Strogatz + Barabási-Albert generator produces realistic clustering, power-law influencers, and cross-community bridges.

</td>
</tr>
<tr>
<td valign="top">

### 🎥 Watch it spread
Real-time 3D WebGL graph (three.js) with orbit / zoom / pan controls, community-colored nodes, and cascade highlighting.

</td>
<td valign="top">

### 🔥 Auto-cascade detection
Viral cascades, polarization, echo chambers, collapse, slow adoption — detected and timeline-marked as the simulation runs.

</td>
<td valign="top">

### 🔌 Multi-LLM ready
Ollama, Claude, OpenAI, Gemini, **+ 2026 Chinese flagships** (DeepSeek, Qwen, Moonshot Kimi, Zhipu GLM) out of the box.

</td>
</tr>
<tr>
<td valign="top">

### 🚨 Mid-run intervention
Pause any time, **Inject Event** (controversy / endorsement / regulation), or **Replay from step N** to branch the timeline and try a different shock.

</td>
<td valign="top">

### ⚙️ Live engine control
Dial the SLM / LLM ratio while the simulation is paused. Trade cost for reasoning depth without restarting from step 0.

</td>
<td valign="top">

### 🔀 Compare scenarios
Run the same campaign with one variable changed. **Compare** view puts adoption / sentiment / cascades side by side. **Clone** any run in one click.

</td>
</tr>
</table>

---

## 🚀 Quick Start

### 🐳 Docker (recommended)

#### GPU — NVIDIA (strongly recommended)

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d
docker compose exec ollama ollama pull llama3.1:8b
```

On an RTX 4070-class GPU, llama3.1:8b runs at **~75 tok/s** — sub-second per agent tick.

#### CPU-only (no NVIDIA)

```bash
docker compose up -d
export OLLAMA_DEFAULT_MODEL=llama3.2:1b SLM_MODEL=llama3.2:1b
docker compose up -d --force-recreate backend
docker compose exec ollama ollama pull llama3.2:1b
```

#### Service endpoints

| Service             | URL                          |
|---------------------|------------------------------|
| 🖥️ Frontend         | http://localhost:5173        |
| ⚙️ Backend API      | http://localhost:8000        |
| 📘 API Docs (Swagger) | http://localhost:8000/docs |

Open `localhost:5173` → **Projects** → create a scenario with a campaign message → click **Run All**. Watch the 3D graph spread in real time.

### 💻 Local development

```bash
# Backend
cd backend && uv sync && uv run uvicorn app.main:app --reload

# Frontend
cd frontend && npm install && npm run dev
```

---

## 🎮 What you actually do in the UI

Prophet is not just an engine — it's a workspace. Here's the loop you actually click through:

1. **Set up.** **Projects → New Scenario → Campaign Setup.** You name the campaign, write the message, dial in *novelty / controversy / utility*, set the budget, pick which communities it lands on, and choose how many steps to run (default 50).
2. **Run.** **Run All** for the whole sweep, or **Step** to advance one tick at a time and watch the 3D graph spread. **Pause** any time.
3. **Intervene mid-run.** While paused you can:
   - **Inject Event** — drop a sudden shock (Controversy / Celebrity Endorsement / Regulatory Change / etc.) targeting all or specific communities. Takes effect on the next step.
   - **Engine Control** — change the SLM / LLM ratio live. Trade cost for reasoning depth without restarting.
   - **Replay from step N** — branch the simulation at any past step and try a different intervention from there.
4. **Read the result.** When it completes you get a **Summary Report** (adoption curve, sentiment, top community, scrollable Key Events timeline) and the dedicated **Analytics** page with deep deltas, cascade timeline, and shareable deep links.
5. **Drill into why.** **Opinions** lets you go scenario → community → individual conversation thread. **Top Influencers** ranks who actually moved the needle. **Agent Interview** asks any single agent why it decided what it did.
6. **Compare.** Run the same campaign with one variable changed (different message, different intervention, different population) and the **Compare** view shows them side by side. **Clone** any scenario in one click to start the next variant.

This is the loop. Most decisions get made between steps 3 and 6 — set it up once, run it many ways.

---

## 🎯 Use Cases

<details>
<summary><strong>🧃 Pre-test a product launch</strong></summary>

A beverage brand was about to spend **$1.2M** launching a sustainability product. Ran the message against 5,000 agents (15% skeptics, 60% mainstream, 20% early adopters, 5% influencers). Prophet showed the message **polarized** skeptics and adoption stalled at **13%**. They reframed and hit **78%** by the same step in the second simulation.

</details>

<details>
<summary><strong>💉 Pre-screen public health messages</strong></summary>

A health agency tested 3 vaccine messages against a 5K-agent virtual population. Strategy B caused **near-zero adoption** in skeptical communities (no viral cascade events in the first 4 steps). Strategy C triggered **three positive cascades** through influencer nodes by step 4. They picked C — adoption lift was **312×** at the early-step horizon.

</details>

<details>
<summary><strong>🏢 Stress-test internal communications</strong></summary>

A Fortune 500 ran their RTO mandate through a synthetic employee population (4,500 engineering-heavy agents). Prophet predicted **complete stall** + slide into negative sentiment (mean_belief = -0.23, zero cascades). Restructured with carve-outs: same population hit **94% adoption** with **+0.68 sentiment** — a +91-point swing from restructuring alone.

</details>

<details>
<summary><strong>🚨 Stress-test crisis response (mid-run shock injection)</strong></summary>

A consumer brand wanted to know how a sudden negative PR event would derail an ongoing campaign. Ran the campaign normally for 20 steps (adoption climbing toward 64%), then mid-run injected `Controversy + "battery explosion in 47 units" + 0.9` via the **Inject Event** modal targeting only the skeptic community. The next 8 steps showed adoption stall at 41% and sentiment crash from +0.42 to -0.31, with two negative cascade events on the timeline. They tested two response messages on top: "transparent recall + free replacement" recovered to 58% by step 30; "deny and deflect" drove a third cascade and stalled at 19%. Crisis playbook went from gut-feel to rehearsed.

</details>

<details>
<summary><strong>🔬 Computational social science research</strong></summary>

Open-source. Reproducible. Runs on a laptop. Built-in cascade detection. If you've been wanting to do agent-based diffusion research without renting a GPU cluster, Prophet is for you.

</details>

> **Reproducible.** Every claim above is verified end-to-end against the current engine in [`docs/USE_CASE_PILOTS.md`](docs/USE_CASE_PILOTS.md), with raw per-step JSON in `docs/pilot_results/`. Re-run any pilot with `uv run python backend/scripts/run_use_case_pilot.py --case <name>`.

---

## 📊 How Prophet compares

|                                  | **Prophet**   | OASIS (academic) | AnyLogic     | Focus groups |
|----------------------------------|:-------------:|:----------------:|:------------:|:------------:|
| 💵 10K-agent simulation cost     | **under $5**  | free             | $15K+ license | $30K+       |
| ⏱️ Time to first result          | **5 minutes** | hours            | days         | 6 weeks      |
| 🧠 LLM-driven agent cognition    | ✅            | ✅               | ❌           | n/a          |
| 🎨 Real-time 3D visualization    | ✅            | ❌               | ✅           | ❌           |
| 🌊 Cascade / echo chamber detect | ✅            | ❌               | ❌           | ❌           |
| 📈 Marketing-specific metrics    | ✅            | ❌               | partial      | ✅           |
| 🆓 Open source                   | **MIT**       | MIT              | ❌           | n/a          |
| 💻 Runs on a laptop              | ✅            | ✅               | ✅           | n/a          |

*Numbers are rough order-of-magnitude based on public pricing and running comparable workloads. Your mileage will vary.*

---

## 📸 Screenshots

<table>
<tr>
<td width="50%" valign="top">
<img src="docs/assets/screenshots/simulation-3d.png" alt="3D simulation graph with cascade highlighting" onerror="this.style.display='none'"/>
<sub><strong>3D Simulation Workspace</strong> — community-colored agents, real-time cascade glow, adopted-node tinting per community. Inject Event / Engine Control / Replay live in the sidebar.</sub>
</td>
<td width="50%" valign="top">
<img src="docs/assets/screenshots/opinions.png" alt="Three-level Opinions hierarchy" onerror="this.style.display='none'"/>
<sub><strong>Opinions Hierarchy</strong> — drill from scenario → community → individual conversation thread. See exactly which messages drove the consensus or the polarization.</sub>
</td>
</tr>
<tr>
<td valign="top">
<img src="docs/assets/screenshots/analytics.png" alt="Post-run Analytics page" onerror="this.style.display='none'"/>
<sub><strong>Post-Run Analytics</strong> — adoption curve, sentiment trajectory, per-community breakdown, cascade timeline. Deep-link any metric for sharing.</sub>
</td>
<td valign="top">
<img src="docs/assets/screenshots/influencers.png" alt="Top Influencers page" onerror="this.style.display='none'"/>
<sub><strong>Top Influencers</strong> — power-law influencers ranked by network reach + step-by-step propagation contribution. Find who actually moved the needle.</sub>
</td>
</tr>
</table>

> Screenshots not rendering? They live in [`docs/assets/screenshots/`](docs/assets/screenshots/) — a fresh clone may be missing them while we record the next batch.

---

## 🏗️ Architecture

```
1. Generate     → 10K agents in 5 communities (early adopters, mainstream,
                  skeptics, experts, influencers) with realistic clustering,
                  scale-free degree, and bridge nodes

2. Inject       → Your campaign / message / policy

3. Simulate     → Each agent runs the 6-layer loop
                  (perception → memory → emotion → cognition → decision → influence)

4. Detect       → Viral cascades, polarization, echo chambers, collapse,
                  slow adoption — auto-marked on the timeline

5. Visualize    → 3D WebGL graph with orbit / zoom / pan,
                  community-colored nodes and edges, WebSocket live updates

6. Decide       → Compare scenarios, export JSON / CSV, share links
```

---

## 🧰 Tech Stack

| Layer        | Stack                                                                    |
|--------------|--------------------------------------------------------------------------|
| 🖼️ Frontend  | React 18 · TypeScript · Vite · Tailwind · react-force-graph-3d (three.js) · Cytoscape.js |
| 🧵 State     | Zustand · TanStack Query · native WebSocket                              |
| ⚙️ Backend   | Python 3.12 · FastAPI (async) · SQLAlchemy 2.0 · Pydantic v2              |
| 🤖 LLM       | **Ollama** (local SLM) · Claude · OpenAI · Gemini · **DeepSeek · Qwen · Moonshot Kimi · Zhipu GLM** |
| 🗄️ Database  | PostgreSQL 16 + pgvector                                                 |
| ⚡ Cache     | Valkey                                                                   |
| 🧪 Testing   | pytest (**1,031**) · Vitest (**736**) · Playwright (E2E)                 |
| 📦 Package   | `uv` (Python) · `npm` (Node)                                             |

---

## 🧪 What's working today

- ✅ **6-layer agent engine** with LLM-driven cognition
- ✅ **3-tier inference** keeping 10K-agent simulations under $5
- ✅ **Real-time 3D WebGL graph** that scales to 5K+ nodes
- ✅ **Cascade, echo chamber, polarization** auto-detection from real network topology
- ✅ **WebSocket live streaming** with pause / resume / step / run-all
- ✅ **8 LLM providers** first-class — Ollama, Claude, OpenAI, Gemini + 4 Chinese flagships (2026)
- ✅ **1,767+ automated tests** with Playwright E2E coverage

🟡 **In progress:** hosted Cloud Starter tier, scenario template library, validation studies
🔮 **Planned:** plugin SDK, Segment / mParticle / HubSpot integrations, multi-language agents

Full history → [CHANGELOG.md](CHANGELOG.md) · Roadmap discussion → [ROADMAP.md](ROADMAP.md)

---

## 📖 Documentation

- 📘 **API Docs** → http://localhost:8000/docs (Swagger UI when running)
- 🛠️ **[Contributing Guide](CONTRIBUTING.md)** — setup under 10 minutes
- 🤝 **[Code of Conduct](CODE_OF_CONDUCT.md)**
- 🔒 **[Security Policy](SECURITY.md)**
- 📜 **[Changelog](CHANGELOG.md)**
- 🗺️ **[Roadmap](ROADMAP.md)**
- 🌿 **[Git Branch Strategy](docs/GIT_BRANCH_STRATEGY.md)**

---

## ⭐ Star History

[![Star History Chart](https://api.star-history.com/svg?repos=showjihyun/prophet&type=Date)](https://star-history.com/#showjihyun/prophet&Date)

*If Prophet is useful to you, a star is the fastest way to help others find it.*

---

## 🤝 Contributing

**We need help.** Specifically:

- 🐛 **Bug reports** with reproduction steps
- 📝 **Documentation** improvements (typos, clarity, examples)
- 🧪 **Test cases** for edge cases you find
- 🌱 **[`good first issue`](https://github.com/showjihyun/prophet/labels/good%20first%20issue)** picks — small, clearly-scoped tasks for newcomers
- 💡 **Use cases** — tell us what you're trying to simulate; we may already support it

**Start here:**

1. Read [`CONTRIBUTING.md`](CONTRIBUTING.md)
2. Browse [`good first issue`](https://github.com/showjihyun/prophet/labels/good%20first%20issue)
3. Open a Discussion before any large change
4. Open a PR — we aim to respond within 48 hours

Maintainers are active. First-time contributors get a thank-you and a fast review. We label every issue, keep the roadmap public, and publish what we ship.

### 👥 Contributors

<a href="https://github.com/showjihyun/prophet/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=showjihyun/prophet" alt="Contributors" />
</a>

---

## 🗣️ Community

- 💬 **[GitHub Discussions](https://github.com/showjihyun/prophet/discussions)** — questions, ideas, show-and-tell
- 🐞 **[GitHub Issues](https://github.com/showjihyun/prophet/issues)** — bugs and feature requests

*If you build something cool with Prophet, we want to see it. Open a Discussion and post a screenshot.*

---

## 🙏 Inspiration & Acknowledgments

Prophet stands on the shoulders of many other projects.

<details>
<summary><strong>MiroFish</strong> — biggest architectural influence</summary>

MiroFish combined OASIS (academic agent simulator) with GraphRAG and Zep Cloud for long-term memory. It proved LLM-driven agents with persistent memory could be assembled into a coherent pipeline. Prophet takes that idea, opens it up, makes it cheaper through tiered inference, and adds the marketing-specific layer (cascade detection, viral metrics, real-time viz) that MiroFish doesn't focus on.

</details>

<details>
<summary><strong>Other prior art we learned from</strong></summary>

- **OASIS** — academic foundation for large-scale agent-based social simulation
- **GraphRAG** (Microsoft Research) — hybrid vector + graph retrieval pattern
- **NetworkX** — hybrid WS+BA generator would have taken months instead of days without it
- **three.js / react-force-graph-3d** — 3D rendering; instanced sphere rendering scales to thousands of nodes
- **Cytoscape.js** — EgoGraph 2D force-directed layout
- **Ollama** — local SLM inference makes the 3-tier cost model possible
- **Hugging Face / open-weight LLM community** — proved small models are good enough for agent reasoning
- **NetLogo and MASON** — showed decades ago that simulating a society is a tractable engineering problem

</details>

If you contributed to any of these and feel we should credit you more specifically, open a PR — we'll fix it.

---

## 📜 License

**MIT** — see [LICENSE](LICENSE).

Use it commercially. Fork it. Modify it. Embed it. We just ask you to keep the license file and not pretend you wrote it from scratch.

---

## 📚 Citation

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

<div align="center">

**Built because marketing deserves a wind tunnel.**
**Open-sourced because everyone deserves one.**

<sub>Made with ⚡ and way too much coffee · [⬆ back to top](#-prophet)</sub>

</div>
