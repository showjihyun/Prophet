/**
 * Central glossary of Prophet (MCASP) technical and simulation terminology.
 *
 * Every UI label that surfaces a domain-specific term should pull its
 * explanation from here via `<HelpTooltip term="..." />`. Adding a new
 * term in one place automatically lets every consumer use it.
 *
 * Style guide for entries:
 * - `label`: short, capitalized, matches the on-screen label
 * - `text`: 1–3 sentences, plain English, no jargon-on-jargon
 * - Explain the *meaning*, not the implementation
 * - When a value has a range, include it (e.g. "−1.0 to +1.0")
 * - When a higher / lower value matters, say what direction is "good"
 */

export const GLOSSARY = {
  // ───────── Core simulation ─────────
  totalSteps: {
    label: "Total Steps",
    text: "Number of simulation steps that ran. Each step represents one tick of agent perception, cognition, and action across the entire population.",
  },
  step: {
    label: "Step",
    text: "A single simulation tick. During one step, every active agent perceives its environment, updates its memory and emotion, decides on an action, and propagates influence to its neighbors.",
  },
  totalAgents: {
    label: "Total Agents",
    text: "All agents in the simulated population, regardless of activity level. Includes early adopters, mainstream consumers, skeptics, experts, and influencers across all communities.",
  },
  activeAgents: {
    label: "Active Agents",
    text: "Agents that performed a non-idle action (share, comment, adopt, etc.) during the latest step. The 'active / total' ratio shows how engaged the population is right now.",
  },

  // ───────── Adoption & diffusion ─────────
  adoptionRate: {
    label: "Adoption Rate",
    text: "Percentage of agents that have adopted the campaign / message. 100% means everyone adopted; 0% means no one did. The single most important success metric for a campaign.",
  },
  finalAdoption: {
    label: "Final Adoption",
    text: "Percentage of agents that adopted the campaign by the end of the simulation. Compare to the initial adoption rate to see how much the campaign moved the needle.",
  },
  diffusionRate: {
    label: "Diffusion Rate",
    text: "Number of new adoptions per step. A measure of how fast the message is spreading right now. High and rising = viral; flat or falling = stalling.",
  },
  diffusionWaveTimeline: {
    label: "Diffusion Wave Timeline",
    text: "A sparkline of the cascade's diffusion rate over the last 100 simulation steps. Higher areas mean more new adoptions that step; a rising curve is viral spread, a falling curve means saturation or resistance. Amber pins mark emergent events (viral cascade, echo chamber, polarization, collapse) so you can correlate shape with what the detector fired.",
  },
  propagation: {
    label: "Propagation",
    text: "When one agent's action (share, comment, adopt) influences a neighbor, a propagation event is recorded. These edges drive how messages flow through the network.",
  },

  // ───────── Sentiment ─────────
  sentiment: {
    label: "Sentiment",
    text: "How positively or negatively agents feel about the campaign. Range: −1.0 (strongly negative) to +1.0 (strongly positive). 0 is neutral.",
  },
  finalSentiment: {
    label: "Final Sentiment",
    text: "Average sentiment of all agents at the final step of the simulation. Range: −1.0 to +1.0. Even with high adoption, negative sentiment signals brand risk.",
  },
  sentimentDistribution: {
    label: "Sentiment Distribution",
    text: "How the population's feelings split across positive, neutral, and negative right now. A healthy campaign trends positive over time; a polarizing one shows positive AND negative growing together.",
  },
  meanBelief: {
    label: "Mean Belief",
    text: "Average belief score across agents in this community. Range: −1.0 (strongly opposed) to +1.0 (strongly in favor). Reflects the underlying conviction, not just surface sentiment.",
  },

  // ───────── Emergent behaviors ─────────
  polarization: {
    label: "Polarization Index",
    text: "How divided the population's beliefs are. 0 = everyone agrees; 1 = the population has split into opposing camps. High polarization predicts viral controversy.",
  },
  emergentEvents: {
    label: "Emergent Events",
    text: "Behavioral patterns Prophet automatically detects: viral cascade, polarization, echo chamber, collapse, and slow adoption. More events = more dynamic, more interesting simulation.",
  },
  viralCascade: {
    label: "Viral Cascade",
    text: "A rapid chain of adoptions across many communities, typically triggered by influencer agents. The pattern marketers want — and the one PR teams fear when the message is wrong.",
  },
  cascadeDepth: {
    label: "Cascade Depth",
    text: "How many propagation hops the cascade has reached from its origin. Depth 1 = direct shares only; depth 10+ = the message is reaching people far from where it started.",
  },
  cascadeWidth: {
    label: "Cascade Width",
    text: "How many distinct agents the cascade has touched in total. Width measures reach; depth measures penetration. A campaign needs both.",
  },
  echoChamber: {
    label: "Echo Chamber",
    text: "A community where the message keeps circulating among the same agents without escaping to other communities. Echo chambers boost in-group conviction but limit overall reach.",
  },
  collapse: {
    label: "Collapse",
    text: "Detected when a campaign's adoption rate drops sharply step-over-step. Often follows a controversial event or backlash. Early warning sign for marketing teams.",
  },
  slowAdoption: {
    label: "Slow Adoption",
    text: "The opposite of viral: the campaign is spreading well below the threshold expected for its size. Usually means the message isn't resonating.",
  },

  // ───────── Agents & roles ─────────
  influencer: {
    label: "Influencer",
    text: "An agent with high influence score and many connections. Influencers disproportionately shape what their community believes — landing one in a campaign is worth dozens of normal agents.",
  },
  influenceScore: {
    label: "Influence Score",
    text: "How much weight an agent's actions carry with neighbors. Range: 0.0 to 1.0. Influencers typically score above 0.7. Used to rank agents and detect viral cascade origins.",
  },
  bridge: {
    label: "Bridge Agent",
    text: "An agent connected across multiple communities, acting as a conduit between otherwise isolated groups. Cross-community messages must pass through bridges — they're the chokepoint of cross-community virality.",
  },
  community: {
    label: "Community",
    text: "A clustered group of agents with shared characteristics: early adopters, consumers, skeptics, experts, or influencers. Real social networks are composed of overlapping communities, not random connections.",
  },
  topCommunity: {
    label: "Top Community",
    text: "The community with the highest adoption rate at the end of the simulation. The percentage shows how much of that specific community adopted.",
  },

  // ───────── Personality & emotion ─────────
  belief: {
    label: "Belief",
    text: "An agent's current opinion about the campaign topic. Range: −1.0 (strongly against) to +1.0 (strongly in favor). Updates step by step based on what the agent perceives and remembers.",
  },
  openness: {
    label: "Openness",
    text: "How receptive an agent is to new ideas. High openness agents adopt faster but are also more easily swayed back. Range: 0.0 to 1.0.",
  },
  trendFollowing: {
    label: "Trend Following",
    text: "How much an agent imitates what their neighbors are doing. High trend-following agents drive virality once a critical mass is reached. Range: 0.0 to 1.0.",
  },
  emotion: {
    label: "Emotion",
    text: "An agent's current emotional state across four dimensions: interest, trust, excitement, and skepticism. Emotion modulates how the agent reacts to the next message it sees.",
  },

  // ───────── LLM cost engine ─────────
  tier1: {
    label: "Tier 1 (Mass SLM)",
    text: "Small Language Model running locally — used for the bulk of agents (~80%). Fast, free per call, good enough for routine cognition. The reason a 10K-agent simulation costs $5 instead of $15K.",
  },
  tier2: {
    label: "Tier 2 (Heuristic)",
    text: "Pure rule-based decisions — no LLM call at all. Used for ~10% of agents in clear-cut situations. The cheapest tier; instant.",
  },
  tier3: {
    label: "Tier 3 (Elite LLM)",
    text: "Frontier LLM (Claude / GPT-4 / Gemini) — used for the ~10% of agents whose decisions matter most: influencers, experts, and pivotal moments. Expensive per call but worth it.",
  },
  slmLlmRatio: {
    label: "SLM / LLM Ratio",
    text: "Fraction of agents handled by the local Small Language Model versus the elite LLM. Higher = cheaper but less nuanced; lower = more expensive but higher fidelity.",
  },

  // ───────── Simulation flow ─────────
  adoptionCurve: {
    label: "Adoption Curve",
    text: "Adoption rate plotted over time. Steep rises indicate viral spread; flat plateaus indicate stalling. The shape of the curve tells you what kind of campaign you have.",
  },
  keyEvents: {
    label: "Key Events",
    text: "Notable behavioral patterns detected during the run, in chronological order. Each event includes its step number and a short description of what happened.",
  },

  // ───────── Analytics page charts ─────────
  analyticsAdoptionChart: {
    label: "Adoption Rate Over Time",
    text: "Fraction of the population that adopted the campaign, step by step. The curve's shape is the headline: an S-curve means healthy viral spread, a linear slope means steady push-based growth, and a flat line means the message is stalling. Delta vs. baseline (the dashed line, when a comparison scenario is loaded) shows what THIS run changed.",
  },
  analyticsSentimentChart: {
    label: "Mean Sentiment Over Time",
    text: "Average belief across all agents, from -1 (hostile) to +1 (enthusiastic), per step. Tracks whether the campaign is winning hearts or hardening opposition. Sudden drops mark injected shocks (negative PR, controversies); sustained climbs mark successful reframing.",
  },
  analyticsCommunityComparison: {
    label: "Community Adoption Comparison",
    text: "Bar chart of per-community adoption at the final step. Tells you WHO adopted and who didn't — a 70% overall adoption rate means nothing if one community is at 95% and another at 20%. Use this to spot segments the campaign failed to reach.",
  },
  analyticsCascadeAnalytics: {
    label: "Cascade Analytics",
    text: "Summary of viral cascades detected during the run: how many fired, how deep (node hops from source to farthest adopter), how wide (total nodes touched), and which communities they propagated through. Cascades are the engine of viral growth — their absence usually explains a flat adoption curve.",
  },
  analyticsEventTimeline: {
    label: "Emergent Event Timeline",
    text: "Chronological list of every emergent event the detectors flagged — viral cascades, polarization, echo chambers, collapse, slow adoption. Click a row to jump to that step. Filter by type to study a specific dynamic without the noise of others.",
  },

  // ───────── Settings — LLM providers ─────────
  settingsDefaultProvider: {
    label: "Default Provider",
    text: "Which LLM backend Prophet uses for Tier 3 (elite) calls. Ollama and vLLM run locally on your hardware (free after setup). Claude, OpenAI, and Gemini are cloud APIs (charged per call). The 3-tier inference model only hits this provider for the ~10% of agents that really need it.",
  },
  settingsProviderBaseUrl: {
    label: "Base URL",
    text: "HTTP endpoint where the self-hosted inference server is running. Must be reachable from the Prophet backend container — when using Docker Compose, this is typically the service name (e.g. `http://ollama:11434`) rather than `localhost`.",
  },
  settingsProviderModel: {
    label: "Model",
    text: "The specific model identifier to use for chat-style completions. Free-text so you can use any model the provider supports — Prophet passes it through without validation. When in doubt, use the provider's flagship (e.g. `gpt-4o`, `claude-sonnet-4-6`, `gemini-2.0-flash`).",
  },
  settingsProviderApiKey: {
    label: "API Key",
    text: "Secret credential for the cloud provider. Sent to the backend only when you press Save, and the backend never returns it on subsequent reads — the placeholder tells you whether a key is currently stored without revealing its value.",
  },
  settingsEmbedModel: {
    label: "Embed Model",
    text: "Model used to generate vector embeddings for agent memory similarity search. Different from the chat model — it must be an embedding-specific model (e.g. `text-embedding-3-small` for OpenAI, `models/text-embedding-004` for Gemini). Leave at the default unless you know you want a different embedding space.",
  },
  settingsSlmModel: {
    label: "SLM Model (Tier 1)",
    text: "The Small Language Model used for the ~80% of agents that run on Tier 1 — fast, local, free per call. This is typically the same model as the Ollama Default Model, but can be set separately if you want a lighter model for the mass population (e.g. a 1B model for SLM, a bigger model for Tier 3 fallbacks).",
  },

  // ───────── Settings — Simulation defaults ─────────
  settingsTier3Ratio: {
    label: "LLM Tier 3 Ratio",
    text: "Hard cap on the fraction of agents that get routed to Tier 3 (the elite LLM) per step. Range 0.0–1.0, default 0.10. Higher = more nuanced behavior but more API cost; lower = cheaper but flatter cognition. The tier selector picks influencers and critical agents first, so even 0.10 captures the high-leverage decisions.",
  },
  settingsCacheTtl: {
    label: "LLM Cache TTL",
    text: "How long (in seconds) the backend keeps an LLM response cached before re-calling. Default 3600 (1 hour). Prophet caches by prompt fingerprint, so two agents asking the exact same question share one call. Raise it for long batch runs to save money; lower it if you're tuning prompts and need fresh output.",
  },

  // ───────── Page-level overviews ─────────
  pageGlobalMetrics: {
    label: "Global Insight & Metrics",
    text: "A scenario-wide dashboard that summarizes what happened across the whole simulated population — total agents, polarization trend, sentiment by community, the 3-tier LLM cost split, and the cascade analytics. Use this to answer 'in aggregate, how did the run go?' before drilling into per-community detail.",
  },
  pageAnalytics: {
    label: "Post-Run Analytics",
    text: "A read-only deep-dive into a completed simulation: adoption curve, sentiment trajectory, per-community comparison, cascade analytics, and the full emergent-event timeline. Open this after a run finishes; click any timeline row to deep-link back to that step on the Simulation page.",
  },
  pageOpinions: {
    label: "Opinion Landscape",
    text: "A three-level hierarchy that lets you read the simulation as if it were public discourse. Level 1 (this page) is the scenario-wide opinion landscape; Level 2 zooms into one community's opinion clusters; Level 3 surfaces individual conversation threads. Use this to answer what the population is talking about and how they feel.",
  },
  pageCommunityOpinion: {
    label: "Community Opinion (L2)",
    text: "Per-community deep-dive: the dominant opinion clusters within this community, the support/neutral/oppose split per topic, and the most recent agent conversations. Click an opinion cluster or conversation to drill further (Level 3).",
  },

  // ───────── Global Metrics — section headers ─────────
  globalPolarizationTrend: {
    label: "Polarization Trend",
    text: "Belief variance across the population over the last 10 simulation steps. Bars rising means the population is splitting into camps; bars falling means belief is converging. Color: green (low, <0.3), amber (mid), red (high, ≥0.6 — fragmentation risk).",
  },
  globalSentimentByCommunity: {
    label: "Sentiment by Community",
    text: "Stacked bar showing each community's positive / neutral / negative split at the latest step. Lets you spot which segments the campaign won and which it lost — even when the global average looks healthy. Long red bands flag at-risk communities.",
  },
  globalThreeTierCost: {
    label: "Prophet 3-Tier Cost Optimization",
    text: "Live breakdown of which inference tier each agent ran on this step. Tier 1 (~80%) is local SLM (free). Tier 2 (~10%) is heuristic (free). Tier 3 (~10%) is the elite cloud LLM (paid per call). The closer the split stays to the 80/10/10 default, the closer your run cost stays to the under-$5 target.",
  },
  globalCascadeAnalytics: {
    label: "Cascade Analytics",
    text: "Four summary numbers about cascades fired during this run: average depth (hops from origin), max width (largest one-step jump in adoption), critical paths (number of cascade events), and decay rate (how fast peak diffusion fell off). Together they tell you whether the campaign achieved viral spread or merely a one-step push.",
  },
  globalActiveCascades: {
    label: "Active Cascades",
    text: "Number of agents currently in an actively-propagating state at the latest step. Derived as adoption_rate × total_agents — a rough proxy for how many agents are actively carrying the message right now (not just have seen it).",
  },
  globalSimulationStep: {
    label: "Simulation Step",
    text: "Current tick of the simulation engine, out of the configured maximum. A step is one full round where every active agent perceives, decides, and acts. The progress bar shows how far through the configured run you are.",
  },

  // ───────── Opinions — section headers ─────────
  opinionsAvgSentiment: {
    label: "Avg Sentiment",
    text: "Population-wide mean belief at the current step, on a -1.0 (strongly hostile) to +1.0 (strongly enthusiastic) scale. The delta below shows how much it moved from the previous step — a sustained climb signals successful framing.",
  },
  opinionsTotalConversations: {
    label: "Total Conversations",
    text: "Number of agent-to-agent message threads recorded so far in the simulation. Higher means more discourse activity — useful proxy for engagement separate from adoption (people can talk about something without adopting it).",
  },
  opinionsCommunityBreakdown: {
    label: "Community Opinion Breakdown",
    text: "Per-community summary cards showing the dominant stance (positive / negative / mixed), conversation count, and sentiment distribution. Click any card to drill into that community's opinion clusters and recent conversations.",
  },
  opinionClusters: {
    label: "Opinion Clusters",
    text: "Topics this community is currently debating, ranked by mention count. Each cluster shows the support / neutral / oppose split — the percentages reflect actual agent stances, not poll responses. A high contested ratio (Support ≈ Oppose) flags a polarizing topic.",
  },
  recentConversations: {
    label: "Recent Conversations",
    text: "Latest agent-generated message threads from this community, in reverse chronological order. Each entry is real LLM output produced during the simulation — click to read the full thread. Useful for understanding the *why* behind the sentiment numbers.",
  },

  // ───────── Settings — vLLM ─────────
  settingsVllmMaxConcurrent: {
    label: "Max Concurrent Requests",
    text: "How many agent inference requests vLLM will process in parallel. Higher = faster simulation but more GPU memory pressure. Default 64. If you see OOM errors on your GPU, lower this first before touching the model size.",
  },
} as const satisfies Record<string, { label: string; text: string }>;

export type GlossaryTerm = keyof typeof GLOSSARY;
