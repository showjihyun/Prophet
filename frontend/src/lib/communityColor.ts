/**
 * Single source of truth for community color resolution.
 *
 * The 3D graph in `GraphPanel` derives colors dynamically from whichever
 * community ids the loaded simulation actually uses (A/B/C/D/E for the
 * default profile, or M/E/S/I, or UUIDs from custom templates). Anywhere
 * else in the UI that paints a community swatch — the legend, the
 * Communities sidebar page, charts, badges — must use the same resolver
 * or the colors will drift and the user sees the same community in
 * different colors across views.
 *
 * Algorithm:
 *  1. If the id matches a built-in COMMUNITIES entry (A–E), use that
 *     entry's color.
 *  2. Otherwise hash the id and pick a slot from FALLBACK_COMMUNITY_PALETTE.
 *     Hashing the id (not insertion order) keeps the same community on
 *     the same color across re-fetches, pagination, or backend reorderings.
 *
 * @spec docs/spec/ui/UI_02_COMMUNITIES_DETAIL.md
 */
import { COMMUNITIES } from "@/config/constants";

/**
 * 10-slot fallback palette used when a community id has no entry in
 * the static `COMMUNITIES` table. Mirrors the array previously kept
 * private inside `GraphPanel.tsx`; consolidated here so every surface
 * picks from the exact same set of colors.
 */
export const FALLBACK_COMMUNITY_PALETTE: readonly string[] = [
  "#3b82f6", // blue
  "#22c55e", // green
  "#f97316", // orange
  "#a855f7", // purple
  "#ef4444", // red
  "#06b6d4", // cyan
  "#ec4899", // pink
  "#84cc16", // lime
  "#eab308", // yellow
  "#14b8a6", // teal
];

const STATIC_COMMUNITY_COLOR: Record<string, string> = Object.fromEntries(
  COMMUNITIES.map((c) => [c.id, c.color]),
);

/**
 * Resolve a community id to its display hex color. Stable across renders:
 * the same id always returns the same color regardless of ordering,
 * pagination, or which simulation is currently loaded.
 */
export function resolveCommunityColor(communityId: string): string {
  const fromStatic = STATIC_COMMUNITY_COLOR[communityId];
  if (fromStatic) return fromStatic;
  let h = 0;
  for (let i = 0; i < communityId.length; i++) {
    h = (h * 31 + communityId.charCodeAt(i)) | 0;
  }
  return FALLBACK_COMMUNITY_PALETTE[
    Math.abs(h) % FALLBACK_COMMUNITY_PALETTE.length
  ];
}
