# Prophet (MCASP) — Marketing & Launch Strategy

Version: 1.0 | Date: 2026-04-07 | Audience: Founder + first contributors

---

## 0. Positioning Statement

> **Prophet is the wind tunnel for marketing campaigns.**
> Run your message through 10,000 AI agents organized into real social
> communities and watch it succeed — or burn down — before you spend a
> dollar on the launch.

**One-sentence pitch (engineer audience):**
> Open-source agent-based simulation engine that combines a 6-layer cognitive
> agent, GraphRAG memory, and a 3-tier LLM cost model to predict how messages
> spread through social networks.

**One-sentence pitch (marketing audience):**
> Pre-test your campaign on a virtual society before you spend the launch
> budget — see exactly how the message spreads, where it stalls, and which
> communities push back.

**One-sentence pitch (academic audience):**
> An open-source, reproducible alternative to OASIS for computational social
> science, with built-in viral cascade detection and 100x lower compute cost.

---

## 1. Audience Segments & Messaging

| Segment | Pain | Hook | Channel | CTA |
|---------|------|------|---------|-----|
| **ML Engineers** | "I want to play with agent simulations but everything is academic and slow" | "10K LLM agents on your laptop in under 2 seconds per step" | HN, r/MachineLearning, dev.to | Star the repo, run the demo |
| **Marketing leads** | "I'm spending $500K on a launch and I have no idea if it'll work" | "Simulate your launch through a virtual audience for under $50" | LinkedIn, AdAge, Marketing Week | Book a demo |
| **PR / Comms** | "We're always reactive when something goes viral the wrong way" | "Pre-screen every message for viral risk before it ships" | PR Week, Substack newsletters | Pilot program |
| **Researchers** | "OASIS is great but expensive and closed" | "Reproducible, open, 10x cheaper, runs on a laptop" | NeurIPS, ICWSM, papers w/ code | Cite + use |
| **Policy / Public Health** | "How do we predict misinformation cascades?" | "Test communication strategies on a synthetic population" | Govtech, public health journals | Workshop |
| **Internal Comms** | "RTO/DEI/layoff announcements always backfire" | "Pre-test internal messages against your synthetic org" | LinkedIn, HR newsletters | Enterprise demo |

---

## 2. Launch Plan — 90 Days

### Phase 1 — Foundations (Days 1–14)

**Goal:** Make the project look credible and easy to try.

- [ ] Polish `README.md` — hero image, GIF demo, 5-minute quickstart
- [ ] Record 2-minute demo video (graph spreading, real-time animation, control panel)
- [ ] Build landing page (`prophet.io` or similar) with the wind-tunnel pitch
- [ ] Write 3 blog posts:
  1. "Why marketing campaigns need a wind tunnel" (positioning)
  2. "How we built a 10,000-agent LLM simulation that runs in 2 seconds per step" (technical)
  3. "The $5 vs $15K simulation: why tiered LLM inference matters" (cost story)
- [ ] Set up GitHub Discussions, issue templates, contributing guide
- [ ] Add architecture diagram + roadmap to README
- [ ] Create demo dataset: 3 pre-built scenarios (product launch, public health message, political slogan)

### Phase 2 — Soft Launch (Days 15–30)

**Goal:** Get first 100 GitHub stars, 10 design partner conversations.

- [ ] Personal outreach to 30 ML / marketing / academic contacts before going public
- [ ] Post in 5 niche communities first (smaller, kinder feedback): 
  - Indie Hackers, r/SideProject, Lobsters, Dev.to, Medium
- [ ] Publish technical blog post on personal blog
- [ ] DM 10 marketing leaders on LinkedIn for "research conversation"
- [ ] Submit talk proposals to 3 conferences (PyCon, MLConf, Marketing Analytics Summit)

### Phase 3 — Public Launch (Days 31–60)

**Goal:** Show HN front page, 1,000+ stars, first paying customer.

- [ ] **Show HN launch** — Tuesday 9am EST, with interactive demo link
  - Title: "Show HN: Prophet — Simulate marketing campaigns through 10,000 LLM agents"
  - Be present in comments for 8 hours straight
- [ ] **Twitter/X technical thread** — 12-tweet breakdown of the architecture
- [ ] **Product Hunt launch** — "Best of the day" target
- [ ] **Reddit launches** (staged, not all at once):
  - r/MachineLearning (Saturday "self-promotion" thread)
  - r/marketing (Monday)
  - r/datascience (Wednesday)
- [ ] **YouTube technical walkthrough** by a channel with 50K+ subscribers
  - Outreach: Andrej Karpathy, Two Minute Papers, Yannic Kilcher style
- [ ] Press release to TechCrunch, VentureBeat, The Information
- [ ] First case study published (with first design partner)

### Phase 4 — Build the Flywheel (Days 61–90)

**Goal:** $5K MRR, 5 paying customers, 5,000 GitHub stars, 1 academic citation.

