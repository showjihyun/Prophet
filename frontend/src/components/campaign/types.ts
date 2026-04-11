/**
 * Shared types and constants for the Campaign Setup form.
 * Extracted from the monolithic CampaignSetupPage so each section
 * component can consume them without circular imports.
 *
 * @spec docs/spec/ui/UI_16_CAMPAIGN_SETUP.md
 */
import type { CommunityConfigInput } from "../../api/client";

export const CHANNELS = ["SNS", "Influencer", "Online Ads", "TV", "Email"] as const;

export const AGENT_TYPES = [
  "early_adopter",
  "consumer",
  "skeptic",
  "expert",
  "influencer",
  "bridge",
] as const;

export const PERSONALITY_KEYS = [
  "openness",
  "skepticism",
  "trend_following",
  "brand_loyalty",
  "social_influence",
] as const;

export const PERSONALITY_LABELS: Record<string, string> = {
  openness: "Openness",
  skepticism: "Skepticism",
  trend_following: "Trend Following",
  brand_loyalty: "Brand Loyalty",
  social_influence: "Social Influence",
};

export const COMMUNITY_COLORS = [
  "#3b82f6",
  "#22c55e",
  "#f97316",
  "#a855f7",
  "#ef4444",
  "#06b6d4",
  "#ec4899",
  "#84cc16",
];

export function defaultCommunity(index: number): CommunityConfigInput {
  return {
    id: String.fromCharCode(65 + index),
    name: `Community ${String.fromCharCode(65 + index)}`,
    size: 100,
    agent_type: "consumer",
    personality_profile: {
      openness: 0.5,
      skepticism: 0.5,
      trend_following: 0.5,
      brand_loyalty: 0.5,
      social_influence: 0.5,
    },
  };
}

/** Fallback community options used when no templates have been loaded yet. */
export const FALLBACK_COMMUNITY_OPTIONS = [
  { id: "alpha", name: "Alpha", color: "#3b82f6" },
  { id: "beta", name: "Beta", color: "#22c55e" },
  { id: "gamma", name: "Gamma", color: "#f97316" },
  { id: "delta", name: "Delta", color: "#a855f7" },
  { id: "bridge", name: "Bridge", color: "#ef4444" },
];
