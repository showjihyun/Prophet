/**
 * Shared sentiment colour + delta-formatting helpers for the Opinions hierarchy.
 *
 * Centralises the ±0.1 threshold and the CSS-variable mapping that previously
 * lived as duplicated ternaries inside three opinion pages.
 *
 * @spec docs/spec/27_OPINIONS_SPEC.md#opinions-sentiment-color
 */

export type SentimentTone = "positive" | "negative" | "neutral";

const POS_THRESHOLD = 0.1;
const NEG_THRESHOLD = -0.1;

/** Bucket a numeric sentiment into a tone using ±0.1 thresholds. */
export function sentimentTone(value: number): SentimentTone {
  if (value > POS_THRESHOLD) return "positive";
  if (value < NEG_THRESHOLD) return "negative";
  return "neutral";
}

/** Map a numeric sentiment to a Tailwind text-colour class (CSS vars). */
export function sentimentTextClass(value: number): string {
  switch (sentimentTone(value)) {
    case "positive":
      return "text-[var(--sentiment-positive)]";
    case "negative":
      return "text-[var(--destructive)]";
    default:
      return "text-[var(--muted-foreground)]";
  }
}

/**
 * Format a delta diff for stat-card "change" labels.
 *
 *  formatDelta(0.08, "from prev step") → "+0.08 from prev step"
 *  formatDelta(-12, "today")            → "-12 today"
 *  formatDelta(0)                       → "no change"
 *
 * The numeric portion is formatted with up to 2 decimals when |diff| < 10,
 * otherwise as an integer.
 */
export function formatDelta(diff: number, suffix?: string): string {
  if (diff === 0) return "no change";
  const abs = Math.abs(diff);
  const num = abs < 10 ? diff.toFixed(2) : Math.round(diff).toString();
  const sign = diff > 0 ? "+" : "";
  return suffix ? `${sign}${num} ${suffix}` : `${sign}${num}`;
}

/**
 * Map a delta sign to a StatCard `changeType`.
 *
 * `inverted = true` flips the meaning — used for metrics like polarization
 * where a *decrease* is good news.
 */
export function deltaChangeType(
  diff: number,
  inverted = false,
): "positive" | "negative" | "neutral" {
  if (diff === 0) return "neutral";
  const positive = inverted ? diff < 0 : diff > 0;
  return positive ? "positive" : "negative";
}