- [ ] Weekly blog post cadence (alternate technical / use case)
- [ ] First conference talk
- [ ] First academic paper using Prophet (collaborate with researcher contact)
- [ ] Hire first growth/community person
- [ ] Launch Cloud Starter ($99/mo) self-service tier
- [ ] Set up affiliate / referral program for agencies
- [ ] First customer-led webinar

---

## 3. Content Strategy

### 3.1 Content pillars

**Pillar 1 — Technical credibility (40%)**
- "How we built X" deep-dives
- Performance benchmarks
- SPEC document walkthroughs
- Open-source contribution highlights

**Pillar 2 — Use case storytelling (30%)**
- "We simulated [famous campaign] — here's what we found"
- Customer case studies
- "What if we'd tested this beforehand?" historical analysis (Pepsi Kendall Jenner, Bud Light, etc.)

**Pillar 3 — Category education (20%)**
- "Why focus groups are obsolete"
- "The hidden math of viral cascades"
- "Inside an agent's head: how Prophet decides"

**Pillar 4 — Community / culture (10%)**
- Contributor spotlights
- Office hours recordings
- Behind-the-scenes "we shipped this" posts

### 3.2 Specific high-value content ideas

| Title | Format | Audience | Priority |
|-------|--------|----------|----------|
| "We re-simulated the Bud Light campaign in Prophet" | Blog + video | Marketing | **P0** |
| "From 287ms to 1500ms: scaling agent simulation to 10K agents" | Engineering blog | ML Eng | **P0** |
| "GraphRAG for agent memory: a practical guide" | Technical tutorial | ML Eng | **P1** |
| "The $5 simulation: how 3-tier LLM inference works" | Cost engineering blog | Eng + biz | **P0** |
| "Detecting viral cascades mathematically" | Academic-leaning blog | Research | **P1** |
| "10 marketing campaigns we wish someone had simulated first" | Listicle | Marketing | **P0** |
| "Open-sourcing Prophet: why and how" | Founder essay | Everyone | **P0** |
| "Show HN debrief: what 100K HN visitors taught us about marketing tools" | Retrospective | Founder community | **P2** |

---

## 4. Channels & Tactics

### 4.1 Hacker News (highest leverage)

**Why:** A successful Show HN can drive 10K+ stars overnight and unlock VC interest.

**Tactics:**
- Submit Tuesday 9am EST (best engagement window)
- Have an interactive demo URL ready (sandbox.prophet.io)
- 30-second loading time max — first impressions kill
- Reply to every comment for the first 8 hours
- Have a "we built this because..." personal narrative ready
- Title: "Show HN: Prophet — Test marketing campaigns on a virtual society of 10K AI agents"

### 4.2 Twitter / X

**Strategy:** Build a personal founder voice, then amplify the project.

- 1 technical thread per week (architecture, perf, design decisions)
- Reply guy mode in agent / LLM / marketing tech communities
- Pin the demo video
- Engage with: Andrej Karpathy, Simon Willison, Hamel Husain, swyx, Yann LeCun, Ethan Mollick

### 4.3 LinkedIn (for marketing audience)

**Strategy:** Founder-led thought leadership in marketing space.

- 2 posts per week minimum
- Format: hook → story → lesson → CTA
- Topics: campaign post-mortems, viral case studies, cost of marketing failures
- DM marketing leaders for "research conversations" (not pitches)

### 4.4 YouTube

**Strategy:** Long-form demo + technical walkthrough.

- 5-minute "what is Prophet" explainer
- 20-minute "let's simulate the Apple Vision Pro launch in Prophet" deep-dive
- 1-minute "60 seconds of Prophet" social cuts
- Outreach to 10 ML/marketing channels for cross-promotion

### 4.5 Academic outreach

**Strategy:** Get cited, get used in coursework, get referenced in papers.

- Submit to ICWSM, CSCW, NeurIPS workshops on agent-based modeling
- Provide free Cloud Pro to 10 university research groups
- Sponsor a "Prophet Best Paper" award at one conference
- Open call for collaboration with comp-soc-sci professors

### 4.6 Conference circuit

**Target conferences (Year 1):**
- PyCon (technical)
- MLOps Summit (ML eng)
- Marketing Analytics Summit (buyers)
- ICWSM (academic)
- IndieHackers Festival (community)

---

## 5. Brand & Voice

### 5.1 Brand attributes

| Attribute | What it looks like | What to avoid |
|-----------|-------------------|---------------|
| **Bold** | "The wind tunnel for marketing" | Hedging, "kind of like" |
| **Technical-but-accessible** | Diagrams + plain English | Pure jargon, dumbed-down |
| **Skeptical of hype** | "AI won't fix bad marketing — but it'll show you why it's bad" | "Revolutionary AI-powered" |
| **Confident but humble** | "We built this. We think it's useful. Here's why it might be wrong." | "World's first" claims |
| **Visual** | Always show the graph | Walls of text |

### 5.2 Voice examples

**Don't write:**
> Prophet leverages cutting-edge AI technology to revolutionize marketing simulation through advanced agent-based modeling powered by next-generation LLMs.

