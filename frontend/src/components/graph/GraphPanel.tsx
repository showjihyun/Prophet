/**
 * GraphPanel — AI Social World Graph Engine (Zone 2 Center).
 * @spec docs/spec/ui/UI_01_SIMULATION_MAIN.md#zone-2-center-ai-social-world-graph-engine
 *
 * Phase 7A: dark-themed container with overlays.
 * Actual Cytoscape.js integration deferred to post-Phase 7.
 */
import { ZoomIn, ZoomOut, Maximize2 } from "lucide-react";

const LEGEND_ITEMS = [
  { name: "Alpha", color: "var(--community-alpha)", count: "1,500" },
  { name: "Beta", color: "var(--community-beta)", count: "1,200" },
  { name: "Gamma", color: "var(--community-gamma)", count: "1,100" },
  { name: "Delta", color: "var(--community-delta)", count: "1,400" },
  { name: "Bridge", color: "var(--community-bridge)", count: "300" },
];

export default function GraphPanel() {
  return (
    <div
      data-testid="graph-panel"
      className="relative w-full h-full overflow-hidden"
      style={{
        background:
          "radial-gradient(ellipse at center, var(--bg-graph-primary) 0%, var(--bg-graph-gradient-end) 100%)",
      }}
    >
      {/* Title Overlay — top-left */}
      <div className="absolute top-4 left-4 z-10">
        <h2 className="text-lg font-bold text-white">AI Social World</h2>
        <p className="text-xs text-white/60">
          MiroFish Engine — 6,500 Active Agents · Force-Directed Graph
        </p>
      </div>

      {/* Zoom Controls — top-right */}
      <div className="absolute top-4 right-4 z-10 flex flex-col gap-1">
        <GraphButton icon={<ZoomIn className="w-4 h-4" />} label="Zoom in" />
        <GraphButton icon={<ZoomOut className="w-4 h-4" />} label="Zoom out" />
        <GraphButton
          icon={<Maximize2 className="w-4 h-4" />}
          label="Fullscreen"
        />
      </div>

      {/* Cascade Badge */}
      <div className="absolute top-4 left-1/2 -translate-x-1/2 z-10">
        <span className="inline-flex items-center gap-1.5 text-[11px] font-semibold text-green-400 bg-green-950/60 border border-green-800/40 px-2.5 py-1 rounded-full shadow-[0_0_12px_rgba(34,197,94,0.3)]">
          <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse-dot" />
          Cascade #47 Active
        </span>
      </div>

      {/* Placeholder content */}
      <div className="absolute inset-0 flex items-center justify-center">
        <span className="text-sm text-white/20 font-mono">
          Graph engine will render here
        </span>
      </div>

      {/* Legend — bottom-left */}
      <div className="absolute bottom-4 left-4 z-10 bg-black/40 rounded-lg p-3 backdrop-blur-sm">
        <div className="flex flex-col gap-1.5">
          {LEGEND_ITEMS.map((item) => (
            <div key={item.name} className="flex items-center gap-2">
              <span
                className="w-2 h-2 rounded-full shrink-0"
                style={{ backgroundColor: item.color }}
              />
              <span className="text-[11px] text-white/80 w-12">
                {item.name}
              </span>
              <span className="text-[10px] text-white/50 font-mono">
                {item.count}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Status Bar — bottom-right */}
      <div className="absolute bottom-4 right-4 z-10">
        <span className="text-[11px] font-mono text-white/40">
          60 FPS · 6,500 nodes · 18,420 edges · WebGL
        </span>
      </div>
    </div>
  );
}

function GraphButton({
  icon,
  label,
}: {
  icon: React.ReactNode;
  label: string;
}) {
  return (
    <button
      title={label}
      className="w-8 h-8 flex items-center justify-center rounded-md bg-white/10 text-white/70 hover:bg-white/20 hover:text-white transition-colors"
    >
      {icon}
    </button>
  );
}
