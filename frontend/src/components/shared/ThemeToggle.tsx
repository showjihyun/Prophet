import { Moon, Sun } from 'lucide-react';
import { useSimulationStore } from '../../store/simulationStore';

export default function ThemeToggle() {
  const { theme, toggleTheme } = useSimulationStore();

  return (
    <button
      onClick={toggleTheme}
      className="interactive p-2 rounded-md text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
      aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
      title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
    >
      {theme === 'dark' ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
    </button>
  );
}
