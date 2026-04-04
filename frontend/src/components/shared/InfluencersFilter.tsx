/**
 * InfluencersFilter — Filter popover for the Top Influencers page.
 * @spec docs/spec/ui/UI_09_INFLUENCERS_FILTER.md
 */
import { useState, useEffect, useRef, useCallback } from "react";
import { type FilterState, DEFAULT_FILTERS } from "./influencersFilterTypes";

interface InfluencersFilterProps {
  isOpen: boolean;
  onClose: () => void;
  onApply: (filters: FilterState) => void;
  currentFilters: FilterState;
}

const COMMUNITIES = [
  { name: "Alpha", color: "var(--community-alpha)" },
  { name: "Beta", color: "var(--community-beta)" },
  { name: "Gamma", color: "var(--community-gamma)" },
  { name: "Delta", color: "var(--community-delta)" },
  { name: "Bridge", color: "var(--community-bridge)" },
];

export default function InfluencersFilter({
  isOpen,
  onClose,
  onApply,
  currentFilters,
}: InfluencersFilterProps) {
  const [draft, setDraft] = useState<FilterState>(currentFilters);
  const panelRef = useRef<HTMLDivElement>(null);

  // Sync draft when popover opens.
  // Deferred via queueMicrotask to avoid calling setState synchronously
  // inside the effect body (react-hooks/set-state-in-effect).
  useEffect(() => {
    if (isOpen) {
      queueMicrotask(() => setDraft(currentFilters));
    }
  }, [isOpen, currentFilters]);

  // Auto-focus first interactive element on open
  useEffect(() => {
    if (!isOpen || !panelRef.current) return;
    const firstFocusable = panelRef.current.querySelector<HTMLElement>(
      'button, input, select, textarea, [tabindex]:not([tabindex="-1"])',
    );
    firstFocusable?.focus();
  }, [isOpen]);

  // Close on Escape
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    },
    [onClose],
  );

  useEffect(() => {
    if (!isOpen) return;
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, handleKeyDown]);

  if (!isOpen) return null;

  const toggleCommunity = (name: string) => {
    setDraft((prev) => ({
      ...prev,
      communities: prev.communities.includes(name)
        ? prev.communities.filter((c) => c !== name)
        : [...prev.communities, name],
    }));
  };

  const handleReset = () => {
    setDraft({ ...DEFAULT_FILTERS });
  };

  const handleApply = () => {
    onApply(draft);
  };

  const scoreInvalid = draft.scoreMin > draft.scoreMax;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40"
        onClick={onClose}
      />

      {/* Popover panel */}
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-label="Filter Influencers"
        className="absolute z-50 mt-2 rounded-lg border shadow-lg"
        style={{
          width: 600,
          maxHeight: 700,
          backgroundColor: "var(--card)",
          borderColor: "var(--border)",
          boxShadow: "0 4px 24px rgba(0,0,0,0.12)",
        }}
      >
        {/* Header */}
        <div
          className="flex items-center justify-between border-b px-6 py-4"
          style={{ borderColor: "var(--border)" }}
        >
          <h3 className="text-base font-semibold" style={{ color: "var(--foreground)" }}>
            Filter Influencers
          </h3>
          <button
            onClick={onClose}
            className="rounded-md p-1 hover:bg-[var(--secondary)]"
            aria-label="Close filter"
          >
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        {/* Body */}
        <div className="overflow-y-auto p-6 flex flex-col gap-6" style={{ maxHeight: 560 }}>
          {/* Community */}
          <div className="flex flex-col gap-3">
            <label className="text-sm font-medium" style={{ color: "var(--foreground)" }}>
              Community
            </label>
            <div className="flex flex-col gap-3">
              {COMMUNITIES.map((c) => (
                <label key={c.name} className="flex items-center gap-2 cursor-pointer text-sm">
                  <input
                    type="checkbox"
                    checked={draft.communities.includes(c.name)}
                    onChange={() => toggleCommunity(c.name)}
                    className="rounded"
                  />
                  <span
                    className="w-2 h-2 rounded-full"
                    style={{ backgroundColor: c.color }}
                  />
                  {c.name}
                </label>
              ))}
            </div>
          </div>

          {/* Status */}
          <div className="flex flex-col gap-3">
            <label className="text-sm font-medium" style={{ color: "var(--foreground)" }}>
              Status
            </label>
            <div className="flex gap-4">
              {(["all", "active", "idle"] as const).map((s) => (
                <label key={s} className="flex items-center gap-2 cursor-pointer text-sm">
                  <input
                    type="radio"
                    name="status"
                    checked={draft.status === s}
                    onChange={() => setDraft((prev) => ({ ...prev, status: s }))}
                  />
                  {s.charAt(0).toUpperCase() + s.slice(1)}
                </label>
              ))}
            </div>
          </div>

          {/* Influence Score Range */}
          <div className="flex flex-col gap-3">
            <label className="text-sm font-medium" style={{ color: "var(--foreground)" }}>
              Influence Score Range
            </label>
            <div className="flex gap-4">
              <div className="flex flex-col gap-1 flex-1">
                <span className="text-xs" style={{ color: "var(--muted-foreground)" }}>
                  Min
                </span>
                <input
                  type="number"
                  min={0}
                  max={100}
                  value={draft.scoreMin}
                  onChange={(e) =>
                    setDraft((prev) => ({ ...prev, scoreMin: Number(e.target.value) }))
                  }
                  className="h-10 w-full rounded-md border px-3 text-sm"
                  style={{
                    borderColor: scoreInvalid
                      ? "var(--sentiment-negative)"
                      : "var(--border)",
                  }}
                />
              </div>
              <div className="flex flex-col gap-1 flex-1">
                <span className="text-xs" style={{ color: "var(--muted-foreground)" }}>
                  Max
                </span>
                <input
                  type="number"
                  min={0}
                  max={100}
                  value={draft.scoreMax}
                  onChange={(e) =>
                    setDraft((prev) => ({ ...prev, scoreMax: Number(e.target.value) }))
                  }
                  className="h-10 w-full rounded-md border px-3 text-sm"
                  style={{
                    borderColor: scoreInvalid
                      ? "var(--sentiment-negative)"
                      : "var(--border)",
                  }}
                />
              </div>
            </div>
          </div>

          {/* Sentiment */}
          <div className="flex flex-col gap-3">
            <label className="text-sm font-medium" style={{ color: "var(--foreground)" }}>
              Sentiment
            </label>
            <select
              value={draft.sentiment}
              onChange={(e) => setDraft((prev) => ({ ...prev, sentiment: e.target.value }))}
              className="h-10 w-full rounded-md border px-3 text-sm"
              style={{ borderColor: "var(--border)" }}
            >
              <option value="all">All</option>
              <option value="Positive">Positive</option>
              <option value="Neutral">Neutral</option>
              <option value="Negative">Negative</option>
            </select>
          </div>

          {/* Min Connections */}
          <div className="flex flex-col gap-3">
            <label className="text-sm font-medium" style={{ color: "var(--foreground)" }}>
              Min Connections
            </label>
            <input
              type="number"
              min={0}
              value={draft.minConnections}
              onChange={(e) =>
                setDraft((prev) => ({
                  ...prev,
                  minConnections: Math.max(0, Number(e.target.value)),
                }))
              }
              className="h-10 w-full rounded-md border px-3 text-sm"
              style={{ borderColor: "var(--border)" }}
            />
          </div>
        </div>

        {/* Footer */}
        <div
          className="flex items-center justify-between border-t px-6 py-4"
          style={{ borderColor: "var(--border)" }}
        >
          <button
            onClick={handleReset}
            className="rounded-md border px-4 py-2 text-sm font-medium hover:bg-[var(--secondary)]"
            style={{ borderColor: "var(--border)" }}
          >
            Reset
          </button>
          <button
            onClick={handleApply}
            className="rounded-md px-4 py-2 text-sm font-medium text-white"
            style={{ backgroundColor: "var(--primary)" }}
          >
            Apply Filters
          </button>
        </div>
      </div>
    </>
  );
}
