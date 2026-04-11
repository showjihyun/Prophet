/**
 * SimilarityWarningBanner — pre-flight community differentiation alert.
 *
 * @spec docs/spec/25_COMMUNITY_INSIGHT_SPEC.md#2-similarity-advisor-pre-flight
 *
 * Renders a non-blocking warning when the user's community personality
 * profiles are too similar — high similarity leads to all communities
 * collapsing to the same trajectory in the diffusion engine, which
 * defeats the purpose of multi-community simulation.
 *
 * Severity-aware: warning (amber) vs critical (red). Hidden when severity
 * is "ok" so the form stays clean for properly differentiated configs.
 */
import { memo, useState } from "react";
import { AlertTriangle, ChevronDown, ChevronUp } from "lucide-react";
import type { SimilarityReport } from "./communitySimilarity";

interface SimilarityWarningBannerProps {
  report: SimilarityReport;
}

function SimilarityWarningBanner({ report }: SimilarityWarningBannerProps) {
  const [expanded, setExpanded] = useState(false);

  // Severity=ok → render nothing. The parent doesn't need to gate this;
  // a hidden banner takes zero layout space and keeps the JSX clean.
  if (report.severity === "ok") return null;

  const isCritical = report.severity === "critical";

  const containerClass = isCritical
    ? "border-red-500/40 bg-red-500/10 text-red-200"
    : "border-amber-500/40 bg-amber-500/10 text-amber-200";

  const headlineLabel = isCritical
    ? "Communities virtually identical — diffusion will collapse"
    : "Communities may behave alike";

  return (
    <div
      data-testid="similarity-warning"
      data-severity={report.severity}
      role="alert"
      aria-live="polite"
      className={`rounded-md border p-3 text-xs space-y-2 ${containerClass}`}
    >
      <div className="font-semibold flex items-center gap-2">
        <AlertTriangle className="w-4 h-4" aria-hidden="true" />
        <span>{headlineLabel}</span>
        <span className="ml-auto tabular-nums">
          {Math.round(report.overallSimilarity * 100)}% similar
        </span>
      </div>

      <ul className="space-y-1 list-disc list-inside leading-snug">
        {report.suggestions.map((s, i) => (
          <li key={i}>{s}</li>
        ))}
      </ul>

      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        aria-expanded={expanded}
        data-testid="similarity-warning-toggle"
        className="flex items-center gap-1 text-[10px] opacity-80 hover:opacity-100 transition-opacity"
      >
        {expanded ? (
          <ChevronUp className="w-3 h-3" />
        ) : (
          <ChevronDown className="w-3 h-3" />
        )}
        Per-trait variation
      </button>

      {expanded && (
        <table
          data-testid="similarity-warning-trait-table"
          className="text-[10px] mt-1 w-full"
        >
          <thead>
            <tr className="opacity-60">
              <th className="text-left font-normal pr-2">Trait</th>
              <th className="text-right font-normal">CV</th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(report.perTrait).map(([trait, cv]) => (
              <tr key={trait}>
                <td className="pr-2">{trait}</td>
                <td className="text-right tabular-nums">{cv.toFixed(3)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

export default memo(SimilarityWarningBanner);
