/**
 * Frontend architectural invariants — static source-scan meta tests.
 *
 * @spec docs/spec/20_CLEAN_ARCHITECTURE_SPEC.md#frontend-invariants
 *
 * These tests enforce the same kind of structural rules that the backend
 * ``TestContractDiscipline`` + ``TestCompositionRoot`` + ``TestEnginePurity``
 * classes enforce on the Python side. Before this file, the frontend had
 * 601 functional tests but **zero** invariants — layer violations could
 * only be caught by manual code review.
 *
 * Each test scans source files with a regex. Pre-existing violations are
 * captured in explicit allow-lists so the tests pass on current code
 * **but fail immediately for any new violation**. The allow-lists are
 * a baseline we ratchet down over time — every removal is a win.
 *
 * Rules enforced:
 *   #1 components/** must not import apiClient as a runtime value
 *   #2 pages/**      must not import apiClient as a runtime value
 *   #3 store/**      must not import from api/client or components/
 *   #4 types/**      must not depend on any non-type internal module
 *   #5 no hardcoded SimulationStatus literals outside constants.ts
 *   #6 no hardcoded community color hex outside constants.ts
 *   #7 no raw fetch() calls to /api/v1 outside api/client.ts
 *   #8 component files export only components (Vite react-refresh rule)
 */
import { describe, it, expect } from "vitest";
import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, relative, sep } from "node:path";

// --------------------------------------------------------------------------- //
// Source walker                                                               //
// --------------------------------------------------------------------------- //

const SRC_ROOT = join(__dirname, "..");

function walkSrcFiles(dir: string = SRC_ROOT): string[] {
  const out: string[] = [];
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    const s = statSync(full);
    if (s.isDirectory()) {
      if (entry === "__tests__" || entry === "node_modules") continue;
      out.push(...walkSrcFiles(full));
    } else if (/\.tsx?$/.test(entry) && !entry.endsWith(".d.ts")) {
      const rel = relative(SRC_ROOT, full).split(sep).join("/");
      out.push(rel);
    }
  }
  return out;
}

function readSrc(relPath: string): string {
  return readFileSync(join(SRC_ROOT, relPath), "utf-8");
}

function stripComments(src: string): string {
  return src
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .replace(/^\s*\/\/.*$/gm, "");
}

const ALL_FILES = walkSrcFiles();

interface Violation {
  file: string;
  line: number;
  snippet: string;
}

function filesMatching(prefix: string): string[] {
  return ALL_FILES.filter((f) => f.startsWith(prefix));
}

function findViolations(files: string[], pattern: RegExp): Violation[] {
  const violations: Violation[] = [];
  for (const f of files) {
    const src = stripComments(readSrc(f));
    const lines = src.split("\n");
    lines.forEach((line, idx) => {
      if (pattern.test(line)) {
        violations.push({ file: f, line: idx + 1, snippet: line.trim() });
      }
    });
  }
  return violations;
}

function reportViolations(rule: string, offenders: Violation[]): void {
  if (offenders.length === 0) return;
  const report = offenders
    .map((v) => `  ${v.file}:${v.line}  ${v.snippet}`)
    .join("\n");
  throw new Error(`${rule}\n${report}`);
}

// --------------------------------------------------------------------------- //
// Known pre-existing violations (baseline).                                   //
// Each entry documented in docs/spec/20_CLEAN_ARCHITECTURE_SPEC.md#6.3.       //
// New additions MUST NOT extend these lists — they're meant to ratchet down. //
// --------------------------------------------------------------------------- //

/** Files that legitimately or pre-existingly import ``apiClient`` as a
 *  runtime value. Every entry is either:
 *    - A legacy hook/component pending migration to ``api/queries.ts``
 *    - A one-shot fetcher that's hard to express as a query hook
 */
const COMPONENTS_APICLIENT_BASELINE = new Set([
  "components/control/hooks/useAutoStepLoop.ts",
  "components/control/hooks/usePlaybackControls.ts",
  "components/control/hooks/usePrevSimulations.ts",
  "components/control/hooks/useProjectScenarioSync.ts",
  "components/shared/SimulationReportModal.tsx",
]);

