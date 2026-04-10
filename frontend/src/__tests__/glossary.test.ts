/**
 * glossary — unit tests for the central technical-term glossary.
 *
 * Validates structure (every entry has label + non-empty text),
 * key uniqueness (handled by TS already, but spot-checked at runtime),
 * and that the type narrowing works as expected.
 */
import { describe, it, expect } from "vitest";
import { GLOSSARY, type GlossaryTerm } from "@/config/glossary";

describe("GLOSSARY", () => {
  it("has at least 25 entries", () => {
    // Ensures the glossary stays meaningful — if entries get accidentally
    // deleted, this catches it.
    expect(Object.keys(GLOSSARY).length).toBeGreaterThanOrEqual(25);
  });

  describe("entry shape", () => {
    const entries = Object.entries(GLOSSARY) as Array<[GlossaryTerm, { label: string; text: string }]>;

    it.each(entries)("'%s' has a non-empty label", (_key, entry) => {
      expect(entry.label).toBeTruthy();
      expect(typeof entry.label).toBe("string");
      expect(entry.label.length).toBeGreaterThan(0);
    });

    it.each(entries)("'%s' has a non-empty text", (_key, entry) => {
      expect(entry.text).toBeTruthy();
      expect(typeof entry.text).toBe("string");
      expect(entry.text.length).toBeGreaterThan(0);
    });

    it.each(entries)("'%s' text ends with a period", (_key, entry) => {
      // Style guide: entries should be complete sentences.
      expect(entry.text.trimEnd()).toMatch(/[.!?]$/);
    });
  });

  describe("required core terms", () => {
    // These are referenced from production components. If any disappear,
    // the corresponding HelpTooltip silently shows nothing.
    const REQUIRED_TERMS: GlossaryTerm[] = [
      "totalSteps",
      "finalAdoption",
      "finalSentiment",
      "emergentEvents",
      "topCommunity",
      "adoptionCurve",
      "keyEvents",
      "activeAgents",
      "sentimentDistribution",
      "polarization",
      "cascadeDepth",
      "cascadeWidth",
      "influencer",
      "influenceScore",
      "community",
      "viralCascade",
      "diffusionWaveTimeline",
    ];

    it.each(REQUIRED_TERMS)("'%s' exists in the glossary", (term) => {
      expect(GLOSSARY[term]).toBeDefined();
    });
  });

  describe("type guarantees", () => {
    it("GlossaryTerm narrows to a string union", () => {
      // Compile-time check via runtime: a known key must satisfy the type.
      const known: GlossaryTerm = "polarization";
      expect(GLOSSARY[known]).toBeDefined();
    });
  });
});
