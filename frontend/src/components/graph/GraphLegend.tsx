/**
 * GraphLegend — fixed overlay explaining the 3D graph color contract.
 *
 * @spec docs/spec/07_FRONTEND_SPEC.md#graph-legend
 *
 * Before this component, the graph used 5+ colors with no key. Users
 * had to guess that "green glow = adopted" and which community each
 * color belonged to. This legend makes the contract explicit and can
 * be collapsed to save screen space.
 */
import { memo, useState } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";
import { COMMUNITIES } from "@/config/constants";

interface LegendCommunity {
  id: string;
  name: string;
  color: string;
}

interface GraphLegendProps {
  /**
   * Communities to display in the Communities section. When omitted, falls
   * back to the hardcoded `COMMUNITIES` default profile. Pass the dynamic
   * list from the currently loaded graph so the legend reflects reality.
   */
  communities?: readonly LegendCommunity[];
  /**
   * Extra vertical offset above the bottom edge, in pixels. Lets the
   * parent stack this overlay above other bottom-anchored UI (e.g. the
   * 3D Controls hint) without hardcoding a magic number inside this
   * component.
   */
  bottomOffsetPx?: number;
}

const NODE_STATE_LEGEND: Array<{ label: string; color: string; description: string }> = [
  { label: "Adopted", color: "#22c55e", description: "Converted to target" },
  { label: "Dimmed", color: "#1e293b", description: "Outside active filter" },
  { label: "Default", color: "#64748b", description: "Unknown community" },
];

const EDGE_LEGEND: Array<{ label: string; color: string; description: string }> = [
  { label: "Intra-community", color: "rgba(59,130,246,0.35)", description: "Within one community" },
  { label: "Inter-community", color: "rgba(148,163,184,0.15)", description: "Cross-community tie" },
  { label: "Bridge", color: "rgba(148,163,184,0.55)", description: "Long-range structural hub" },
];

function GraphLegend({
  communities,
  bottomOffsetPx = 0,
}: GraphLegendProps = {}) {
  const [open, setOpen] = useState(true);
  const items: readonly LegendCommunity[] =
    communities && communities.length > 0 ? communities : COMMUNITIES;

  return (
    <div
      data-testid="graph-legend"
      className="absolute left-4 z-10 max-w-[240px] rounded-lg border border-white/10 bg-slate-900/80 backdrop-blur-sm text-white/90 shadow-lg"
      // Base ``1rem`` (the original ``bottom-4``) plus the caller-supplied
      // offset so the parent can stack this overlay above other
      // bottom-anchored UI without hardcoding a magic number here.
      style={{ bottom: `calc(1rem + ${bottomOffsetPx}px)` }}
    >
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        data-testid="graph-legend-toggle"
        className="w-full flex items-center justify-between gap-2 px-3 py-2 text-xs font-semibold"
      >
        <span>Legend</span>
        {open ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronUp className="w-3.5 h-3.5" />}
      </button>

      {open && (
        <div
          data-testid="graph-legend-content"
          className="px-3 pb-3 space-y-3 text-[10px]"
        >
          <section>
            <h4 className="mb-1 font-semibold text-white/70">Communities</h4>
            <ul className="space-y-1">
              {items.map((c) => (
                <li key={c.id} className="flex items-center gap-2">
                  <span
                    className="inline-block w-3 h-3 rounded-full shrink-0"
                    style={{ backgroundColor: c.color }}
                    aria-hidden="true"
                  />
                  <span className="truncate">{c.name}</span>
                  <span className="ml-auto text-white/50 shrink-0">{c.id}</span>
                </li>
              ))}
            </ul>
          </section>

          <section>
            <h4 className="mb-1 font-semibold text-white/70">Node state</h4>
            <ul className="space-y-1">
              {NODE_STATE_LEGEND.map((n) => (
                <li key={n.label} className="flex items-center gap-2">
                  <span
                    className="inline-block w-3 h-3 rounded-full ring-1 ring-white/30"
                    style={{ backgroundColor: n.color }}
                    aria-hidden="true"
                  />
                  <span className="font-medium">{n.label}</span>
                  <span className="ml-auto text-white/50 text-[9px]">{n.description}</span>
                </li>
              ))}
            </ul>
          </section>

          <section>
            <h4 className="mb-1 font-semibold text-white/70">Edges</h4>
            <ul className="space-y-1">
              {EDGE_LEGEND.map((e) => (
                <li key={e.label} className="flex items-center gap-2">
                  <span
                    className="inline-block w-6 h-[2px]"
                    style={{ backgroundColor: e.color }}
                    aria-hidden="true"
                  />
                  <span className="font-medium">{e.label}</span>
                </li>
              ))}
            </ul>
          </section>
        </div>
      )}
    </div>
  );
}

export default memo(GraphLegend);
