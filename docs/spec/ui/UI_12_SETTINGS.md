# UI-12 — Settings SPEC
Version: 0.1.0 | Status: DRAFT
Source: AppSidebar navigation > Settings

---

## 1. Overview

Settings page for configuring LLM providers, simulation defaults, and system preferences.
Accessible from AppSidebar > Settings. Changes are persisted via API and take effect on next simulation run.

---

## 2. Layout Structure

```
+---------+----------------------------------------------------------+
| Sidebar | Main Content (padding 32px)                              |
| 256px   |                                                          |
|         | "Settings" title                                         |
|         |                                                          |
|         | +--- LLM Provider Configuration ----------------------+  |
|         | | Default Provider: [Ollama v]                         |  |
|         | |                                                      |  |
|         | | Ollama (On-Premise)                                  |  |
|         | |   Base URL: [http://localhost:11434]                  |  |
|         | |   Default Model: [llama3.1:8b        v] (auto-detect)|  |
|         | |   SLM Model (Tier 1): [llama3.1:8b   v]              |  |
|         | |   Embed Model: [llama3.1:8b          v]              |  |
|         | |   [Test Connection]                                   |  |
|         | |                                                      |  |
|         | | Claude API (External)                                |  |
|         | |   API Key: [sk-ant-*******]                           |  |
|         | |   Model: [claude-sonnet-4-6 v]                        |  |
|         | |                                                      |  |
|         | | OpenAI API (External)                                |  |
|         | |   API Key: [sk-*******]                               |  |
|         | |   Model: [gpt-4o v]                                   |  |
|         | +------------------------------------------------------+  |
|         |                                                          |
|         | +--- Simulation Defaults -----------------------------+  |
|         | | SLM/LLM Ratio: [====*====] 0.5                      |  |
|         | | LLM Tier 3 Ratio: [0.1]                              |  |
|         | | LLM Cache TTL: [3600] seconds                        |  |
|         | +------------------------------------------------------+  |
|         |                                                          |
|         | [Save Settings] primary button                           |
+---------+----------------------------------------------------------+
```

## 3. Interaction Behavior

- On page load: fetch current settings from `GET /api/v1/settings`
- Ollama "Test Connection": calls Ollama health_check, shows success/error badge
- Ollama model dropdowns: auto-populated from `GET /api/v1/settings/ollama-models` (calls Ollama /api/tags)
- Save: `PUT /api/v1/settings` persists to backend config/env
- API keys: masked display, only sent on change

## 4. Data Binding

| Component | API Endpoint |
|-----------|-------------|
| Load settings | `GET /api/v1/settings` |
| Save settings | `PUT /api/v1/settings` |
| List Ollama models | `GET /api/v1/settings/ollama-models` |
| Test Ollama | `POST /api/v1/settings/test-ollama` |

## 5. Acceptance Criteria

| ID | Test | Expected |
|----|------|----------|
| UI12-01 | Navigate to /settings | Settings page renders with sidebar active on Settings |
| UI12-02 | Page load fetches GET /api/v1/settings | Form fields populated with current values |
| UI12-03 | Ollama model dropdowns populated from /ollama-models | Dropdown shows available models |
| UI12-04 | Test Connection button calls POST /test-ollama | Green badge on success, red on failure |
| UI12-05 | Save Settings calls PUT /api/v1/settings | Saves form data, shows success toast |
| UI12-06 | API keys display masked | Only asterisks shown, raw key not in DOM |
