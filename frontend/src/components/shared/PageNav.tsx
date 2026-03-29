/**
 * PageNav — Top navigation bar for sub-pages.
 * @spec docs/spec/ui/UI_02_COMMUNITIES_DETAIL.md#navigation-bar
 * @spec docs/spec/ui/UI_03_TOP_INFLUENCERS.md#navigation-bar
 * @spec docs/spec/ui/UI_04_AGENT_DETAIL.md#navigation-bar
 * @spec docs/spec/ui/UI_05_GLOBAL_METRICS.md#navigation-bar
 */
import type { ReactNode } from "react";
import { useNavigate } from "react-router-dom";

interface BreadcrumbItem {
  label: string;
  href?: string;
  testId?: string;
}

interface PageNavProps {
  breadcrumbs: BreadcrumbItem[];
  actions?: ReactNode;
}

export default function PageNav({ breadcrumbs, actions }: PageNavProps) {
  const navigate = useNavigate();

  return (
    <nav
      data-testid="page-nav"
      className="h-14 flex items-center justify-between px-6 border-b border-[var(--border)] bg-[var(--card)] shrink-0"
    >
      <div className="flex items-center gap-3">
        <button
          data-testid="back-btn"
          onClick={() => navigate(-1)}
          className="flex items-center gap-1 text-sm text-[var(--muted-foreground)] hover:text-[var(--foreground)] transition-colors"
          aria-label="Go back"
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
            <path d="M15 18l-6-6 6-6" />
          </svg>
          Back
        </button>
        <span className="text-[var(--border)]">/</span>
        <ol className="flex items-center gap-1 text-sm">
          {breadcrumbs.map((item, i) => {
            const isLast = i === breadcrumbs.length - 1;
            return (
              <li key={i} className="flex items-center gap-1">
                {i > 0 && <span className="text-[var(--muted-foreground)] mx-1">&gt;</span>}
                {item.href && !isLast ? (
                  <button
                    onClick={() => navigate(item.href!)}
                    className="text-[var(--muted-foreground)] hover:text-[var(--foreground)] transition-colors"
                  >
                    {item.label}
                  </button>
                ) : (
                  <span
                    data-testid={item.testId}
                    className={
                      isLast
                        ? "text-[var(--foreground)] font-semibold"
                        : "text-[var(--muted-foreground)]"
                    }
                  >
                    {item.label}
                  </span>
                )}
              </li>
            );
          })}
        </ol>
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </nav>
  );
}
