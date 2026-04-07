/**
 * Centralized constants for the Prophet frontend.
 * @spec docs/spec/07_FRONTEND_SPEC.md
 *
 * All magic numbers, localStorage keys, URLs, and shared defaults
 * should live here so they can be changed in one place.
 */

// ── Network / API ──────────────────────────────────────────────────────────

export const API_VERSION_PREFIX = "/api/v1";

export const DEFAULT_API_BASE_URL = `http://localhost:8000${API_VERSION_PREFIX}`;

export const DEFAULT_WS_BASE_URL = "ws://localhost:8000";

export const DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434";

// ── localStorage Keys ──────────────────────────────────────────────────────

export const LS_KEY_TOKEN = "prophet-token";
export const LS_KEY_THEME = "prophet-theme";
export const LS_KEY_SIMULATION_ID = "prophet-simulation-id";
export const LS_KEY_USERNAME = "prophet-username";
export const LS_KEY_PROJECT_ID = "prophet-project-id";
export const LS_KEY_MC_PREFIX = "prophet-mc-";

// ── WebSocket ──────────────────────────────────────────────────────────────

export const WS_MAX_RETRIES = 5;
export const WS_BASE_DELAY_MS = 1000;
export const WS_HEARTBEAT_INTERVAL_MS = 30_000;
export const WS_MAX_RECONNECT_DELAY_MS = 30_000;

// ── Polling / Timers ───────────────────────────────────────────────────────

export const LLM_STATS_POLL_INTERVAL_MS = 5_000;
export const MONTE_CARLO_POLL_INTERVAL_MS = 2_000;
export const TOAST_DISMISS_TIMEOUT_MS = 5_000;
export const SETTINGS_SAVE_SUCCESS_DURATION_MS = 3_000;
export const QUERY_STALE_TIME_MS = 5_000;
export const QUERY_RETRY_COUNT = 1;

// ── Simulation Defaults ────────────────────────────────────────────────────

export const DEFAULT_SIMULATION_DAYS = 365;
export const DEFAULT_MAX_STEPS = 50;
export const MAX_SIMULATION_STEPS = 1000;
export const MIN_COMMUNITY_SIZE = 10;
export const MAX_COMMUNITY_SIZE = 5000;
export const DEFAULT_SLM_LLM_RATIO = 0.5;
export const DEFAULT_SIMULATION_SPEED = 2;
export const DEFAULT_RANDOM_SEED = 42;
export const SIMULATION_SPEEDS = [1, 2, 5, 10] as const;

// ── Monte Carlo ────────────────────────────────────────────────────────────

export const DEFAULT_MONTE_CARLO_RUNS = 100;
export const MONTE_CARLO_MIN_RUNS = 10;
export const MONTE_CARLO_MAX_RUNS = 500;
export const MONTE_CARLO_STEP = 10;
export const MONTE_CARLO_LLM_TIME_FACTOR = 2.5;
export const MONTE_CARLO_SLM_TIME_FACTOR = 0.3;
export const MONTE_CARLO_LLM_COST_PER_RUN = 0.05;
export const MONTE_CARLO_SLM_COST_PER_RUN = 0.001;

// ── Engine Control ─────────────────────────────────────────────────────────

export const DEFAULT_ENGINE_BUDGET_USD = 50;
export const ENGINE_QUALITY_THRESHOLD = 0.3;
export const ENGINE_SPEED_THRESHOLD = 0.7;

// ── Community Palette ──────────────────────────────────────────────────────

export const COMMUNITY_PALETTE = {
  Alpha: "#3b82f6",
  Beta: "#22c55e",
  Gamma: "#f97316",
  Delta: "#a855f7",
  Bridge: "#ef4444",
} as const;

/** Community definitions with id → name mapping and default sizes. */
export const COMMUNITIES = [
  { id: "A", name: "Alpha", color: COMMUNITY_PALETTE.Alpha, size: 50 },
  { id: "B", name: "Beta", color: COMMUNITY_PALETTE.Beta, size: 40 },
  { id: "C", name: "Gamma", color: COMMUNITY_PALETTE.Gamma, size: 35 },
  { id: "D", name: "Delta", color: COMMUNITY_PALETTE.Delta, size: 25 },
  { id: "E", name: "Bridge", color: COMMUNITY_PALETTE.Bridge, size: 10 },
] as const;

