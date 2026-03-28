# UI-10 — Agent Intervene Modal SPEC
Version: 0.1.0 | Status: DRAFT
Source: pencil-shadcn.pen > Frame: Agent Intervene Modal (ID: XLwVu)

---

## 1. Overview

The Agent Intervene Modal is a dialog that appears when the "Intervene" button is clicked on the Agent Detail page (UI-04). It allows users to inject events, modify sentiment, change community assignments, or boost influence for a specific agent during a running simulation. The modal provides structured fields for intervention type, target scope, parameters, a free-text prompt area, and behavioral options including force-LLM override.

---

## 2. Layout Structure

```
+--------------------------------------------------+
| Header                            [XLwVu/header] |
| "Intervene on Agent #3847"             [X close] |
| "Configure and apply an intervention..."         |
+--------------------------------------------------+
| Body (padding 24px, gap 20px)     [XLwVu/body]   |
|                                                   |
| Intervention Type                                 |
| [ Select intervention type...            v ]      |
|                                                   |
| Target Scope                                      |
| [ Individual Agent                       v ]      |
|                                                   |
| Duration (steps)     Strength (0-1)               |
| [ 100 ]              [ 0.75 ]                     |
|                                                   |
| Intervention Message / Prompt                     |
| +-----------------------------------------------+|
| |                                               ||
| | (textarea)                                    ||
| |                                               ||
| +-----------------------------------------------+|
|                                                   |
| Options                                           |
| [x] Notify connected agents of intervention      |
| [x] Log intervention in cascade analytics         |
| [ ] Override Prophet Tier (force LLM)  [toggle]   |
|                                                   |
+--------------------------------------------------+
| Footer                            [XLwVu/footer] |
| [Cancel]               [⚡ Apply Intervention]   |
+--------------------------------------------------+
```

---

## 3. Components

### Header

| Component ID | Type | Description | Parent ID |
|-------------|------|-------------|-----------|
| `XLwVu/header` | `div` (flex col) | Header section, padding 24px 24px 16px, border-bottom | `XLwVu` |
| `XLwVu/header/title` | `h2` | "Intervene on Agent #3847" heading, font-semibold. Agent ID is dynamic. | `XLwVu/header` |
| `XLwVu/header/description` | `p` | "Configure and apply an intervention to modify this agent's behavior during simulation." muted-foreground | `XLwVu/header` |
| `XLwVu/header/closeBtn` | `Button` | Close button, variant=ghost, icon=X, absolute top-right | `XLwVu/header` |

### Body

| Component ID | Type | Description | Parent ID |
|-------------|------|-------------|-----------|
| `XLwVu/body` | `div` (flex col) | Body container, padding 24px, gap 20px, scrollable if overflow | `XLwVu` |

#### Intervention Type

| Component ID | Type | Description | Parent ID |
|-------------|------|-------------|-----------|
| `XLwVu/body/typeLabel` | `label` | "Intervention Type" label, font-medium | `XLwVu/body` |
| `XLwVu/body/typeSelect` | `Select` | Dropdown with placeholder "Select intervention type...", options: "Inject Message", "Modify Sentiment", "Change Community", "Boost Influence" | `XLwVu/body` |

#### Target Scope

| Component ID | Type | Description | Parent ID |
|-------------|------|-------------|-----------|
| `XLwVu/body/scopeLabel` | `label` | "Target Scope" label, font-medium | `XLwVu/body` |
| `XLwVu/body/scopeSelect` | `Select` | Dropdown with options: "Individual Agent", "Community", "Network Neighbors" | `XLwVu/body` |

#### Parameter Row

| Component ID | Type | Description | Parent ID |
|-------------|------|-------------|-----------|
| `XLwVu/body/paramRow` | `div` (grid 2-col) | Two-column parameter row, gap 16px | `XLwVu/body` |
| `XLwVu/body/durationLabel` | `label` | "Duration (steps)" label, font-medium | `XLwVu/body/paramRow` |
| `XLwVu/body/durationInput` | `Input` (number) | Duration input, default value "100", min=1 | `XLwVu/body/paramRow` |
| `XLwVu/body/strengthLabel` | `label` | "Strength (0-1)" label, font-medium | `XLwVu/body/paramRow` |
| `XLwVu/body/strengthInput` | `Input` (number) | Strength input, default value "0.75", min=0, max=1, step=0.05 | `XLwVu/body/paramRow` |

