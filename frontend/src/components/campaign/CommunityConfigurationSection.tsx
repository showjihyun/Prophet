/**
 * CommunityConfigurationSection — Section 5 of the Campaign Setup form.
 * Collapsible list of per-community config cards with personality sliders.
 *
 * @spec docs/spec/ui/UI_16_CAMPAIGN_SETUP.md#section-5
 */
import type { CommunityConfigInput } from "../../api/client";
import {
  AGENT_TYPES,
  COMMUNITY_COLORS,
  PERSONALITY_KEYS,
  PERSONALITY_LABELS,
} from "./types";

interface Props {
  communities: CommunityConfigInput[];
  open: boolean;
  onToggleOpen: (open: boolean) => void;
  onLoadTemplates: () => void;
  onUpdateCommunity: (index: number, updates: Partial<CommunityConfigInput>) => void;
  onUpdatePersonality: (index: number, key: string, value: number) => void;
  onRemoveCommunity: (index: number) => void;
  onAddCommunity: () => void;
}

export default function CommunityConfigurationSection({
  communities,
  open,
  onToggleOpen,
  onLoadTemplates,
  onUpdateCommunity,
  onUpdatePersonality,
  onRemoveCommunity,
  onAddCommunity,
}: Props) {
  return (
    <details
      open={open}
      onToggle={(e) => onToggleOpen((e.target as HTMLDetailsElement).open)}
      className="border border-[var(--border)] rounded-lg bg-[var(--card)]"
    >
      <summary className="px-4 py-3 text-sm font-medium text-[var(--foreground)] cursor-pointer select-none flex items-center justify-between">
        <span>Community Configuration ({communities.length} communities)</span>
      </summary>
      <div className="px-4 pb-4 border-t border-[var(--border)] pt-4 flex flex-col gap-4">
        <button
          type="button"
          onClick={onLoadTemplates}
          className="self-start px-3 py-1.5 text-xs font-medium border border-[var(--border)] rounded-md bg-[var(--secondary)] hover:bg-[var(--accent)] transition-colors"
        >
          Load from Templates
        </button>

        {communities.map((comm, idx) => (
          <CommunityCard
            key={idx}
            community={comm}
            index={idx}
            canRemove={communities.length > 1}
            onUpdate={(updates) => onUpdateCommunity(idx, updates)}
            onUpdatePersonality={(key, value) => onUpdatePersonality(idx, key, value)}
            onRemove={() => onRemoveCommunity(idx)}
          />
        ))}

        <button
          type="button"
          onClick={onAddCommunity}
          className="self-start px-3 py-1.5 text-xs font-medium border border-dashed border-[var(--border)] rounded-md hover:bg-[var(--secondary)] transition-colors"
        >
          + Add Community
        </button>
      </div>
    </details>
  );
}

interface CommunityCardProps {
  community: CommunityConfigInput;
  index: number;
  canRemove: boolean;
  onUpdate: (updates: Partial<CommunityConfigInput>) => void;
  onUpdatePersonality: (key: string, value: number) => void;
  onRemove: () => void;
}

function CommunityCard({
  community,
  index,
  canRemove,
  onUpdate,
  onUpdatePersonality,
  onRemove,
}: CommunityCardProps) {
  return (
    <div
      className="border border-[var(--border)] rounded-lg p-4 flex flex-col gap-3"
      style={{
        borderLeftColor: COMMUNITY_COLORS[index % COMMUNITY_COLORS.length],
        borderLeftWidth: 3,
      }}
    >
      <div className="flex items-center justify-between">
        <span className="text-sm font-semibold text-[var(--foreground)]">
          {community.name || `Community ${index + 1}`}
        </span>
        <button
          type="button"
          onClick={onRemove}
          disabled={!canRemove}
          className="text-xs text-[var(--destructive)] hover:underline disabled:opacity-30 disabled:cursor-not-allowed"
        >
          Remove
        </button>
      </div>

      <div className="grid grid-cols-3 gap-3">
        <div className="flex flex-col gap-1">
          <label className="text-xs text-[var(--muted-foreground)]">Name</label>
          <input
            type="text"
            value={community.name}
            onChange={(e) => onUpdate({ name: e.target.value })}
            className="h-8 px-2 text-xs border border-[var(--border)] rounded bg-[var(--background)] focus:outline-none focus:ring-1 focus:ring-[var(--ring)]"
          />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs text-[var(--muted-foreground)]">Agent Type</label>
          <select
            value={community.agent_type}
            onChange={(e) => onUpdate({ agent_type: e.target.value })}
            className="h-8 px-2 text-xs border border-[var(--border)] rounded bg-[var(--background)] focus:outline-none focus:ring-1 focus:ring-[var(--ring)]"
          >
            {AGENT_TYPES.map((t) => (
              <option key={t} value={t}>
                {t.replace("_", " ")}
              </option>
            ))}
          </select>
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs text-[var(--muted-foreground)]">Agent Count</label>
          <input
            type="number"
            value={community.size}
            onChange={(e) =>
              onUpdate({ size: Math.max(10, Math.min(5000, Number(e.target.value))) })
            }
            min={10}
            max={5000}
            className="h-8 px-2 text-xs border border-[var(--border)] rounded bg-[var(--background)] focus:outline-none focus:ring-1 focus:ring-[var(--ring)]"
          />
        </div>
      </div>

      <div className="flex flex-col gap-2">
        <span className="text-xs font-medium text-[var(--muted-foreground)]">Personality Profile</span>
        {PERSONALITY_KEYS.map((key) => {
          // `personality_profile` is optional + partial on the wire — the
          // backend fills any missing trait with 0.5 at agent generation,
          // so we mirror that default in the slider UI when the user
          // hasn't configured a specific trait yet.
          const traitValue =
            community.personality_profile?.[
              key as keyof NonNullable<typeof community.personality_profile>
            ] ?? 0.5;
          return (
            <div key={key} className="flex items-center gap-2">
              <span className="text-[11px] text-[var(--muted-foreground)] w-28 shrink-0">
                {PERSONALITY_LABELS[key]}
              </span>
              <input
                type="range"
                min="0"
                max="1"
                step="0.05"
                value={traitValue}
                onChange={(e) => onUpdatePersonality(key, Number(e.target.value))}
                className="flex-1 accent-[var(--foreground)] h-1"
              />
              <span className="text-[10px] font-mono text-[var(--muted-foreground)] w-8 text-right">
                {traitValue.toFixed(2)}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
