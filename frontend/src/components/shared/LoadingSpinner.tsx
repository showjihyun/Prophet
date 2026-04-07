/**
 * Shared loading spinner and skeleton components.
 * @spec docs/spec/07_FRONTEND_SPEC.md#10-2-loading-states
 */

interface SpinnerProps {
  size?: "sm" | "md" | "lg";
  label?: string;
  className?: string;
}

export function LoadingSpinner({ size = "md", label, className = "" }: SpinnerProps) {
  const sizeClasses = { sm: "w-4 h-4", md: "w-6 h-6", lg: "w-8 h-8" };
  return (
    <div className={`flex flex-col items-center justify-center gap-2 ${className}`}>
      <svg
        className={`animate-spin ${sizeClasses[size]} text-[var(--primary)]`}
        viewBox="0 0 24 24"
        fill="none"
      >
        <circle
          cx="12" cy="12" r="10"
          stroke="currentColor"
          strokeWidth="3"
          strokeLinecap="round"
          className="opacity-20"
        />
        <path
          d="M12 2a10 10 0 0 1 10 10"
          stroke="currentColor"
          strokeWidth="3"
          strokeLinecap="round"
        />
      </svg>
      {label && (
        <span className="text-xs text-[var(--muted-foreground)] animate-pulse">
          {label}
        </span>
      )}
    </div>
  );
}

interface SkeletonProps {
  className?: string;
}

export function Skeleton({ className = "" }: SkeletonProps) {
  return (
    <div
      className={`animate-pulse rounded bg-[var(--muted)] ${className}`}
    />
  );
}

export function SkeletonCard() {
  return (
    <div className="p-4 rounded-lg border border-[var(--border)] bg-[var(--card)] space-y-3">
      <Skeleton className="h-4 w-3/4" />
      <Skeleton className="h-3 w-1/2" />
      <Skeleton className="h-8 w-full" />
    </div>
  );
}

export function SkeletonList({ rows = 5 }: { rows?: number }) {
  return (
    <div className="space-y-2 p-2">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex items-center gap-3 px-3 py-2">
          <Skeleton className="w-3 h-3 rounded-full shrink-0" />
          <div className="flex-1 space-y-1.5">
            <Skeleton className="h-3 w-2/3" />
            <Skeleton className="h-2 w-1/3" />
          </div>
          <Skeleton className="w-12 h-1.5 rounded-full" />
        </div>
      ))}
    </div>
  );
}

export function ListTransition({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={`animate-in fade-in duration-300 ${className}`}>
      {children}
    </div>
  );
}
