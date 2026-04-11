/**
 * Community personality similarity advisor.
 *
 * @spec docs/spec/25_COMMUNITY_INSIGHT_SPEC.md#2-similarity-advisor-pre-flight
 *
 * Round 7 pilot finding: when communities have similar personality_profiles,
 * the diffusion engine produces near-identical trajectories across all of
 * them — wasting 5-30 minutes of wall-clock before the user discovers the
 * problem. This module measures pre-flight similarity and flags critical
 * lack of differentiation BEFORE the user clicks Run.
 *
 * Pure functions only — no React, no I/O, no globals. Trivially testable.
 */
import type { CommunityConfigInput } from "../../api/client";

// --------------------------------------------------------------------------- //
// Types                                                                       //
// --------------------------------------------------------------------------- //

/** The 5 personality traits Prophet's diffusion engine reads. */
export const PERSONALITY_TRAITS = [
  "openness",
  "skepticism",
  "trend_following",
  "brand_loyalty",
  "social_influence",
] as const;

export type PersonalityTrait = (typeof PERSONALITY_TRAITS)[number];

export type SimilaritySeverity = "ok" | "warning" | "critical";

export interface SimilarPair {
  /** Community A name (or id when name is missing). */
  a: string;
  b: string;
  /** Cosine similarity in [0, 1]. */
  similarity: number;
}

export interface SimilarityReport {
  /** Mean pairwise cosine similarity (0 = perfectly differentiated, 1 = identical). */
  overallSimilarity: number;
  /** Coefficient of variation per trait (higher = more spread). */
  perTrait: Record<PersonalityTrait, number>;
  /** Pairs whose cosine similarity exceeds 0.95. */
  similarPairs: SimilarPair[];
  /** Severity decision based on overallSimilarity. */
  severity: SimilaritySeverity;
  /** Human-readable suggestions for the user. */
  suggestions: string[];
}

// --------------------------------------------------------------------------- //
// Thresholds                                                                  //
// --------------------------------------------------------------------------- //

/** Pairs above this similarity are flagged in `similarPairs`. */
export const SIMILAR_PAIR_THRESHOLD = 0.95;

/** overallSimilarity above this triggers severity=critical. */
export const CRITICAL_SIMILARITY_THRESHOLD = 0.97;

/** overallSimilarity above this (but below critical) triggers severity=warning. */
export const WARNING_SIMILARITY_THRESHOLD = 0.92;

// --------------------------------------------------------------------------- //
// Helpers                                                                     //
// --------------------------------------------------------------------------- //

/** Default trait value used when personality_profile lacks an entry. */
const TRAIT_DEFAULT = 0.5;

/** Pull a community's personality vector in canonical trait order. */
function personalityVector(c: CommunityConfigInput): number[] {
  const profile = c.personality_profile ?? {};
  return PERSONALITY_TRAITS.map((t) => {
    const v = (profile as Record<string, number | undefined>)[t];
    return typeof v === "number" ? v : TRAIT_DEFAULT;
  });
}

/** Cosine similarity between two equal-length vectors. */
function cosineSimilarity(a: number[], b: number[]): number {
  let dot = 0;
  let normA = 0;
  let normB = 0;
  for (let i = 0; i < a.length; i++) {
    dot += a[i] * b[i];
    normA += a[i] * a[i];
    normB += b[i] * b[i];
  }
  if (normA === 0 || normB === 0) return 0;
  return dot / (Math.sqrt(normA) * Math.sqrt(normB));
}

/** Coefficient of variation = stdDev / mean. Returns 0 when mean is 0. */
function coefficientOfVariation(values: number[]): number {
  if (values.length === 0) return 0;
  const mean = values.reduce((s, v) => s + v, 0) / values.length;
  if (mean === 0) return 0;
  const variance =
    values.reduce((s, v) => s + (v - mean) ** 2, 0) / values.length;
  const stdDev = Math.sqrt(variance);
  return stdDev / mean;
}

/** Display name fallback for a community. */
function displayName(c: CommunityConfigInput): string {
  return c.name?.trim() || c.id || "(unnamed)";
}

// --------------------------------------------------------------------------- //
// Public API                                                                  //
// --------------------------------------------------------------------------- //

