# UI-09 — Influencers Filter Popover SPEC
Version: 0.1.0 | Status: DRAFT
Source: pencil-shadcn.pen > Frame: Influencers Filter Popover (ID: 9fgvc)

---

## 1. Overview

The Influencers Filter Popover is a floating panel that appears when the "Filter" button is clicked on the Influencers page (UI-08). It provides multi-faceted filtering controls for the influencer data table including community selection, status filter, influence score range, sentiment filter, and minimum connections threshold. The popover is anchored to the filter button and dismissible via close button, clicking outside, or pressing Escape.

---

## 2. Layout Structure

```
+--------------------------------------------+
| Header                        [9fgvc/header]|
| "Filter Influencers"              [X close] |
+--------------------------------------------+
| Body (padding 24px, gap 24px)  [9fgvc/body] |
|                                              |
| Community                                    |
| [x] Alpha                                   |
| [x] Beta                                    |
| [x] Gamma                                   |
| [x] Delta                                   |
| [x] Bridge                                  |
|                                              |
| Status                                       |
| (o) All  ( ) Active  ( ) Idle               |
|                                              |
| Influence Score Range                        |
| Min [  0  ]        Max [ 100 ]               |
|                                              |
| Sentiment                                    |
| [ All                              v ]       |
|                                              |
| Min Connections                              |
| [  0  ]                                      |
|                                              |
+--------------------------------------------+
| Footer                      [9fgvc/footer]  |
| [Reset]                  [Apply Filters ->] |
+--------------------------------------------+
```

---

## 3. Components

### Header

| Component ID | Type | Description | Parent ID |
|-------------|------|-------------|-----------|
| `9fgvc/header` | `div` (flex row) | Header bar, padding 16px 24px, border-bottom, space-between | `9fgvc` |
| `9fgvc/header/title` | `h3` | "Filter Influencers" heading, font-semibold | `9fgvc/header` |
| `9fgvc/header/closeBtn` | `Button` | Close button, variant=ghost, icon=X, top-right | `9fgvc/header` |

### Body

| Component ID | Type | Description | Parent ID |
|-------------|------|-------------|-----------|
| `9fgvc/body` | `div` (flex col) | Body container, padding 24px, gap 24px, scrollable if overflow | `9fgvc` |

#### Community Section

| Component ID | Type | Description | Parent ID |
|-------------|------|-------------|-----------|
| `9fgvc/body/communityLabel` | `label` | "Community" section label, font-medium | `9fgvc/body` |
| `9fgvc/body/communityGroup` | `div` (flex col) | Checkbox group container, gap 12px | `9fgvc/body` |
| `9fgvc/body/cbAlpha` | `Checkbox` | "Alpha" checkbox with blue community dot, checked by default | `9fgvc/body/communityGroup` |
| `9fgvc/body/cbBeta` | `Checkbox` | "Beta" checkbox with green community dot, checked by default | `9fgvc/body/communityGroup` |
| `9fgvc/body/cbGamma` | `Checkbox` | "Gamma" checkbox with orange community dot, checked by default | `9fgvc/body/communityGroup` |
| `9fgvc/body/cbDelta` | `Checkbox` | "Delta" checkbox with purple community dot, checked by default | `9fgvc/body/communityGroup` |
| `9fgvc/body/cbBridge` | `Checkbox` | "Bridge" checkbox with red community dot, checked by default | `9fgvc/body/communityGroup` |

#### Status Section

| Component ID | Type | Description | Parent ID |
|-------------|------|-------------|-----------|
| `9fgvc/body/statusLabel` | `label` | "Status" section label, font-medium | `9fgvc/body` |
| `9fgvc/body/statusGroup` | `div` (flex row) | Radio button group container, gap 16px | `9fgvc/body` |
| `9fgvc/body/radioAll` | `Radio` | "All" radio button, selected by default | `9fgvc/body/statusGroup` |
| `9fgvc/body/radioActive` | `Radio` | "Active" radio button | `9fgvc/body/statusGroup` |
| `9fgvc/body/radioIdle` | `Radio` | "Idle" radio button | `9fgvc/body/statusGroup` |

#### Influence Score Range Section

| Component ID | Type | Description | Parent ID |
|-------------|------|-------------|-----------|
| `9fgvc/body/scoreLabel` | `label` | "Influence Score Range" section label, font-medium | `9fgvc/body` |
| `9fgvc/body/scoreRange` | `div` (flex row) | Min/Max input pair, gap 16px | `9fgvc/body` |
| `9fgvc/body/scoreMin` | `Input` (number) | "Min" labeled input, default value "0", min=0, max=100 | `9fgvc/body/scoreRange` |
| `9fgvc/body/scoreMax` | `Input` (number) | "Max" labeled input, default value "100", min=0, max=100 | `9fgvc/body/scoreRange` |

#### Sentiment Section

| Component ID | Type | Description | Parent ID |
|-------------|------|-------------|-----------|
| `9fgvc/body/sentimentLabel` | `label` | "Sentiment" section label, font-medium | `9fgvc/body` |
| `9fgvc/body/sentimentSelect` | `Select` | Sentiment dropdown, default "All", options: All, Positive, Neutral, Negative | `9fgvc/body` |

#### Min Connections Section

| Component ID | Type | Description | Parent ID |
|-------------|------|-------------|-----------|
| `9fgvc/body/connectionsLabel` | `label` | "Min Connections" section label, font-medium | `9fgvc/body` |
| `9fgvc/body/connectionsInput` | `Input` (number) | Minimum connections input, default value "0", min=0 | `9fgvc/body` |

### Footer