#### Intervention Message

| Component ID | Type | Description | Parent ID |
|-------------|------|-------------|-----------|
| `XLwVu/body/messageLabel` | `label` | "Intervention Message / Prompt" label, font-medium | `XLwVu/body` |
| `XLwVu/body/messageTextarea` | `Textarea` | Multi-line text input for intervention message or LLM prompt, min-height 100px, placeholder "Enter the message or prompt to inject..." | `XLwVu/body` |

#### Options

| Component ID | Type | Description | Parent ID |
|-------------|------|-------------|-----------|
| `XLwVu/body/optionsLabel` | `label` | "Options" section label, font-medium | `XLwVu/body` |
| `XLwVu/body/optionsGroup` | `div` (flex col) | Options group container, gap 12px | `XLwVu/body` |
| `XLwVu/body/cbNotify` | `Checkbox` | "Notify connected agents of intervention" — checked by default | `XLwVu/body/optionsGroup` |
| `XLwVu/body/cbLog` | `Checkbox` | "Log intervention in cascade analytics" — checked by default | `XLwVu/body/optionsGroup` |
| `XLwVu/body/tierOverride` | `div` (flex row) | "Override Prophet Tier (force LLM)" label + Switch toggle, off by default | `XLwVu/body/optionsGroup` |
| `XLwVu/body/tierSwitch` | `Switch` | Toggle switch for forcing LLM tier override, default off | `XLwVu/body/tierOverride` |

### Footer

| Component ID | Type | Description | Parent ID |
|-------------|------|-------------|-----------|
| `XLwVu/footer` | `div` (flex row) | Footer bar, padding 16px 24px, border-top, justify-end, gap 12px | `XLwVu` |
| `XLwVu/footer/cancelBtn` | `Button` | "Cancel" button, variant=outline | `XLwVu/footer` |
| `XLwVu/footer/applyBtn` | `Button` | "Apply Intervention" button, variant=default (primary), icon=Zap (left) | `XLwVu/footer` |

---

## 4. Design Tokens

### Colors

| Token | Value | Usage |
|-------|-------|-------|
| `--modal-bg` | `var(--popover)` | Modal background |
| `--modal-overlay` | `rgba(0, 0, 0, 0.5)` | Background overlay/scrim |
| `--modal-border` | `var(--border)` | Modal border |
| `--modal-shadow` | `0 8px 32px rgba(0,0,0,0.2)` | Modal drop shadow |
| `--header-border` | `var(--border)` | Header bottom border |
| `--footer-border` | `var(--border)` | Footer top border |
| `--input-border` | `var(--input)` | Input/select/textarea border |
| `--input-focus-ring` | `var(--ring)` | Focus ring color |
| `--checkbox-checked` | `var(--primary)` | Checked checkbox fill |
| `--switch-checked` | `var(--primary)` | Switch on state |
| `--switch-unchecked` | `var(--muted)` | Switch off state |
| `--zap-icon` | `#f59e0b` | Zap icon accent color on apply button |
| `--destructive-warning` | `#f59e0b` | Tier override warning indicator |

### Typography

| Element | Font | Size | Weight |
|---------|------|------|--------|
| Modal title | Inter / system | 18px | 600 |
| Modal description | Inter / system | 14px | 400 |
| Section/field label | Inter / system | 14px | 500 |
| Input value | Inter / system | 14px | 400 |
| Select value | Inter / system | 14px | 400 |
| Textarea text | Inter / system | 14px | 400 |
| Checkbox/option label | Inter / system | 14px | 400 |
| Button text | Inter / system | 14px | 500 |

### Spacing

| Token | Value | Usage |
|-------|-------|-------|
| `--modal-width` | `560px` | Modal total width |
| `--modal-max-height` | `700px` | Modal max height |
| `--modal-radius` | `8px` | Modal border radius |
| `--header-padding` | `24px 24px 16px` | Header padding |
| `--body-padding` | `24px` | Body padding |
| `--body-field-gap` | `20px` | Gap between form fields |
| `--param-col-gap` | `16px` | Gap between parameter columns |
| `--options-gap` | `12px` | Gap between option items |
| `--footer-padding` | `16px 24px` | Footer padding |
| `--footer-btn-gap` | `12px` | Gap between footer buttons |
| `--textarea-min-height` | `100px` | Textarea minimum height |

