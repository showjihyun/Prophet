/**
 * CampaignInfoSection — Section 2 of the Campaign Setup form.
 * Name, budget, channels (multi-select), message.
 *
 * @spec docs/spec/ui/UI_16_CAMPAIGN_SETUP.md#section-2
 */
import { CHANNELS } from "./types";

interface Props {
  name: string;
  onNameChange: (value: string) => void;
  budget: string;
  onBudgetChange: (value: string) => void;
  channels: Set<string>;
  onToggleChannel: (channel: string) => void;
  message: string;
  onMessageChange: (value: string) => void;
}

export default function CampaignInfoSection({
  name,
  onNameChange,
  budget,
  onBudgetChange,
  channels,
  onToggleChannel,
  message,
  onMessageChange,
}: Props) {
  return (
    <>
      <div className="flex flex-col gap-1.5">
        <label htmlFor="campaign-name" className="text-sm font-medium text-[var(--foreground)]">
          Campaign Name
        </label>
        <input
          id="campaign-name"
          type="text"
          value={name}
          onChange={(e) => onNameChange(e.target.value)}
          placeholder="e.g., Q4 Product Launch"
          required
          className="h-10 px-3 text-sm border border-[var(--border)] rounded-md bg-[var(--card)] focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
        />
      </div>

      <div className="flex flex-col gap-1.5">
        <label htmlFor="campaign-budget" className="text-sm font-medium text-[var(--foreground)]">
          Budget ($)
        </label>
        <input
          id="campaign-budget"
          type="number"
          value={budget}
          onChange={(e) => onBudgetChange(e.target.value)}
          placeholder="10000"
          min="0"
          className="h-10 px-3 text-sm border border-[var(--border)] rounded-md bg-[var(--card)] focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
        />
      </div>

      <div className="flex flex-col gap-1.5">
        <label className="text-sm font-medium text-[var(--foreground)]">Channels</label>
        <div className="flex flex-wrap gap-3">
          {CHANNELS.map((ch) => (
            <label key={ch} className="flex items-center gap-2 text-sm cursor-pointer">
              <input
                type="checkbox"
                checked={channels.has(ch)}
                onChange={() => onToggleChannel(ch)}
                className="w-4 h-4 rounded border-[var(--border)] text-[var(--foreground)] focus:ring-[var(--ring)]"
              />
              {ch}
            </label>
          ))}
        </div>
      </div>

      <div className="flex flex-col gap-1.5">
        <label htmlFor="campaign-message" className="text-sm font-medium text-[var(--foreground)]">
          Campaign Message
        </label>
        <textarea
          id="campaign-message"
          value={message}
          onChange={(e) => onMessageChange(e.target.value)}
          placeholder="Enter the campaign message to simulate..."
          rows={4}
          className="px-3 py-2 text-sm border border-[var(--border)] rounded-md bg-[var(--card)] focus:outline-none focus:ring-2 focus:ring-[var(--ring)] resize-y"
        />
      </div>
    </>
  );
}
