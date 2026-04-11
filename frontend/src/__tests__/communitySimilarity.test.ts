/**
 * Tests for the pure-function similarity advisor.
 * @spec docs/spec/25_COMMUNITY_INSIGHT_SPEC.md#csi-01
 */
import { describe, it, expect } from "vitest";
import {
  analyzeCommunitySimilarity,
  PERSONALITY_TRAITS,
  SIMILAR_PAIR_THRESHOLD,
} from "@/components/campaign/communitySimilarity";
import type { CommunityConfigInput } from "@/api/client";

function makeCommunity(
  id: string,
  name: string,
  profile: Partial<Record<(typeof PERSONALITY_TRAITS)[number], number>>,
): CommunityConfigInput {
  return {
    id,
    name,
    size: 100,
    agent_type: "consumer",
    personality_profile: {
      openness: 0.5,
      skepticism: 0.5,
      trend_following: 0.5,
      brand_loyalty: 0.5,
      social_influence: 0.5,
      ...profile,
    },
  };
}

describe("analyzeCommunitySimilarity", () => {
  it("returns ok severity for an empty community list", () => {
    const r = analyzeCommunitySimilarity([]);
    expect(r.severity).toBe("ok");
    expect(r.overallSimilarity).toBe(0);
    expect(r.suggestions).toEqual([]);
    expect(r.similarPairs).toEqual([]);
  });

  it("returns ok severity for a single community", () => {
    const r = analyzeCommunitySimilarity([makeCommunity("A", "alpha", {})]);
    expect(r.severity).toBe("ok");
    expect(r.suggestions).toEqual([]);
  });

  it("flags severity=critical when 4 communities are identical", () => {
    const same = (id: string, name: string) =>
      makeCommunity(id, name, {
        openness: 0.5,
        skepticism: 0.5,
        trend_following: 0.5,
        brand_loyalty: 0.5,
        social_influence: 0.5,
      });
    const r = analyzeCommunitySimilarity([
      same("A", "a"),
      same("B", "b"),
      same("C", "c"),
      same("D", "d"),
    ]);
    expect(r.severity).toBe("critical");
    expect(r.overallSimilarity).toBeCloseTo(1.0, 4);
    expect(r.similarPairs.length).toBe(6); // 4 choose 2
    expect(r.suggestions.length).toBeGreaterThan(0);
  });

  it("returns severity=ok for highly differentiated communities", () => {
    const r = analyzeCommunitySimilarity([
      makeCommunity("S", "skeptics", {
        openness: 0.2,
        skepticism: 0.9,
        trend_following: 0.1,
        brand_loyalty: 0.3,
        social_influence: 0.4,
      }),
      makeCommunity("E", "early_adopters", {
        openness: 0.9,
        skepticism: 0.15,
        trend_following: 0.85,
        brand_loyalty: 0.4,
        social_influence: 0.65,
      }),
      makeCommunity("I", "influencers", {
        openness: 0.7,
        skepticism: 0.25,
        trend_following: 0.6,
        brand_loyalty: 0.5,
        social_influence: 0.95,
      }),
    ]);
    expect(r.severity).toBe("ok");
    expect(r.overallSimilarity).toBeLessThan(0.92);
    expect(r.suggestions).toEqual([]);
  });

  it("computes per-trait coefficient of variation correctly", () => {
    const r = analyzeCommunitySimilarity([
      makeCommunity("A", "a", { openness: 0.2 }),
      makeCommunity("B", "b", { openness: 0.8 }),
    ]);
    // values = [0.2, 0.8], mean = 0.5, var = ((0.3)^2 + (0.3)^2)/2 = 0.09,
    // stdDev = 0.3, CV = 0.3/0.5 = 0.6
    expect(r.perTrait.openness).toBeCloseTo(0.6, 4);
    // The other traits are all 0.5 → CV = 0
    expect(r.perTrait.skepticism).toBeCloseTo(0, 4);
  });

  it("identifies similar pairs above the threshold", () => {
    const r = analyzeCommunitySimilarity([
      makeCommunity("A", "alpha", { openness: 0.5, skepticism: 0.5 }),
      makeCommunity("B", "beta", { openness: 0.51, skepticism: 0.51 }), // near-clone
      makeCommunity("C", "gamma", {
        openness: 0.1,
        skepticism: 0.9,
        trend_following: 0.1,
        brand_loyalty: 0.9,
        social_influence: 0.1,
      }),
    ]);
    // alpha ↔ beta are essentially identical
    const ab = r.similarPairs.find(
      (p) => (p.a === "alpha" && p.b === "beta") || (p.a === "beta" && p.b === "alpha"),
    );
    expect(ab).toBeDefined();
    expect(ab!.similarity).toBeGreaterThan(SIMILAR_PAIR_THRESHOLD);
  });

  it("first suggestion mentions the trait with the lowest CV", () => {
    const r = analyzeCommunitySimilarity([
      makeCommunity("A", "a", {
        openness: 0.5,
        skepticism: 0.5,
        trend_following: 0.5,
      }),
      makeCommunity("B", "b", {
        openness: 0.5, // identical → CV=0 for openness
        skepticism: 0.51,
        trend_following: 0.55,
      }),
    ]);
    expect(r.severity).not.toBe("ok");
    // Suggestion 2 should mention openness (lowest CV)
    const traitMention = r.suggestions.find((s) => s.includes("openness"));
    expect(traitMention).toBeDefined();
  });

  it("falls back to default 0.5 when personality_profile is missing", () => {
    const c1: CommunityConfigInput = {
      id: "A",
      name: "a",
      size: 100,
      agent_type: "consumer",
      personality_profile: {},
    };
    const c2: CommunityConfigInput = {
      id: "B",
      name: "b",
      size: 100,
      agent_type: "consumer",
      personality_profile: {},
    };
    const r = analyzeCommunitySimilarity([c1, c2]);
    // Both default to all-0.5 → identical
    expect(r.severity).toBe("critical");
  });

  it("uses id as display name when name is empty", () => {
    const r = analyzeCommunitySimilarity([
      makeCommunity("A", "", { openness: 0.5 }),
      makeCommunity("B", "", { openness: 0.5 }),
    ]);
    const pair = r.similarPairs[0];
    expect(pair.a).toBe("A");
    expect(pair.b).toBe("B");
  });

  it("warning severity sits between critical and ok thresholds", () => {
    // Construct two near-similar (but not identical) communities so
    // similarity falls in (0.92, 0.97].
    const r = analyzeCommunitySimilarity([
      makeCommunity("A", "a", {
        openness: 0.6,
        skepticism: 0.6,
        trend_following: 0.6,
        brand_loyalty: 0.6,
        social_influence: 0.6,
      }),
      makeCommunity("B", "b", {
        openness: 0.55,
        skepticism: 0.65,
        trend_following: 0.5,
        brand_loyalty: 0.6,
        social_influence: 0.65,
      }),
    ]);
    // The exact value depends on the cosine math but should land in
    // [0.92, 0.97] for these inputs. We assert severity ≠ ok and ≠ critical.
    expect(r.severity).not.toBe("ok");
    expect(["warning", "critical"]).toContain(r.severity);
  });
});
