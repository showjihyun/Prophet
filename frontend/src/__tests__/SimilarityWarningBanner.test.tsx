/**
 * SimilarityWarningBanner component tests.
 * @spec docs/spec/25_COMMUNITY_INSIGHT_SPEC.md#csi-ac-06-08
 */
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect } from "vitest";

import SimilarityWarningBanner from "@/components/campaign/SimilarityWarningBanner";
import type { SimilarityReport } from "@/components/campaign/communitySimilarity";

function report(overrides: Partial<SimilarityReport> = {}): SimilarityReport {
  return {
    overallSimilarity: 0.5,
    perTrait: {
      openness: 0.4,
      skepticism: 0.3,
      trend_following: 0.5,
      brand_loyalty: 0.2,
      social_influence: 0.6,
    },
    similarPairs: [],
    severity: "ok",
    suggestions: [],
    ...overrides,
  };
}

describe("<SimilarityWarningBanner />", () => {
  it("renders nothing when severity is ok", () => {
    const { container } = render(
      <SimilarityWarningBanner report={report({ severity: "ok" })} />,
    );
    expect(container.firstChild).toBeNull();
  });

  it("renders amber banner for warning severity", () => {
    render(
      <SimilarityWarningBanner
        report={report({
          severity: "warning",
          overallSimilarity: 0.94,
          suggestions: ["Diffusion will collapse"],
        })}
      />,
    );
    const banner = screen.getByTestId("similarity-warning");
    expect(banner).toBeInTheDocument();
    expect(banner).toHaveAttribute("data-severity", "warning");
    expect(banner).toHaveAttribute("role", "alert");
    // The header shows "94% similar" — at least one match.
    expect(screen.getAllByText(/94%/).length).toBeGreaterThanOrEqual(1);
  });

  it("renders red banner with 'collapse' headline for critical severity", () => {
    render(
      <SimilarityWarningBanner
        report={report({
          severity: "critical",
          overallSimilarity: 0.99,
          suggestions: ["Communities are very similar"],
        })}
      />,
    );
    const banner = screen.getByTestId("similarity-warning");
    expect(banner).toHaveAttribute("data-severity", "critical");
    expect(screen.getByText(/collapse/i)).toBeInTheDocument();
    expect(screen.getAllByText(/99%/).length).toBeGreaterThanOrEqual(1);
  });

  it("toggles per-trait CV table when expand button is clicked", () => {
    render(
      <SimilarityWarningBanner
        report={report({ severity: "warning", overallSimilarity: 0.93 })}
      />,
    );

    // Table is collapsed initially
    expect(
      screen.queryByTestId("similarity-warning-trait-table"),
    ).not.toBeInTheDocument();

    // Click toggle
    fireEvent.click(screen.getByTestId("similarity-warning-toggle"));

    // Table now visible with all 5 traits
    const table = screen.getByTestId("similarity-warning-trait-table");
    expect(table).toBeInTheDocument();
    expect(table).toHaveTextContent("openness");
    expect(table).toHaveTextContent("skepticism");
    expect(table).toHaveTextContent("trend_following");
    expect(table).toHaveTextContent("brand_loyalty");
    expect(table).toHaveTextContent("social_influence");

    // Click toggle again — table collapses
    fireEvent.click(screen.getByTestId("similarity-warning-toggle"));
    expect(
      screen.queryByTestId("similarity-warning-trait-table"),
    ).not.toBeInTheDocument();
  });

  it("renders all suggestions as list items", () => {
    render(
      <SimilarityWarningBanner
        report={report({
          severity: "warning",
          overallSimilarity: 0.93,
          suggestions: [
            "Suggestion one.",
            "Suggestion two.",
            "Suggestion three.",
          ],
        })}
      />,
    );
    expect(screen.getByText(/Suggestion one\./)).toBeInTheDocument();
    expect(screen.getByText(/Suggestion two\./)).toBeInTheDocument();
    expect(screen.getByText(/Suggestion three\./)).toBeInTheDocument();
  });
});
