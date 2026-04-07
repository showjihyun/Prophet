# Prophet Roadmap

This is the public roadmap. It's intentionally directional rather than
deadline-driven — open source moves at the speed of contributors.

If something here matters to you, **open a Discussion or Issue**. We prioritize
based on what real users actually need.

---

## ✅ Shipped

- 6-layer agent engine (perception, memory, emotion, cognition, decision, influence)
- Hybrid network generator (Watts-Strogatz + Barabási-Albert + bridges)
- Diffusion engine with auto cascade detection
- 3-tier LLM inference (Mass SLM / Heuristic / Elite LLM)
- Real-time WebSocket visualization
- Monte Carlo simulation
- Pause / Resume / Step / Reset / Run-All controls
- Community management (CRUD + agent reassignment)
- Project / scenario management
- Export to JSON / CSV
- Real-time propagation animation with zoom-based LOD
- Tier A+B performance optimizations (backend + frontend)
- Docker Compose deployment

---

## 🟡 In Progress

- **Hosted Cloud Starter tier** — managed Prophet, $99/month, 5K agents max
- **Scenario template library** — pre-built scenarios for common launches
  (CPG, public health, internal comms, political messaging)
- **Validation studies** — running real campaigns through Prophet retroactively
  and comparing predicted vs. actual outcomes; publishing the results
- **`good first issue` backlog** — surfacing 10–20 newcomer-friendly tickets
- **Documentation site** — versioned docs at docs.prophet.io
- **Performance tier C optimizations** — Ray-based CPU parallelism for
  community ticks

---

## ⬜ Planned (no committed timeline)

### Engine
- Plugin SDK for custom agent layers (custom perception, custom memory backend)
- Multi-language LLM agents (cross-cultural simulation)
- Time-of-day modeling (engagement varies by hour)
- Real-world data ingestion (anonymized survey data → synthetic population calibration)

### Integrations
- Segment / mParticle / HubSpot connector
- Slack / Teams "what would happen if we sent this?" bot
- Webhook API for embedding Prophet in other tools
- Notion / Confluence integration for sharing simulation reports

### Marketplace
- Synthetic population marketplace (industry-specific community templates)
- Validated agent personality presets
- Community-contributed scenario library

### Research
- OASIS-compatibility layer (run OASIS scenarios in Prophet)
- Reproducibility certifications for academic use
- Export to standard ABM formats (NetLogo, MASON)

### Enterprise
- SSO (SAML, OIDC)
- Audit logs
- Multi-tenant cloud
- On-premise deployment guide
- Compliance docs (SOC 2, GDPR)

---

## 🤔 Under Consideration

Things we're not sure about yet. Comment on the linked Discussion if you have
an opinion.

- **Native mobile viewer** — read-only iOS/Android app for watching simulations on the go
- **Voice narration** — LLM-generated audio walkthrough of a simulation result
- **Collaborative editing** — multiple users on the same simulation in real time
- **Markdown campaign authoring** — write campaigns in markdown, simulate from CLI
- **GPT-OSS / Llama 4 support** — when they ship

---

## How to Influence the Roadmap

1. **Open a Discussion** describing the use case and the gap
2. **Vote** with 👍 reactions on existing issues/discussions
3. **Build it** — fork, prototype, share your branch
4. **Sponsor** — if a feature matters enough to your team, sponsoring
   maintainers makes it happen faster

We don't promise to build everything, but we do read everything.

---

## What We Won't Build

To keep Prophet focused, we're explicitly **not** going to:

- Build a CRM or marketing automation tool — Prophet is a simulator, not a launcher
- Become a survey panel — synthetic populations are the whole point
- Train custom models — we're a consumer of LLMs, not a producer
- Build a closed-source "Pro" version that's better than the open one

If you need any of those, there are great tools that already exist.