---

## 5. Interaction Behavior

| Action | Trigger | Effect |
|--------|---------|--------|
| Open modal | Click "Intervene" button on UI-04 | Modal fades in with overlay. Focus trapped inside modal. Body scroll locked. |
| Close modal (X) | Click close X button | Modal closes. No changes applied. Form state cleared. |
| Close modal (Cancel) | Click "Cancel" button | Same as close X — modal closes without changes. |
| Close modal (Escape) | Press Escape key | Same as close X — modal closes without changes. |
| Close modal (overlay) | Click on overlay/scrim behind modal | Same as close X — modal closes without changes. |
| Select intervention type | Choose from type dropdown | Updates placeholder to selected value. May show type-specific guidance text below the select. |
| Select target scope | Choose from scope dropdown | Updates scope. "Community" scope shows additional community selector. "Network Neighbors" shows depth input. |
| Edit duration | Type in duration input | Validates: positive integer >= 1. |
| Edit strength | Type in strength input | Validates: 0.0 to 1.0. Red border on out-of-range. |
| Edit message | Type in textarea | Free-text input, no character limit. Used as injection message or LLM prompt depending on intervention type. |
| Toggle notify | Click notify checkbox | Toggles whether connected agents are notified of the intervention event. |
| Toggle log | Click log checkbox | Toggles whether the intervention is recorded in cascade analytics. |
| Toggle tier override | Click tier override switch | Toggles LLM tier override. When on, shows warning: "This will use Tier 3 (Elite LLM) regardless of agent tier assignment." |
| Apply intervention | Click "Apply Intervention" button | Validates all fields. If valid: POST to API, modal closes, toast notification "Intervention applied to Agent #{id}". If invalid: highlights invalid fields with red borders and error messages. |
| Form validation | On apply attempt | Required: intervention type, target scope. Duration must be >= 1. Strength must be 0-1. At least one option or message should be provided. |
| Loading state | After apply click, during API call | "Apply Intervention" button shows spinner, disabled. All form fields disabled during submission. |

---

## 6. Data Binding (Backend API)

| Component | API Endpoint | Method | Payload / Response |
|-----------|-------------|--------|-------------------|
| Apply intervention (agent modify) | `PATCH /simulations/{id}/agents/{agentId}` | PATCH | `{ intervention_type, target_scope, duration, strength, message, options: { notify_connected, log_cascade, force_llm } }` -> `{ success, message }` |
| Apply intervention (event inject) | `POST /simulations/{id}/inject-event` | POST | `{ agent_id, event_type: "intervention", payload: { type, scope, duration, strength, message, options } }` -> `{ success, event_id }` |
| Agent data (pre-fill) | `GET /simulations/{id}/agents/{agentId}` | GET | `{ id, community, tier, influence_score }` — used to populate header and defaults |

### Intervention Type to API Mapping

| Intervention Type | Primary API | Secondary API |
|------------------|------------|---------------|
| Inject Message | `POST /simulations/{id}/inject-event` | — |
| Modify Sentiment | `PATCH /simulations/{id}/agents/{agentId}` | — |
| Change Community | `PATCH /simulations/{id}/agents/{agentId}` | — |
| Boost Influence | `PATCH /simulations/{id}/agents/{agentId}` | `POST /simulations/{id}/inject-event` (if notify_connected) |

---

## 7. Pencil Node Reference

| Node ID | Element | Section |
|---------|---------|---------|
| `XLwVu` | Root modal frame (560x700) | -- |
| `XLwVu/header` | Modal header with title + description + close | Top |
| `XLwVu/body` | Form body with all input fields | Center |
| `XLwVu/body/typeSelect` | Intervention type dropdown | Body field |
| `XLwVu/body/scopeSelect` | Target scope dropdown | Body field |
| `XLwVu/body/paramRow` | Duration + Strength parameter row | Body field |
| `XLwVu/body/messageTextarea` | Intervention message textarea | Body field |
| `XLwVu/body/optionsGroup` | Options checkboxes + toggle | Body field |
| `XLwVu/body/tierSwitch` | Tier override toggle switch | Body option |
| `XLwVu/footer` | Footer with Cancel + Apply buttons | Bottom |