const PAGES_APICLIENT_BASELINE = new Set([
  "pages/SimulationPage.tsx", // one-shot restore from URL
  "pages/SettingsPage.tsx", // settings CRUD, low-churn
  "pages/GlobalMetricsPage.tsx", // LLM stats + export
  "pages/ProjectScenariosPage.tsx", // scenario runner
]);

/** Hardcoded community-palette files that existed before the invariant
 *  was introduced. Follow-up: migrate to ``COMMUNITY_PALETTE`` import. */
const COMMUNITY_HEX_BASELINE = new Set([
  "components/campaign/types.ts",
  "components/graph/CommunityPanel.tsx", // fallback palette mirrors GraphPanel
  "components/graph/FactionMapView.tsx",
  "components/graph/GraphLegend.tsx", // legend intentionally mirrors palette
  "components/graph/GraphPanel.tsx", // ADOPTED_GLOW_COLOR + fallback palette
  "components/graph/MetricsPanel.tsx",
  "components/graph/propagationAnimationUtils.ts",
  "components/shared/AgentInterveneModal.tsx",
  "pages/AgentDetailPage.tsx",
]);

/** Component files that intentionally export small helpers alongside
 *  the component (react-refresh rule exception). Every entry should
 *  eventually be split into a sibling ``*Utils.ts`` file. */
const COMPONENT_EXPORT_BASELINE = new Set<string>([
  // (empty) — new components split helpers into ``*Utils.ts`` by default.
]);

// --------------------------------------------------------------------------- //
// Invariant 1 — components/** must not runtime-import apiClient                //
// --------------------------------------------------------------------------- //