**Do write:**
> Prophet runs your campaign through 10,000 AI agents organized into real social communities. You watch it spread, see where it stalls, and find out why — before you spend the launch budget.

### 5.3 Visual identity

- **Primary metaphor:** Wind tunnel / graph / network
- **Color palette:** Dark mode default (matches the engineering audience), graph-friendly (community colors are part of the brand)
- **Typography:** Monospace for code/data, sans-serif for marketing copy
- **Demo aesthetic:** The Cytoscape graph IS the brand. Every screenshot should show it.

---

## 6. Metrics & Goals

### 6.1 90-day targets

| Metric | Target | Stretch |
|--------|--------|---------|
| GitHub stars | 1,000 | 5,000 |
| Cloud signups (Starter) | 50 | 200 |
| Cloud Pro customers | 5 | 15 |
| Design partner pilots | 10 | 25 |
| Academic citations / mentions | 1 | 5 |
| Press mentions (top-50 outlets) | 2 | 8 |
| HN front page | 1 visit | 3+ visits |
| YouTube views (cumulative) | 10K | 50K |
| Newsletter subscribers | 500 | 2,000 |
| MRR | $500 | $5,000 |

### 6.2 Year 1 targets

- 25,000 GitHub stars
- $1M ARR
- 100 paying customers (Cloud Pro + Enterprise)
- 5 published case studies
- 10 academic papers using Prophet
- 1 acquisition offer (good leverage even if rejected)

---

## 7. Activation Funnel

```
GitHub README / landing page  →  Star + Bookmark
        ↓
2-minute demo video           →  "I get it"
        ↓
Sandbox demo (no signup)      →  "I want to try this on my problem"
        ↓
Cloud Starter signup          →  Free email capture
        ↓
3 simulations run             →  Activation moment
        ↓
Paid Cloud Pro upgrade        →  Conversion
        ↓
Case study + referral         →  Flywheel
```

**Activation moment:** The first time a user runs a simulation on their own
campaign / message / scenario and sees a result that surprises them. This is
when they tell their team. Optimize the entire onboarding flow for this moment
within the first 5 minutes of signup.

---

## 8. Risks & Defenses

| Risk | Defense |
|------|---------|
| "AI sims are inaccurate" criticism | Validation studies, transparency about limitations, peer-reviewed accuracy paper in Year 1 |
| Big competitor copies | Open-source community is the moat; speed of iteration |
| Marketing buyers don't understand AI | Lead with the visual; show, don't tell; case studies in their language |
| Privacy backlash | Synthetic populations only, explicit messaging about no real data |
| "Just another agent framework" perception | Lead with the cost engineering ($5 vs $15K), the cascade detector, and the visualization — not the agent loop |

---

## 9. Competitive Messaging

**vs. OASIS:**
> "OASIS is the academic gold standard. Prophet is OASIS made affordable, productized, and visual — so marketing teams (not just researchers) can use it."

**vs. Brandwatch / Sprinklr:**
> "They tell you what already happened. Prophet tells you what will happen — before you ship."

**vs. Survey panels:**
> "Surveys ask 200 people what they'd do. Prophet shows you what 10,000 do, including how they influence each other."

**vs. A/B testing:**
> "A/B tests are great — once your campaign is live and you're already paying for it. Prophet runs the test before launch."

---

## 10. First Marketing Asset Checklist

Before launch day, these must all exist:

- [ ] **README.md** — hero image, demo GIF, 5-minute quickstart, architecture, contribution guide
- [ ] **Landing page** — single hero, demo video embed, 3 use cases, sign-up CTA
- [ ] **2-minute demo video** — graph animation hero, narrated, ends with CTA
- [ ] **30-second social cut** — pure visual, music, no narration, for Twitter/LinkedIn
- [ ] **Architecture diagram (PNG)** — for blog posts and decks
- [ ] **3 pre-built scenarios** — embedded in the demo, one-click run
- [ ] **Pricing page** — even if Cloud isn't ready, list "coming soon" tiers
- [ ] **Documentation site** — at least getting-started, API reference, SPEC index
- [ ] **Case study template** — for first design partners
- [ ] **One-pager PDF** — for sales conversations
- [ ] **Investor deck** — even if not raising, useful for partnerships

---

## 11. Long-Term Vision (Year 2–3)

Once the wedge works, expand:

**Year 2 — Adjacent verticals**
- Public health communication simulation (gov licenses)
- Internal corporate communication (HR/comms)
- Crisis communication pre-planning (PR firms)

**Year 3 — Platform play**
- Marketplace for community templates (industry-specific synthetic populations)
- Plugin SDK for custom agent layers
- Integration ecosystem: Segment, mParticle, HubSpot, Salesforce
- Validated synthetic populations (sold as data products)

**Year 5 — The category leader**
- "Run your campaign through Prophet" becomes a verb in marketing
- The default pre-launch step for every major launch
- Acquisition target for Adobe, Salesforce, Oracle, or strategic IPO