/**
 * Analyze community personality similarity and return a structured report.
 *
 * @spec docs/spec/25_COMMUNITY_INSIGHT_SPEC.md#csi-01
 */
export function analyzeCommunitySimilarity(
  communities: CommunityConfigInput[],
): SimilarityReport {
  // Empty / single community → nothing to compare.
  if (communities.length < 2) {
    return {
      overallSimilarity: 0,
      perTrait: emptyTraitRecord(),
      similarPairs: [],
      severity: "ok",
      suggestions: [],
    };
  }

  // Per-trait CV — measures spread of one trait across all communities.
  const perTrait = emptyTraitRecord();
  for (const trait of PERSONALITY_TRAITS) {
    const values = communities.map((c) => {
      const v = (c.personality_profile as Record<string, number | undefined>)?.[trait];
      return typeof v === "number" ? v : TRAIT_DEFAULT;
    });
    perTrait[trait] = coefficientOfVariation(values);
  }

  // Pairwise cosine similarity over the 5-dim personality vectors.
  const vectors = communities.map(personalityVector);
  const similarPairs: SimilarPair[] = [];
  let totalSimilarity = 0;
  let pairCount = 0;
  for (let i = 0; i < communities.length; i++) {
    for (let j = i + 1; j < communities.length; j++) {
      const sim = cosineSimilarity(vectors[i], vectors[j]);
      totalSimilarity += sim;
      pairCount++;
      if (sim > SIMILAR_PAIR_THRESHOLD) {
        similarPairs.push({
          a: displayName(communities[i]),
          b: displayName(communities[j]),
          similarity: sim,
        });
      }
    }
  }

  const overallSimilarity = pairCount > 0 ? totalSimilarity / pairCount : 0;

  const severity: SimilaritySeverity =
    overallSimilarity > CRITICAL_SIMILARITY_THRESHOLD
      ? "critical"
      : overallSimilarity > WARNING_SIMILARITY_THRESHOLD
        ? "warning"
        : "ok";

  const suggestions = buildSuggestions({
    severity,
    overallSimilarity,
    perTrait,
    similarPairs,
  });

  return {
    overallSimilarity,
    perTrait,
    similarPairs,
    severity,
    suggestions,
  };
}

// --------------------------------------------------------------------------- //
// Suggestion builder                                                          //
// --------------------------------------------------------------------------- //

interface SuggestionInput {
  severity: SimilaritySeverity;
  overallSimilarity: number;
  perTrait: Record<PersonalityTrait, number>;
  similarPairs: SimilarPair[];
}

function buildSuggestions(input: SuggestionInput): string[] {
  if (input.severity === "ok") return [];

  const out: string[] = [];
  const pct = Math.round(input.overallSimilarity * 100);
  out.push(
    `Communities are ${pct}% similar on personality traits. ` +
      `Diffusion will likely produce uniform behavior across communities.`,
  );

  // Find the trait with the lowest CV — that's the one to differentiate first.
  const sorted = (Object.entries(input.perTrait) as [PersonalityTrait, number][])
    .sort((a, b) => a[1] - b[1]);
  const flatTrait = sorted[0]?.[0];
  if (flatTrait != null) {
    out.push(
      `Consider increasing the spread of "${flatTrait}" — current CV is ` +
        `${sorted[0][1].toFixed(3)} (lower = less variation).`,
    );
  }

  if (input.similarPairs.length > 0) {
    const top = input.similarPairs
      .slice(0, 3)
      .map((p) => `${p.a} ↔ ${p.b}`)
      .join(", ");
    out.push(
      `${input.similarPairs.length} pair${
        input.similarPairs.length > 1 ? "s are" : " is"
      } nearly identical: ${top}`,
    );
  }

  out.push(
    "Recommended baselines: skeptic.skepticism ≥ 0.80, " +
      "early_adopter.openness ≥ 0.80, influencer.social_influence ≥ 0.85.",
  );

  return out;
}

function emptyTraitRecord(): Record<PersonalityTrait, number> {
  return {
    openness: 0,
    skepticism: 0,
    trend_following: 0,
    brand_loyalty: 0,
    social_influence: 0,
  };
}
