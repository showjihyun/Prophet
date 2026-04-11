/**
 * FormProgressBanner — required-field progress + Quick Start toggle.
 *
 * @spec docs/spec/07_FRONTEND_SPEC.md#campaign-form-progress
 *
 * Sits at the top of the CampaignSetupPage so users immediately see:
 *   1. How many required fields are still missing
 *   2. A "Quick Start" toggle that hides advanced sections until they
 *      want to tune them
 *
 * This fixes the pre-existing UX gap where users couldn't tell which
 * fields were mandatory and had to read every section before knowing
 * whether they could submit.
 */
import { memo } from "react";
import { Check, Settings2 } from "lucide-react";

export interface RequiredFieldCheck {
  /** Short label shown in the banner when the field is incomplete. */
  label: string;
  /** True when the field is filled in (user can move on). */
  satisfied: boolean;
}

interface FormProgressBannerProps {
  /** Required fields in display order. */
  fields: RequiredFieldCheck[];
  /** Whether the "Quick Start" mode (hide advanced sections) is active. */
  quickStart: boolean;
  /** Toggle the Quick Start mode. */
  onToggleQuickStart: () => void;
}

function FormProgressBanner({
  fields,
  quickStart,
  onToggleQuickStart,
}: FormProgressBannerProps) {
  const total = fields.length;
  const completed = fields.filter((f) => f.satisfied).length;
  const ratio = total === 0 ? 0 : completed / total;
  const percent = Math.round(ratio * 100);
  const allComplete = completed === total;

  return (
    <div
      data-testid="form-progress-banner"
      className="rounded-lg border border-[var(--border)] bg-[var(--card)] p-4 flex flex-col gap-3"
    >
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 min-w-0">
          {allComplete ? (
            <span
              data-testid="form-progress-complete"
              className="flex items-center gap-1.5 text-emerald-500 text-sm font-medium"
            >
              <Check className="w-4 h-4" />
              All required fields completed
            </span>
          ) : (
            <span
              data-testid="form-progress-count"
              className="text-sm font-medium text-[var(--foreground)]"
            >
              {completed} / {total} required fields
            </span>
          )}
        </div>
        <button
          type="button"
          onClick={onToggleQuickStart}
          data-testid="quick-start-toggle"
          aria-pressed={quickStart}
          className={`shrink-0 flex items-center gap-1.5 px-3 h-8 rounded-md text-xs font-medium transition-colors ${
            quickStart
              ? "bg-[var(--primary)] text-[var(--primary-foreground)]"
              : "bg-[var(--secondary)] text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
          }`}
        >
          <Settings2 className="w-3.5 h-3.5" />
          {quickStart ? "Quick Start ON" : "Quick Start"}
        </button>
      </div>

      {/* Progress bar */}
      <div
        className="h-1 bg-[var(--secondary)] rounded-full overflow-hidden"
        role="progressbar"
        aria-valuenow={percent}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={`${completed} of ${total} required fields completed`}
      >
        <div
          data-testid="form-progress-bar-fill"
          className="h-full bg-[var(--primary)] transition-all"
          style={{ width: `${percent}%` }}
        />
      </div>

      {/* Per-field checklist (only the incomplete ones, to stay compact) */}
      {!allComplete && (
        <ul
          data-testid="form-progress-missing"
          className="flex flex-wrap gap-2"
        >
          {fields
            .filter((f) => !f.satisfied)
            .map((f) => (
              <li
                key={f.label}
                className="text-[10px] px-2 py-0.5 rounded bg-[var(--secondary)] text-[var(--muted-foreground)]"
              >
                <span aria-hidden="true" className="text-red-400 mr-0.5">*</span>
                {f.label}
              </li>
            ))}
        </ul>
      )}

      {quickStart && (
        <p className="text-[10px] text-[var(--muted-foreground)] italic">
          Advanced sections (campaign attributes, community configuration,
          advanced settings) are hidden. Toggle off to tune them manually.
        </p>
      )}
    </div>
  );
}

export default memo(FormProgressBanner);
