/**
 * HelpTooltip — reusable contextual help icon with tooltip.
 *
 * Renders a small HelpCircle icon that reveals an explanation popover
 * on hover OR on click (mobile-friendly). Designed to sit next to a
 * label and explain a domain-specific term.
 *
 * Anti-flicker design (battle-tested):
 * - Hover handlers live on the WRAPPER span, not the button, so the
 *   icon → tooltip mouse path stays inside one hover region.
 * - Tooltip is always rendered; visibility toggled via opacity to avoid
 *   layout reflow when it appears/disappears.
 * - `pointer-events-none` on the tooltip ensures it never steals hover
 *   state from the wrapper.
 * - `align="right"` positions the popover flush to the icon's right edge,
 *   used for cards near a container's right edge so the 256px tooltip
 *   doesn't overflow and trigger horizontal scrollbar flicker.
 *
 * Two ways to call:
 *
 *   // Inline label + text
 *   <HelpTooltip label="Polarization" text="A measure of belief variance..." />
 *
 *   // From the central glossary (recommended)
 *   <HelpTooltip term="polarization" />
 */
import { useState, useRef, useEffect } from "react";
import { HelpCircle } from "lucide-react";
import { GLOSSARY, type GlossaryTerm } from "@/config/glossary";

export type TooltipAlign = "left" | "center" | "right";
export type TooltipSize = "xs" | "sm" | "md";

interface HelpTooltipProps {
  /** Pick a term from the central glossary. Mutually exclusive with label/text. */
  term?: GlossaryTerm;
  /** Inline label (used when not pulling from glossary). */
  label?: string;
  /** Inline body text (used when not pulling from glossary). */
  text?: string;
  /** Horizontal alignment of the popover relative to the icon. Default: center. */
  align?: TooltipAlign;
  /** Icon size. Default: xs (3.5px) — matches small label rows. */
  size?: TooltipSize;
  /** Optional className for the wrapper (rare). */
  className?: string;
}

const ICON_SIZE: Record<TooltipSize, string> = {
  xs: "w-3.5 h-3.5",
  sm: "w-4 h-4",
  md: "w-5 h-5",
};

export default function HelpTooltip({
  term,
  label,
  text,
  align = "center",
  size = "xs",
  className = "",
}: HelpTooltipProps) {
  const [open, setOpen] = useState(false);
  const [hovered, setHovered] = useState(false);
  const ref = useRef<HTMLSpanElement>(null);

  // Close on outside click (when toggled open)
  useEffect(() => {
    if (!open) return;
    function handler(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  // Resolve content: glossary > inline props
  const entry = term ? GLOSSARY[term] : undefined;
  const resolvedLabel = entry?.label ?? label ?? "";
  const resolvedText = entry?.text ?? text ?? "";

  // No content → render nothing (defensive)
  if (!resolvedText) return null;

  const visible = open || hovered;
  const alignClass =
    align === "right"
      ? "right-0"
      : align === "left"
        ? "left-0"
        : "left-1/2 -translate-x-1/2";

  return (
    <span
      ref={ref}
      className={`relative inline-flex items-center ${className}`}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      <button
        type="button"
        aria-label={`What does ${resolvedLabel} mean?`}
        onClick={(e) => {
          e.stopPropagation();
          setOpen((v) => !v);
        }}
        className={`inline-flex items-center justify-center ${ICON_SIZE[size]} text-[var(--muted-foreground)] hover:text-[var(--foreground)] transition-colors`}
      >
        <HelpCircle className={ICON_SIZE[size]} />
      </button>
      {/* Always rendered — opacity-toggled to avoid layout reflow */}
      <span
        role="tooltip"
        aria-hidden={!visible}
        className={`absolute z-50 ${alignClass} top-full mt-1.5 w-64 px-3 py-2 rounded-md border border-[var(--border)] bg-[var(--card)] shadow-lg text-[11px] font-normal leading-relaxed text-[var(--foreground)] whitespace-normal pointer-events-none transition-opacity duration-100 ${visible ? "opacity-100" : "opacity-0"}`}
      >
        <span className="block font-semibold text-[var(--foreground)] mb-1">
          {resolvedLabel}
        </span>
        {resolvedText}
      </span>
    </span>
  );
}
