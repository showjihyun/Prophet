/**
 * Small shared icon button used throughout the Simulation Control Bar.
 * @spec docs/spec/ui/UI_01_SIMULATION_MAIN.md#zone-1-simulation-control-bar
 */
import type { ReactNode } from "react";

interface ControlButtonProps {
  icon: ReactNode;
  label: string;
  onClick: () => void;
  testId?: string;
  hidden?: boolean;
  disabled?: boolean;
}

export default function ControlButton({
  icon,
  label,
  onClick,
  testId,
  hidden,
  disabled,
}: ControlButtonProps) {
  return (
    <button
      data-testid={testId}
      onClick={onClick}
      title={label}
      aria-label={label}
      aria-hidden={hidden || undefined}
      tabIndex={hidden ? -1 : undefined}
      disabled={disabled}
      className={`w-8 h-8 flex items-center justify-center rounded-md text-[var(--foreground)] hover:bg-[var(--secondary)] transition-colors disabled:opacity-40 disabled:cursor-not-allowed ${hidden ? "invisible absolute" : ""}`}
    >
      {icon}
    </button>
  );
}