/** CSS variable → hex lookup for canvas rendering (Cytoscape / SVG). */
export const CSS_VAR_TO_HEX: Record<string, string> = {
  "var(--community-alpha)": COMMUNITY_PALETTE.Alpha,
  "var(--community-beta)": COMMUNITY_PALETTE.Beta,
  "var(--community-gamma)": COMMUNITY_PALETTE.Gamma,
  "var(--community-delta)": COMMUNITY_PALETTE.Delta,
  "var(--community-bridge)": COMMUNITY_PALETTE.Bridge,
  "var(--muted-foreground)": "#94a3b8",
};

/** Extended color array for campaign setup (8 colors). */
export const COMMUNITY_SETUP_COLORS = [
  "#3b82f6", "#22c55e", "#f97316", "#a855f7",
  "#ef4444", "#06b6d4", "#ec4899", "#84cc16",
] as const;

// ── Graph / Cytoscape ──────────────────────────────────────────────────────

export const CASCADE_TTL_MS = 8_000;
export const GRAPH_LARGE_NODE_THRESHOLD = 2_000;
export const GRAPH_LOD_ZOOM_FAR = 0.3;
export const GRAPH_LOD_ZOOM_MID = 0.7;
export const GRAPH_LOD_INFLUENCE_THRESHOLD = 0.8;
export const CASCADE_NODE_FRACTION = 0.15;
export const MOCK_GRAPH_SEED = 42;

// ── UI Limits ──────────────────────────────────────────────────────────────

export const AGENTS_FETCH_LIMIT = 200;
export const METRICS_TOP_INFLUENCERS_COUNT = 4;
export const PREV_SIM_DROPDOWN_MAX = 20;
export const COMPARE_DROPDOWN_MAX = 10;
export const DEFAULT_ROWS_PER_PAGE = 10;
export const CONVERSATION_PANEL_MAX_INSIGHTS = 12;
export const POLARIZATION_ROLLING_WINDOW = 10;

// ── Default LLM Settings ──────────────────────────────────────────────────

export const DEFAULT_LLM_PROVIDER = "ollama";
export const DEFAULT_OLLAMA_MODEL = "llama3.1:8b";
export const DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-4-6";
export const DEFAULT_OPENAI_MODEL = "gpt-4o";
export const DEFAULT_LLM_CACHE_TTL_SECONDS = 3_600;
export const DEFAULT_LLM_TIER3_RATIO = 0.1;

export const ANTHROPIC_MODELS = [
  "claude-sonnet-4-6",
  "claude-opus-4-6",
  "claude-haiku-4-5",
] as const;

export const OPENAI_MODELS = [
  "gpt-4o",
  "gpt-4o-mini",
  "gpt-4-turbo",
] as const;

// ── Simulation status ──────────────────────────────────────────────────────
// Mirrors backend SimulationStatus enum (backend/app/api/schemas.py).
// Always import from here instead of hardcoding string literals.
//
// @spec docs/spec/04_SIMULATION_SPEC.md#simulation-status

import type { SimulationStatus } from "@/types/simulation";

export const SIM_STATUS = {
  CREATED: "created",
  CONFIGURED: "configured",
  RUNNING: "running",
  PAUSED: "paused",
  COMPLETED: "completed",
  FAILED: "failed",
} as const satisfies Record<string, SimulationStatus>;

/** Statuses representing terminal/end states for a simulation run. */
export const TERMINAL_SIM_STATUSES: readonly SimulationStatus[] = [
  SIM_STATUS.COMPLETED,
  SIM_STATUS.FAILED,
] as const;

/** Statuses from which a fresh `start()` is the correct play action. */
export const STARTABLE_SIM_STATUSES: readonly SimulationStatus[] = [
  SIM_STATUS.CREATED,
  SIM_STATUS.CONFIGURED,
] as const;
