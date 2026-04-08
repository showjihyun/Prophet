/**
 * CampaignAttributesSection — Section 4 of the Campaign Setup form.
 * Three range sliders: controversy, novelty, utility.
 *
 * @spec docs/spec/ui/UI_16_CAMPAIGN_SETUP.md#section-4
 */

interface Props {
  controversy: number;
  onControversyChange: (value: number) => void;
  novelty: number;
  onNoveltyChange: (value: number) => void;
  utility: number;
  onUtilityChange: (value: number) => void;
}

interface SliderProps {
  id: string;
  label: string;
  description: string;
  value: number;
  onChange: (value: number) => void;
}

function AttributeSlider({ id, label, description, value, onChange }: SliderProps) {
  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center justify-between">
        <label htmlFor={id} className="text-sm text-[var(--muted-foreground)]">
          {label}
        </label>
        <span className="text-xs font-mono text-[var(--muted-foreground)]">{value.toFixed(1)}</span>
      </div>
      <input
        id={id}
        type="range"
        min="0"
        max="1"
        step="0.1"
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full accent-[var(--foreground)]"
      />
      <p className="text-[10px] text-[var(--muted-foreground)]">{description}</p>
    </div>
  );
}

export default function CampaignAttributesSection({
  controversy,
  onControversyChange,
  novelty,
  onNoveltyChange,
  utility,
  onUtilityChange,
}: Props) {
  return (
    <div className="flex flex-col gap-4 border border-[var(--border)] rounded-lg bg-[var(--card)] p-4">
      <h2 className="text-sm font-semibold text-[var(--foreground)]">Campaign Attributes</h2>
      <div className="flex flex-col gap-3">
        <AttributeSlider
          id="attr-controversy"
          label="Controversy"
          description="Higher values cause polarization and heated debate"
          value={controversy}
          onChange={onControversyChange}
        />
        <AttributeSlider
          id="attr-novelty"
          label="Novelty"
          description="Higher values increase attention and curiosity"
          value={novelty}
          onChange={onNoveltyChange}
        />
        <AttributeSlider
          id="attr-utility"
          label="Utility"
          description="Higher values increase adoption likelihood"
          value={utility}
          onChange={onUtilityChange}
        />
      </div>
    </div>
  );
}
