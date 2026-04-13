# 28_SETTINGS_EXTENSIONS_SPEC

> **Status**: CURRENT
> **Version**: 0.1.0
> **Created**: 2026-04-13
> **Scope**: Settings page + runtime-configurable LLM providers (non-first-party)

This SPEC covers two parallel extensions to the settings surface that landed in
the 2026-04 cycle. They are grouped here because both touch `/api/v1/settings`
and the `SettingsPage` UI, and neither is large enough to warrant its own
numbered SPEC.

1. §1 — Chinese LLM provider integration (DeepSeek, Qwen, Moonshot, Zhipu GLM)
2. §2 — `DEFAULT_MAX_STEPS` reconciliation (365 → 50) with new Settings field

---

## 1. Chinese LLM Providers (CL-*)

### 1.1 Providers (CL-01)

Four OpenAI-compatible Chinese providers are wired as Tier-3-capable adapters.
All four share a single generic adapter (`OpenAICompatibleAdapter`) because
their HTTP surface is OpenAI-identical — only `base_url` + `api_key` +
`default_model` differ per provider.

| Provider | Default Model (2026-04) | Default Base URL | Notes |
|----------|-------------------------|------------------|-------|
| DeepSeek | `deepseek-chat` | `https://api.deepseek.com` | `-chat` auto-aliases V3.2 → V4; `-reasoner` for thinking mode |
| Qwen (Alibaba) | `qwen3-max` | `https://dashscope-intl.aliyuncs.com/compatible-mode/v1` | Mainland: swap host to `dashscope.aliyuncs.com` |
| Moonshot (Kimi) | `kimi-k2.5` | `https://api.moonshot.ai/v1` | Mainland: `api.moonshot.cn`; 256K ctx + Agent Swarm |
| Zhipu GLM | `glm-5.1` | `https://open.bigmodel.cn/api/paas/v4/` | International: `api.z.ai/api/paas/v4/`; #1 SWE-Bench Pro |

Version-pinning is via free-text model-name input on `SettingsPage` — new
model releases do **not** require a UI release.

### 1.2 Adapter Architecture (CL-02)

**File**: `backend/app/llm/openai_compat.py`

```
OpenAICompatibleAdapter (base)
  ├─ DeepSeekAdapter     (provider_name="deepseek")
  ├─ QwenAdapter         (provider_name="qwen")
  ├─ MoonshotAdapter     (provider_name="moonshot")
  └─ ZhipuGLMAdapter     (provider_name="glm")
```

Each subclass pins three class attributes — `provider_name`,
`default_base_url`, `default_model` — and inherits the full chat-completion
path (retry, rate-limit, auth-error, timeout handling) unchanged from the
base class. The base class wraps `openai.AsyncOpenAI(api_key, base_url=...)`.

**Embeddings are intentionally not implemented** on these providers — their
embed dimensions don't match the 768-dim pgvector schema. Embeddings remain
the responsibility of Ollama / OpenAI / Gemini.

### 1.3 Registration (CL-03)

**File**: `backend/app/api/deps.py`

Each adapter registers only when its API key is set (`if settings.{provider}_api_key:`).
Registration failures are logged at WARNING level but do not abort the request.

### 1.4 Tier-3 Routing (CL-04)

**File**: `backend/app/llm/registry.py`

`_ELITE_PROVIDERS` ordering is:

```python
_ELITE_PROVIDERS = [
    "claude", "openai", "gemini",          # Western (legacy priority)
    "deepseek", "qwen", "moonshot", "glm", # Chinese (added 2026-04)
]
```

When multiple elite adapters are registered, earlier entries win. The
ordering is a default; users who want Chinese providers preferred should
update the list (a future SPEC may surface this as a runtime setting).

### 1.5 Settings Surface (CL-05)

**GET `/api/v1/settings`** returns `{provider}_api_key_set` (boolean),
`{provider}_base_url`, `{provider}_model` for each of the four providers.
Secrets are **never** returned — only whether a key exists.

**PUT `/api/v1/settings`** accepts `{provider}_api_key`, `{provider}_base_url`,
`{provider}_model`. Sending an empty string for `_api_key` would wipe the key,
so the frontend only includes it in the payload when the user has typed a new
value.

### 1.6 UI Section (CL-06)

**File**: `frontend/src/pages/SettingsPage.tsx`

A single "Chinese LLM APIs (2026)" section houses the four providers, each
with three fields (API Key, Model, Base URL) and the standard eye-toggle for
the key field. The `Default Provider` dropdown at the top of the page
includes `deepseek`, `qwen`, `moonshot`, `glm` as options, so any of them
can be made the default Tier-1/2/3 fallback.

### 1.7 Acceptance Criteria

