/**
 * ZoomTierBadge — shows the current LOD/animation tier of the 3D graph.
 *
 * @spec docs/spec/07_FRONTEND_SPEC.md#graph-zoom-tier-badge
 *
 * The graph already uses ``getAnimationTier`` internally to decide how
 * many propagation particles to render, but the tier is invisible to
 * the user. This badge surfaces it so the user understands why particle
 * density changes as they zoom.
 */
import { memo } from "react";
import { ZoomIn } from "lucide-react";
import type { AnimationTier } from "./propagationAnimationUtils";

const TIER_LABEL: Record<AnimationTier, string> = {
  closeup: "Close-up",
  midrange: "Mid-range",
  overview: "Overview",
};

const TIER_COLOR: Record<AnimationTier, string> = {
  closeup: "text-emerald-300 bg-emerald-500/20",
  midrange: "text-amber-300 bg-amber-500/20",
  overview: "text-slate-300 bg-slate-500/20",
};

const TIER_DESCRIPTION: Record<AnimationTier, string> = {
  closeup: "Full particle detail",
  midrange: "Reduced particle density",
  overview: "Summary particles only",
};

interface ZoomTierBadgeProps {
  tier: AnimationTier;
}

function ZoomTierBadge({ tier }: ZoomTierBadgeProps) {
  return (
    <div
      data-testid="zoom-tier-badge"
      data-tier={tier}
      className="absolute top-16 right-4 z-10 flex items-center gap-2 px-3 py-1.5 rounded-full border border-white/10 bg-slate-900/80 backdrop-blur-sm shadow-lg"
    >
      <ZoomIn className="w-3.5 h-3.5 text-white/70" aria-hidden="true" />
      <span
        className={`text-[10px] font-semibold px-1.5 py-0.5 rounded ${TIER_COLOR[tier]}`}
      >
        {TIER_LABEL[tier]}
      </span>
      <span className="hidden md:inline text-[10px] text-white/50">
        {TIER_DESCRIPTION[tier]}
      </span>
    </div>
  );
}

export default memo(ZoomTierBadge);
