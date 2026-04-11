/**
 * TargetCommunitiesSection — Section 3 of the Campaign Setup form.
 * Community chip selector.
 *
 * @spec docs/spec/ui/UI_16_CAMPAIGN_SETUP.md#section-3
 */

interface CommunityOption {
  id: string;
  name: string;
  color: string;
}

interface Props {
  options: CommunityOption[];
  selected: Set<string>;
  onToggle: (id: string) => void;
}

export default function TargetCommunitiesSection({ options, selected, onToggle }: Props) {
  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-sm font-medium text-[var(--foreground)]">Target Communities</label>
      <p className="text-xs text-[var(--muted-foreground)]">
        Select none to target all communities
      </p>
      <div className="flex flex-wrap gap-2">
        {options.map((c) => {
          const isSelected = selected.has(c.id);
          return (
            <button
              key={c.id}
              type="button"
              onClick={() => onToggle(c.id)}
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm border transition-colors ${
                isSelected
                  ? "border-transparent text-white"
                  : "border-[var(--border)] text-[var(--muted-foreground)] bg-[var(--card)] hover:bg-[var(--secondary)]"
              }`}
              style={isSelected ? { backgroundColor: c.color } : undefined}
            >
              <span
                className="w-2 h-2 rounded-full"
                style={{ backgroundColor: isSelected ? "white" : c.color }}
              />
              {c.name}
            </button>
          );
        })}
      </div>
    </div>
  );
}
