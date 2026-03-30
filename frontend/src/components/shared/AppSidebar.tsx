/**
 * AppSidebar — Shared sidebar navigation for project-level pages.
 * @spec docs/spec/ui/UI_06_PROJECTS_LIST.md#app-sidebar
 * @spec docs/spec/ui/UI_07_PROJECT_SCENARIOS.md#app-sidebar
 */
import { useLocation, useNavigate } from "react-router-dom";
import {
  Brain,
  FolderOpen,
  Play,
  BarChart3,
  Settings,
  Users,
  Crown,
  MessageSquare,
  PlusCircle,
} from "lucide-react";
import ThemeToggle from './ThemeToggle';

interface AppSidebarProps {
  activePath?: string;
}

const NAV_ITEMS = [
  { icon: Play, label: "Simulation", href: "/" },
  { icon: FolderOpen, label: "Projects", href: "/projects" },
  { icon: PlusCircle, label: "New Simulation", href: "/setup" },
  { icon: Users, label: "Communities", href: "/communities" },
  { icon: Crown, label: "Influencers", href: "/influencers" },
  { icon: BarChart3, label: "Global Insights", href: "/metrics" },
  { icon: MessageSquare, label: "Opinions", href: "/opinions" },
  { icon: Settings, label: "Settings", href: "/settings" },
];

export default function AppSidebar({ activePath }: AppSidebarProps) {
  const location = useLocation();
  const navigate = useNavigate();

  const currentPath = activePath ?? location.pathname;

  function isActive(href: string): boolean {
    if (href === "/projects") {
      return currentPath === "/projects" || currentPath.startsWith("/projects/");
    }
    return currentPath === href;
  }

  return (
    <aside
      data-testid="app-sidebar"
      className="flex flex-col shrink-0 border-r border-[var(--border)] bg-[var(--card)]"
      style={{ width: 256 }}
    >
      {/* Logo */}
      <div className="flex items-center gap-2.5 px-4 h-14 border-b border-[var(--border)]">
        <Brain className="w-5 h-5 text-[var(--foreground)]" />
        <span className="text-base font-bold text-[var(--foreground)]">MCASP Prophet</span>
      </div>

      {/* Navigation */}
      <nav className="flex flex-col gap-1 p-3 flex-1">
        {NAV_ITEMS.map((item) => {
          const active = isActive(item.href);
          return (
            <button
              key={item.href}
              onClick={() => navigate(item.href)}
              className={[
                "interactive flex items-center gap-3 rounded-md text-sm font-medium transition-colors",
                "h-10 px-3",
                active
                  ? "bg-[var(--accent)] text-[var(--foreground)]"
                  : "text-[var(--muted-foreground)] hover:bg-[var(--accent)] hover:text-[var(--foreground)]",
              ].join(" ")}
            >
              <item.icon className="w-4 h-4" />
              {item.label}
            </button>
          );
        })}
      </nav>

      {/* Theme toggle */}
      <div className="mt-auto pt-4 border-t border-[var(--border)] flex items-center justify-between px-4 pb-3">
        <span className="text-xs text-[var(--muted-foreground)]">Theme</span>
        <ThemeToggle />
      </div>
    </aside>
  );
}
