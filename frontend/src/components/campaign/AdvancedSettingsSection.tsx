/**
 * AdvancedSettingsSection — Section 6 of the Campaign Setup form.
 * Max steps, random seed, LLM provider, SLM/LLM ratio.
 *
 * @spec docs/spec/ui/UI_16_CAMPAIGN_SETUP.md#section-6
 */

interface Props {
  maxSteps: number;
  onMaxStepsChange: (value: number) => void;
  randomSeed: number;
  onRandomSeedChange: (value: number) => void;
  llmProvider: string;
  onLlmProviderChange: (value: string) => void;
  slmLlmRatio: number;
  onSlmLlmRatioChange: (value: number) => void;
}

export default function AdvancedSettingsSection({
  maxSteps,
  onMaxStepsChange,
  randomSeed,
  onRandomSeedChange,
  llmProvider,
  onLlmProviderChange,
  slmLlmRatio,
  onSlmLlmRatioChange,
}: Props) {
  return (
    <details className="border border-[var(--border)] rounded-lg bg-[var(--card)]">
      <summary className="px-4 py-3 text-sm font-medium text-[var(--foreground)] cursor-pointer select-none">
        Advanced Settings
      </summary>
      <div className="px-4 pb-4 flex flex-col gap-4 border-t border-[var(--border)] pt-4">
        <div className="flex flex-col gap-1.5">
          <label htmlFor="adv-max-steps" className="text-sm font-medium text-[var(--muted-foreground)]">
            Max Steps (simulation days)
          </label>
          <input
            id="adv-max-steps"
            type="number"
            value={maxSteps}
            onChange={(e) => onMaxStepsChange(Number(e.target.value))}
            min="1"
            max="1000"
            className="h-10 px-3 text-sm border border-[var(--border)] rounded-md bg-[var(--card)] focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
          />
        </div>
        <div className="flex flex-col gap-1.5">
          <label htmlFor="adv-random-seed" className="text-sm font-medium text-[var(--muted-foreground)]">
            Random Seed
          </label>
          <input
            id="adv-random-seed"
            type="number"
            value={randomSeed}
            onChange={(e) => onRandomSeedChange(Number(e.target.value))}
            className="h-10 px-3 text-sm border border-[var(--border)] rounded-md bg-[var(--card)] focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
          />
        </div>
        <div className="flex flex-col gap-1.5">
          <label htmlFor="adv-llm-provider" className="text-sm font-medium text-[var(--muted-foreground)]">
            LLM Provider
          </label>
          <select
            id="adv-llm-provider"
            value={llmProvider}
            onChange={(e) => onLlmProviderChange(e.target.value)}
            className="h-10 px-3 text-sm border border-[var(--border)] rounded-md bg-[var(--card)] focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
          >
            <option value="ollama">Ollama (Local)</option>
            <option value="claude">Claude API</option>
            <option value="openai">OpenAI API</option>
          </select>
        </div>
        <div className="flex flex-col gap-1.5">
          <label htmlFor="adv-slm-ratio" className="text-sm font-medium text-[var(--muted-foreground)]">
            SLM / LLM Ratio: {slmLlmRatio}% SLM / {100 - slmLlmRatio}% LLM
          </label>
          <input
            id="adv-slm-ratio"
            type="range"
            min="0"
            max="100"
            value={slmLlmRatio}
            onChange={(e) => onSlmLlmRatioChange(Number(e.target.value))}
            className="w-full accent-[var(--foreground)]"
          />
          <div className="flex justify-between text-[10px] text-[var(--muted-foreground)]">
            <span>100% LLM</span>
            <span>100% SLM</span>
          </div>
        </div>
      </div>
    </details>
  );
}