| Component ID | Type | Description | Parent ID |
|-------------|------|-------------|-----------|
| `9fgvc/footer` | `div` (flex row) | Footer bar, padding 16px 24px, border-top, justify-between | `9fgvc` |
| `9fgvc/footer/resetBtn` | `Button` | "Reset" button, variant=outline | `9fgvc/footer` |
| `9fgvc/footer/applyBtn` | `Button` | "Apply Filters" button, variant=default (primary), icon=SlidersHorizontal (left) | `9fgvc/footer` |

---

## 4. Design Tokens

### Colors

| Token | Value | Usage |
|-------|-------|-------|
| `--popover-bg` | `var(--popover)` | Popover background |
| `--popover-border` | `var(--border)` | Popover border and section dividers |
| `--popover-shadow` | `0 4px 24px rgba(0,0,0,0.12)` | Popover drop shadow |
| `--header-border` | `var(--border)` | Header bottom border |
| `--footer-border` | `var(--border)` | Footer top border |
| `--checkbox-checked` | `var(--primary)` | Checked checkbox fill |
| `--radio-selected` | `var(--primary)` | Selected radio button fill |
| `--input-border` | `var(--input)` | Input field border |
| `--input-focus-ring` | `var(--ring)` | Input focus ring color |
| `--community-alpha` | `#3b82f6` | Alpha community indicator dot |
| `--community-beta` | `#22c55e` | Beta community indicator dot |
| `--community-gamma` | `#f97316` | Gamma community indicator dot |
| `--community-delta` | `#a855f7` | Delta community indicator dot |
| `--community-bridge` | `#ef4444` | Bridge community indicator dot |

### Typography

| Element | Font | Size | Weight |
|---------|------|------|--------|
| Popover title | Instrument Serif | 16px | 600 |
| Section label | Geist | 14px | 500 |
| Checkbox/Radio label | Geist | 14px | 400 |
| Input label | Geist | 12px | 400 |
| Input value | Geist | 14px | 400 |
| Select value | Geist | 14px | 400 |
| Button text | Geist | 14px | 500 |

### Spacing

| Token | Value | Usage |
|-------|-------|-------|
| `--popover-width` | `600px` | Popover total width |
| `--popover-max-height` | `700px` | Popover max height |
| `--header-padding` | `16px 24px` | Header padding |
| `--body-padding` | `24px` | Body padding |
| `--body-section-gap` | `24px` | Gap between filter sections |
| `--checkbox-gap` | `12px` | Gap between checkbox items |
| `--radio-gap` | `16px` | Gap between radio items |
| `--footer-padding` | `16px 24px` | Footer padding |
| `--input-height` | `40px` | Number input height |
| `--popover-radius` | `8px` | Popover border radius |

---

## 5. Interaction Behavior

| Action | Trigger | Effect |
|--------|---------|--------|
| Open popover | Click "Filter" button on UI-08 | Popover slides in / fades in, anchored below the filter button. Focus trapped inside popover. |
| Close popover (X) | Click close X button | Popover closes without applying changes. Filter state reverts to last applied values. |
| Close popover (outside) | Click outside popover area | Same as close X — popover closes, changes discarded. |
| Close popover (Escape) | Press Escape key | Same as close X — popover closes, changes discarded. |
| Toggle community | Click a community checkbox | Toggles that community on/off. Visual check/uncheck. No immediate table effect until Apply. |
| Change status | Click a status radio button | Selects that status option. Only one can be selected. |
| Edit score range | Type in Min/Max inputs | Validates: Min <= Max, both 0-100. Red border on invalid. |
| Change sentiment | Select from dropdown | Selects sentiment filter option. |
| Edit min connections | Type in connections input | Validates: non-negative integer. |
| Reset filters | Click "Reset" button | All checkboxes checked, status "All", score 0-100, sentiment "All", connections 0. Resets to default state. |
| Apply filters | Click "Apply Filters" button | Closes popover. Sends filter params to parent (UI-08). Table re-fetches with filters applied, resets to page 1. Filter button on UI-08 shows active filter count badge. |
| Keyboard navigation | Tab key | Cycles through all interactive elements in order: checkboxes, radios, inputs, buttons. |

---

## 6. Data Binding (Backend API)

The filter popover does not directly call APIs. It constructs filter parameters and passes them to the parent UI-08 component, which applies them to the agent list API call.

| Filter Field | API Query Parameter | Type | Default |
|-------------|-------------------|------|---------|
| Community checkboxes | `community` | `string[]` (comma-separated) | All 5 selected |
| Status radios | `status` | `string` ("all", "active", "idle") | "all" |
| Score Min | `min_score` | `number` (0-100) | 0 |
| Score Max | `max_score` | `number` (0-100) | 100 |
| Sentiment | `sentiment` | `string` ("all", "positive", "neutral", "negative") | "all" |
| Min Connections | `min_connections` | `number` (>= 0) | 0 |

Resulting API call (made by UI-08):
```
GET /simulations/{id}/agents?community=alpha,beta,gamma&status=active&min_score=30&max_score=90&sentiment=positive&min_connections=5&page=1&limit=10
```

---

## 7. Pencil Node Reference

| Node ID | Element | Section |
|---------|---------|---------|
| `9fgvc` | Root popover frame (600x700) | -- |
| `9fgvc/header` | Popover header with title + close button | Top |
| `9fgvc/body` | Filter controls body | Center |
| `9fgvc/body/communityGroup` | Community checkbox group | Body section |
| `9fgvc/body/statusGroup` | Status radio button group | Body section |
| `9fgvc/body/scoreRange` | Influence score min/max inputs | Body section |
| `9fgvc/body/sentimentSelect` | Sentiment dropdown | Body section |
| `9fgvc/body/connectionsInput` | Min connections input | Body section |
| `9fgvc/footer` | Footer with Reset + Apply buttons | Bottom |