describe("ArchitectureInvariants · Layer separation", () => {
  it("[#1] components/** must not runtime-import apiClient", () => {
    const files = filesMatching("components/").filter(
      (f) => !COMPONENTS_APICLIENT_BASELINE.has(f),
    );
    // Flag runtime imports (``import { apiClient }``) and property
    // accesses (``apiClient.``). Explicitly allow TypeScript type-only
    // imports (``import type { ... }`` or ``import { type ... }``) — they
    // don't create runtime dependencies.
    const offenders: Violation[] = [];
    for (const f of files) {
      const src = stripComments(readSrc(f));
      const lines = src.split("\n");
      lines.forEach((line, idx) => {
        // Skip pure type-only import lines.
        if (/^\s*import\s+type\s/.test(line)) return;
        // Skip ``import { type X } from "../../api/client"`` — single
        // type import with the ``type`` modifier inside braces.
        if (/^\s*import\s+\{\s*type\s+[^}]+\}\s+from\s+["'][^"']*api\/client/.test(line)) return;
        // Flag: ``import { apiClient }`` or ``apiClient.anything``.
        if (
          /(^\s*import\s+\{[^}]*\bapiClient\b[^}]*\}\s+from\s+["'][^"']*api\/client)|(\bapiClient\s*\.)/.test(
            line,
          )
        ) {
          offenders.push({ file: f, line: idx + 1, snippet: line.trim() });
        }
      });
    }
    reportViolations(
      "Components must consume api/queries hooks, not apiClient directly. " +
        "Add to COMPONENTS_APICLIENT_BASELINE only with a SPEC 20 §6.3 follow-up note.",
      offenders,
    );
    expect(offenders).toEqual([]);
  });

  it("[#2] pages/** must not runtime-import apiClient", () => {
    const files = filesMatching("pages/").filter(
      (f) => !PAGES_APICLIENT_BASELINE.has(f),
    );
    const offenders: Violation[] = [];
    for (const f of files) {
      const src = stripComments(readSrc(f));
      const lines = src.split("\n");
      lines.forEach((line, idx) => {
        if (/^\s*import\s+type\s/.test(line)) return;
        if (/^\s*import\s+\{\s*type\s+[^}]+\}\s+from\s+["'][^"']*api\/client/.test(line)) return;
        if (
          /(^\s*import\s+\{[^}]*\bapiClient\b[^}]*\}\s+from\s+["'][^"']*api\/client)|(\bapiClient\s*\.)/.test(
            line,
          )
        ) {
          offenders.push({ file: f, line: idx + 1, snippet: line.trim() });
        }
      });
    }
    reportViolations(
      "Pages must consume api/queries hooks, not apiClient directly. " +
        "Add to PAGES_APICLIENT_BASELINE only with a SPEC 20 §6.3 follow-up note.",
      offenders,
    );
    expect(offenders).toEqual([]);
  });

  it("[#3] store/** must not import from api/client or components/", () => {
    // Type-only imports of DTO shapes from client.ts are allowed for the
    // store's ``cloneConfig`` typing. Flag only runtime imports.
    const files = filesMatching("store/");
    const offenders: Violation[] = [];
    for (const f of files) {
      const src = stripComments(readSrc(f));
      const lines = src.split("\n");
      lines.forEach((line, idx) => {
        if (/^\s*import\s+type\s/.test(line)) return;
        if (/^\s*import\s+\{\s*type\s+[^}]+\}\s+from\s+["'][^"']*api\/client/.test(line)) return;
        // Runtime import from api/client → violation
        if (
          /^\s*import\s+\{[^}]*\}\s+from\s+["'][^"']*api\/client/.test(line) &&
          !/import\s+\{\s*type\s/.test(line)
        ) {
          offenders.push({ file: f, line: idx + 1, snippet: line.trim() });
        }
        // Any import from components/ → violation
        if (/from\s+["'][^"']*\.\.\/components|from\s+["']components\//.test(line)) {
          offenders.push({ file: f, line: idx + 1, snippet: line.trim() });
        }
      });
    }
    reportViolations(
      "store/ is a leaf state layer — only types-only imports from api/client are allowed.",
      offenders,
    );
    expect(offenders).toEqual([]);
  });

  it("[#4] types/** must not depend on any non-type internal module", () => {
    const files = filesMatching("types/");
    // Allow imports from ``node:`` builtins, other types/ files, and
    // ``type``-modifier imports from siblings (for type aliases).
    const offenders: Violation[] = [];
    for (const f of files) {
      const src = stripComments(readSrc(f));
      const lines = src.split("\n");
      lines.forEach((line, idx) => {
        if (/^\s*import\s+type\s/.test(line)) return;
        if (/from\s+["']node:/.test(line)) return;
        // Runtime import from anything not under types/ → violation
        if (
          /^\s*import\s+\{[^}]*\}\s+from\s+["'](?!.*\/types\/)[^"']+["']/.test(line)
        ) {
          offenders.push({ file: f, line: idx + 1, snippet: line.trim() });
        }
      });
    }
    reportViolations(
      "types/ must be a leaf layer — use type-only imports.",
      offenders,
    );
    expect(offenders).toEqual([]);
  });
});

// --------------------------------------------------------------------------- //
// Invariant 2 — Constants discipline                                           //
// --------------------------------------------------------------------------- //

describe("ArchitectureInvariants · Constants discipline", () => {
  it("[#5] no hardcoded SimulationStatus literals outside constants.ts", () => {
    const ALLOW = new Set([
      "config/constants.ts",
      "types/simulation.ts",
    ]);
    // Only ``SIM_STATUS`` values. Other enums that happen to share
    // keywords (scenario.status === "draft" / WorkflowStepper stage.state
    // === "completed" / etc.) belong to different domains and are fine.
    const SIM_ONLY_LITERALS = ["configured"]; // unique to SIM_STATUS
    // For shared-keyword literals ("running", "paused", "completed",
    // "failed", "created") we flag only when the line compares against
    // an identifier named ``simulation.status``, ``sim.status``, or a
    // store-derived ``status`` variable.
    const SHARED_LITERALS = ["running", "paused", "completed", "failed", "created"];
    const files = ALL_FILES.filter(
      (f) =>
        !ALLOW.has(f) &&
        !f.endsWith(".test.ts") &&
        !f.endsWith(".test.tsx"),
    );
    const offenders: Violation[] = [];
    for (const f of files) {
      const src = stripComments(readSrc(f));
      const lines = src.split("\n");
      lines.forEach((line, idx) => {
        // Rule A: ``"configured"`` anywhere is a clear SIM_STATUS literal.
        for (const lit of SIM_ONLY_LITERALS) {
          if (new RegExp(`["']${lit}["']`).test(line)) {
            offenders.push({ file: f, line: idx + 1, snippet: line.trim() });
            return;
          }
        }
        // Rule B: shared-keyword literal + ``sim.*status`` comparison.
        for (const lit of SHARED_LITERALS) {
          if (!new RegExp(`["']${lit}["']`).test(line)) continue;
          // Accept only literals used with an identifier that looks
          // simulation-specific.
          if (
            /(simulation\.status|sim\.status|\bstatus\b\s*===\s*SIM_STATUS)/.test(
              line,
            )
          ) {
            offenders.push({ file: f, line: idx + 1, snippet: line.trim() });
            return;
          }
        }
      });
    }
    reportViolations(
      "Hardcoded SimulationStatus literal — import SIM_STATUS from config/constants.",
      offenders,
    );
    expect(offenders).toEqual([]);
  });

  it("[#6] no hardcoded community color hex outside baseline", () => {
    const ALLOW = new Set([
      "config/constants.ts",
      "index.css",
      ...COMMUNITY_HEX_BASELINE,
    ]);
    const COMMUNITY_HEXES = [
      "#3b82f6",
      "#22c55e",
      "#f97316",
      "#a855f7",
      "#ef4444",
    ];
    const pattern = new RegExp(
      COMMUNITY_HEXES.map((h) => h.replace("#", "\\#")).join("|"),
      "i",
    );
    const files = ALL_FILES.filter(
      (f) =>
        !ALLOW.has(f) &&
        !f.endsWith(".test.ts") &&
        !f.endsWith(".test.tsx"),
    );
    const offenders = findViolations(files, pattern);
    reportViolations(
      "Community palette hex outside constants.ts — import COMMUNITY_PALETTE. " +
        "Add to COMMUNITY_HEX_BASELINE only with a follow-up note.",
      offenders,
    );
    expect(offenders).toEqual([]);
  });
});

// --------------------------------------------------------------------------- //
// Invariant 3 — Composition + purity                                           //
// --------------------------------------------------------------------------- //

describe("ArchitectureInvariants · Composition + purity", () => {
  it("[#7] no raw fetch() to /api/v1 outside api/client.ts", () => {
    const ALLOW = new Set(["api/client.ts"]);
    const files = ALL_FILES.filter(
      (f) =>
        !ALLOW.has(f) &&
        !f.endsWith(".test.ts") &&
        !f.endsWith(".test.tsx"),
    );
    const offenders = findViolations(files, /\bfetch\s*\(/);
    const apiOffenders = offenders.filter((v) =>
      /\/api\/v1|BASE_URL|API_BASE/.test(v.snippet),
    );
    reportViolations(
      "Raw fetch() to the API detected — route through api/client.ts.",
      apiOffenders,
    );
    expect(apiOffenders).toEqual([]);
  });

  it("[#8] component files export only components (react-refresh rule)", () => {
    // Lowercase-named exports = non-components. ``export type`` /
    // ``export interface`` / ``export default`` are always allowed; they
    // don't conflict with react-refresh. ``export function foo()`` and
    // ``export const foo =`` ARE flagged.
    const files = filesMatching("components/")
      .filter((f) => f.endsWith(".tsx"))
      .filter((f) => !COMPONENT_EXPORT_BASELINE.has(f));
    const offenders: Violation[] = [];
    for (const f of files) {
      const src = stripComments(readSrc(f));
      const lines = src.split("\n");
      lines.forEach((line, idx) => {
        const namedExport = line.match(
          /^\s*export\s+(function|const|let|var)\s+([A-Za-z_][A-Za-z0-9_]*)/,
        );
        if (!namedExport) return;
        const [, , name] = namedExport;
        // Component names start with uppercase → allowed.
        if (/^[A-Z]/.test(name)) return;
        offenders.push({ file: f, line: idx + 1, snippet: line.trim() });
      });
    }
    reportViolations(
      "Component files must only export components. Move helpers to a sibling *Utils.ts file.",
      offenders,
    );
    expect(offenders).toEqual([]);
  });
});
