/**
 * Shared types and constants for the InfluencersFilter component.
 * @spec docs/spec/ui/UI_09_INFLUENCERS_FILTER.md
 *
 * Extracted to a separate file so that InfluencersFilter.tsx can be a
 * component-only module (required by react-refresh/only-export-components).
 */

export interface FilterState {
  communities: string[];
  status: "all" | "active" | "idle";
  scoreMin: number;
  scoreMax: number;
  sentiment: string;
  minConnections: number;
}

export const DEFAULT_FILTERS: FilterState = {
  communities: ["Alpha", "Beta", "Gamma", "Delta", "Bridge"],
  status: "all",
  scoreMin: 0,
  scoreMax: 100,
  sentiment: "all",
  minConnections: 0,
};