| ID | Criterion |
|----|-----------|
| CL-AC-01 | `_ELITE_PROVIDERS` contains all four Chinese providers |
| CL-AC-02 | Adapters register only when their API key env var is set |
| CL-AC-03 | `GET /settings` exposes `{provider}_api_key_set` bool but never the secret |
| CL-AC-04 | `PUT /settings` with empty-string `_api_key` does not leak via `GET` |
| CL-AC-05 | Settings UI has four sections: DeepSeek, Qwen, Moonshot, Zhipu GLM |
| CL-AC-06 | Model input is free-text (not a dropdown) so new models don't require UI release |
| CL-AC-07 | Default models match 2026-04 flagship releases (see §1.1 table) |

---

## 2. `DEFAULT_MAX_STEPS` Reconciliation (DMS-*)

### 2.1 Background (DMS-01)

The frontend had two conflicting step defaults:

- `DEFAULT_SIMULATION_DAYS = 365` (mis-named — a step is not a calendar day)
- `DEFAULT_MAX_STEPS = 50` (unused at the time)

While the backend default was `SIM_DEFAULT_MAX_STEPS = 50`, the frontend
injected `max_steps: 365` when creating simulations from `ControlPanel →
New Simulation`, so a fresh run would execute **365 LLM ticks** against a
1,000-agent graph — unnecessary cost and latency. Additionally, the name
"DAYS" leaked into glossary/tooltips, suggesting a calendar-time binding
that the engine does not enforce.

### 2.2 Resolution (DMS-02)

**File**: `frontend/src/config/constants.ts`

- `DEFAULT_SIMULATION_DAYS` **deleted**
- `DEFAULT_MAX_STEPS = 50` becomes the single source of truth
- `getDefaultMaxSteps()` helper reads `LS_KEY_DEFAULT_MAX_STEPS` from
  `localStorage`, falling back to `DEFAULT_MAX_STEPS` when absent or invalid

**Four runtime fallbacks updated** to use `DEFAULT_MAX_STEPS`:

| File | Old | New |
|------|-----|-----|
| `components/timeline/TimelinePanel.tsx` | `?? 365` | `?? DEFAULT_MAX_STEPS` |
| `pages/GlobalMetricsPage.tsx` | `?? 365` | `?? DEFAULT_MAX_STEPS` |
| `components/control/hooks/useAutoStepLoop.ts` | `?? 365` | `?? DEFAULT_MAX_STEPS` |
| `components/control/hooks/useProjectScenarioSync.ts` | `max_steps: 365` | `max_steps: getDefaultMaxSteps()` |

### 2.3 Settings Page Field (DMS-03)

**File**: `frontend/src/pages/SettingsPage.tsx` — "Simulation Defaults" section

A new `<input type="number">` labeled **Default Max Steps** appears at the
top of the section. Accepted range: `[1, MAX_SIMULATION_STEPS]` where
`MAX_SIMULATION_STEPS = 1000`. On Save, the value is persisted to
`localStorage` under `LS_KEY_DEFAULT_MAX_STEPS`.

This is a **frontend-only** setting — the backend's `SIM_DEFAULT_MAX_STEPS`
remains 50 and is not exposed through `/api/v1/settings` in this cycle.
Per-workstation preference is the explicit intent.

### 2.4 Acceptance Criteria

| ID | Criterion |
|----|-----------|
| DMS-AC-01 | `DEFAULT_SIMULATION_DAYS` is no longer exported from `constants.ts` |
| DMS-AC-02 | `DEFAULT_MAX_STEPS` equals **50** (aligned with backend) |
| DMS-AC-03 | New simulations created via ControlPanel use `getDefaultMaxSteps()` |
| DMS-AC-04 | Settings page has a "Default Max Steps" input clamped to `[1, 1000]` |
| DMS-AC-05 | Invalid / out-of-range `localStorage` value falls back to 50 silently |
| DMS-AC-06 | Tooltip / hint text clarifies "step ≠ day" |

### 2.5 Tests

- `frontend/src/__tests__/UIFlowSpec.test.tsx` — assertion updated:
  `DEFAULT_MAX_STEPS === 50` (was `DEFAULT_SIMULATION_DAYS === 365`).
- `frontend/src/__tests__/SettingsPage.test.tsx` — all 12 tests pass
  with the new field present.

---

## 3. Related SPECs

- `24_UI_WORKFLOW_SPEC.md` §2.2.5 — EmergentEventsPanel layout dimensions
  (independent change from the same 2026-04 cycle).
- `05_LLM_SPEC.md` (IP-protected) — Tier routing + adapter interface
  contract. Chinese providers extend the adapter pattern without changing
  the contract.
- `06_API_SPEC.md` (IP-protected) — `/settings` endpoint; this SPEC adds
  `_api_key_set` / `_base_url` / `_model` triples per new provider.
