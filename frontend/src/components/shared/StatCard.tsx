/**
 * StatCard — Reusable summary stat card for sub-pages.
 * @spec docs/spec/ui/UI_02_COMMUNITIES_DETAIL.md#summary-stats
 * @spec docs/spec/ui/UI_03_TOP_INFLUENCERS.md#summary-stats
 * @spec docs/spec/ui/UI_05_GLOBAL_METRICS.md#summary-stats
 */
import type { ReactNode } from "react";

interface StatCardProps {
  label: string;
  value: string | number;
  change?: string;
  changeType?: "positive" | "negative" | "neutral";
  icon?: ReactNode;
}

const changeColors: Record<string, string> = {
  positive: "text-[var(--sentiment-positive)] bg-[var(--sentiment-positive)]/10",
  negative: "text-[var(--destructive)] bg-[var(--destructive)]/10",
  neutral: "text-[var(--muted-foreground)] bg-[var(--secondary)]",
};

export default function StatCard({
  label,
  value,
  change,
  changeType = "neutral",
  icon,
}: StatCardProps) {
  return (
    <div
      data-testid="stat-card"
      className="bg-[var(--card)] rounded-lg border border-[var(--border)] shadow-sm p-4 flex flex-col gap-2 hover:scale-[1.02] transition-transform"
    >
      <div className="flex items-center justify-between">
        <span className="text-xs font-normal text-[var(--muted-foreground)]">{label}</span>
        {icon && <span className="text-[var(--muted-foreground)]">{icon}</span>}
      </div>
      <span className="text-[28px] font-bold leading-tight text-[var(--foreground)]">
        {value}
      </span>
      {change && (
        <span
          className={`text-[11px] font-medium px-2 py-0.5 rounded-full w-fit ${changeColors[changeType]}`}
        >
          {change}
        </span>
      )}
    </div>
  );
}
