/**
 * GAP-7: Propagation animation utilities for the 3D graph.
 *
 * Exported so that both GraphPanel.tsx and tests can import them directly
 * instead of mirroring magic values.
 *
 * @spec docs/spec/07_FRONTEND_SPEC.md#gap-7
 */
import { GRAPH_LOD_ZOOM_MID, GRAPH_LOD_ZOOM_FAR } from "@/config/constants";

export type AnimationTier = "closeup" | "midrange" | "overview";

/** Determine animation detail tier based on current zoom level. */
export function getAnimationTier(zoom: number): AnimationTier {
  if (zoom >= GRAPH_LOD_ZOOM_MID) return "closeup";
  if (zoom >= GRAPH_LOD_ZOOM_FAR) return "midrange";
  return "overview";
}

/** Max simultaneous animated propagation pairs per tier. */
export const TIER_LIMITS: Record<AnimationTier, number> = {
  closeup: 50,
  midrange: 30,
  overview: 5,
};

/** Action → particle color mapping. "ignore" is intentionally excluded. */
export const ACTION_COLORS: Record<string, string> = {
  share: "#22c55e",
  comment: "#3b82f6",
  like: "#eab308",
  adopt: "#a855f7",
};
