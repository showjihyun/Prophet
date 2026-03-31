/**
 * AppSidebar — Shared sidebar navigation for project-level pages.
 * @spec docs/spec/ui/UI_06_PROJECTS_LIST.md#app-sidebar
 * @spec docs/spec/ui/UI_07_PROJECT_SCENARIOS.md#app-sidebar
 */
import { useEffect, useState, useCallback } from "react";
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
  Menu,
  X,
  LogOut,
} from "lucide-react";
import ThemeToggle from './ThemeToggle';

interface AppSidebarProps {
  activePath?: string;
}

const NAV_ITEMS = [
  { icon: FolderOpen, label: "Projects", href: "/projects" },
  { icon: Play, label: "Simulation", href: "/simulation" },
  { icon: Users, label: "Communities", href: "/communities" },
  { icon: Crown, label: "Influencers", href: "/influencers" },
  { icon: BarChart3, label: "Global Insights", href: "/metrics" },
  { icon: MessageSquare, label: "Opinions", href: "/opinions" },
  { icon: Settings, label: "Settings", href: "/settings" },
];

function useIsMobile() {
  const [isMobile, setIsMobile] = useState(() => window.matchMedia("(max-width: 768px)").matches);
  useEffect(() => {
    const mq = window.matchMedia("(max-width: 768px)");
    const handler = (e: MediaQueryListEvent) => setIsMobile(e.matches);
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);
  return isMobile;
}

export default function AppSidebar({ activePath }: AppSidebarProps) {
  const location = useLocation();
  const navigate = useNavigate();
  const isMobile = useIsMobile();
  const [collapsed, setCollapsed] = useState(false);
  const [username, setUsername] = useState<string | null>(() => localStorage.getItem("prophet-username"));

  const handleLogout = useCallback(() => {
    localStorage.removeItem("prophet-token");
    localStorage.removeItem("prophet-username");
    setUsername(null);
    navigate("/login");
  }, [navigate]);

  // Auto-collapse on mobile
  useEffect(() => {
    setCollapsed(isMobile);
  }, [isMobile]);

  const currentPath = activePath ?? location.pathname;

  function isActive(href: string): boolean {
    if (href === "/projects") {
      return currentPath === "/projects" || currentPath.startsWith("/projects/");
    }
    if (href === "/simulation") {
      return currentPath === "/simulation";
    }
    return currentPath === href;
  }

  const sidebarWidth = collapsed ? 60 : 256;

  return (
    <aside
      data-testid="app-sidebar"
      className="flex flex-col shrink-0 border-r border-[var(--border)] bg-[var(--card)] transition-all duration-200"
      style={{ width: sidebarWidth }}
    >
      {/* Logo / Hamburger toggle */}
      <div className="flex items-center h-14 border-b border-[var(--border)] px-3 gap-2">
        <button
          onClick={() => setCollapsed((c) => !c)}
          className="interactive p-1.5 rounded-md text-[var(--muted-foreground)] hover:text-[var(--foreground)] shrink-0"
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {collapsed ? <Menu className="w-4 h-4" /> : <X className="w-4 h-4" />}
        </button>
        {!collapsed && (
          <div className="flex items-center gap-2 overflow-hidden">
            <Brain className="w-5 h-5 text-[var(--foreground)] shrink-0" />
            <span className="text-base font-bold text-[var(--foreground)] whitespace-nowrap">MCASP Prophet</span>
          </div>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex flex-col gap-1 p-2 flex-1">
        {NAV_ITEMS.map((item) => {
          const active = isActive(item.href);
          return (
            <button
              key={item.href}
              onClick={() => navigate(item.href)}
              title={collapsed ? item.label : undefined}
              className={[
                "interactive flex items-center rounded-md text-sm font-medium transition-colors h-10",
                collapsed ? "justify-center px-0" : "gap-3 px-3",
                active
                  ? "bg-[var(--accent)] text-[var(--foreground)]"
                  : "text-[var(--muted-foreground)] hover:bg-[var(--accent)] hover:text-[var(--foreground)]",
              ].join(" ")}
            >
              <item.icon className="w-4 h-4 shrink-0" />
              {!collapsed && item.label}
            </button>
          );
        })}
      </nav>

      {/* Footer: user + theme */}
      <div className="mt-auto border-t border-[var(--border)]">
        {/* Username row */}
        {username && !collapsed && (
          <div className="flex items-center justify-between px-4 pt-3 pb-1">
            <span className="text-xs text-[var(--muted-foreground)] truncate max-w-[140px]" title={username}>
              {username}
            </span>
            <button
              onClick={handleLogout}
              title="Logout"
              className="interactive p-1.5 rounded-md text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
            >
              <LogOut className="w-3.5 h-3.5" />
            </button>
          </div>
        )}
        {username && collapsed && (
          <div className="flex justify-center pt-3 pb-1">
            <button
              onClick={handleLogout}
              title={`Logout (${username})`}
              className="interactive p-1.5 rounded-md text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
            >
              <LogOut className="w-3.5 h-3.5" />
            </button>
          </div>
        )}
        <div className={[
          "pt-2 pb-3",
          collapsed ? "flex justify-center" : "flex items-center justify-between px-4",
        ].join(" ")}>
          {!collapsed && <span className="text-xs text-[var(--muted-foreground)]">Theme</span>}
          <ThemeToggle />
        </div>
      </div>
    </aside>
  );
}
