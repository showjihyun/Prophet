# Screenshots

This directory holds the product screenshots referenced from the project root `README.md` "📸 Screenshots" section.

## Required files (referenced from README)

| File | Surface | Suggested capture |
|---|---|---|
| `simulation-3d.png` | `/simulation/:id` | Mid-run, ~step 15 with active cascade glow + community-colored adopted nodes. 1600×1000. |
| `opinions.png` | `/opinions` (and drill-in) | Composite/grid showing the three levels (scenario → community → thread). 1600×1000. |
| `analytics.png` | `/analytics` | Post-run state with adoption curve + cascade timeline visible. 1600×1000. |
| `influencers.png` | `/influencers` | Top-N table populated; ideally with the per-step contribution column visible. 1600×1000. |

## Rules

- Use a fresh demo simulation, not real customer data.
- Default theme (matches docs voice).
- Crop to the meaningful UI; no browser chrome unless the URL is the point.
- Compress to under 400 KB per image (TinyPNG or `pngquant --quality 65-80`) so clones stay light.

## How the README handles missing files

The README `<img onerror>` hides any missing image gracefully, so a partial set is fine to land — the section just shows fewer tiles until the rest are recorded.
