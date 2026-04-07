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
  monteCarlo: {
    label: "Monte Carlo",
    text: "Run the same simulation many times with different random seeds, then aggregate the results. Used to get confidence intervals and detect rare events that a single run would miss.",
  },
  adoptionCurve: {
    label: "Adoption Curve",
    text: "Adoption rate plotted over time. Steep rises indicate viral spread; flat plateaus indicate stalling. The shape of the curve tells you what kind of campaign you have.",
  },
  keyEvents: {
    label: "Key Events",
    text: "Notable behavioral patterns detected during the run, in chronological order. Each event includes its step number and a short description of what happened.",
  },
} as const satisfies Record<string, { label: string; text: string }>;

export type GlossaryTerm = keyof typeof GLOSSARY;
