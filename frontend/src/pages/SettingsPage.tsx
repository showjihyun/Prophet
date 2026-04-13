/**
 * SettingsPage — LLM provider configuration & simulation defaults.
 * @spec docs/spec/ui/UI_12_SETTINGS.md
 * @spec docs/spec/06_API_SPEC.md#7-settings-endpoints
 */
import { useEffect, useState, useCallback } from "react";
import {
  Save,
  TestTube2,
  CheckCircle2,
  XCircle,
  Loader2,
} from "lucide-react";
import { apiClient } from "../api/client";
import type { SettingsResponse } from "../api/client";
import HelpTooltip from "../components/shared/HelpTooltip";
import {
  DEFAULT_MAX_STEPS,
  LS_KEY_DEFAULT_MAX_STEPS,
  MAX_SIMULATION_STEPS,
  getDefaultMaxSteps,
} from "@/config/constants";

/* ------------------------------------------------------------------ */
/* Types                                                               */
/* ------------------------------------------------------------------ */

interface OllamaTestResult {
  status: "ok" | "error";
  model?: string;
  latency_ms?: number;
  message?: string;
}

/* ------------------------------------------------------------------ */
/* Component                                                           */
/* ------------------------------------------------------------------ */

export default function SettingsPage() {
  /* ---------- state ---------- */
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState<boolean | null>(null);

  // LLM
  const [defaultProvider, setDefaultProvider] = useState("ollama");
  const [ollamaBaseUrl, setOllamaBaseUrl] = useState("http://localhost:11434");
  const [ollamaDefaultModel, setOllamaDefaultModel] = useState("llama3.1:8b");
  const [slmModel, setSlmModel] = useState("llama3.1:8b");
  const [ollamaEmbedModel, setOllamaEmbedModel] = useState("llama3.1:8b");
  const [anthropicApiKey, setAnthropicApiKey] = useState("");
  const [anthropicKeySet, setAnthropicKeySet] = useState(false);
  const [anthropicModel, setAnthropicModel] = useState("claude-sonnet-4-6");
  const [openaiApiKey, setOpenaiApiKey] = useState("");
  const [openaiKeySet, setOpenaiKeySet] = useState(false);
  const [openaiModel, setOpenaiModel] = useState("gpt-4o");
  // Gemini — real adapter at backend/app/llm/gemini_client.py
  const [geminiApiKey, setGeminiApiKey] = useState("");
  const [geminiKeySet, setGeminiKeySet] = useState(false);
  const [geminiModel, setGeminiModel] = useState("gemini-2.0-flash");
  const [geminiEmbedModel, setGeminiEmbedModel] = useState(
    "models/text-embedding-004",
  );
  const [showGeminiKey, setShowGeminiKey] = useState(false);
  // vLLM — self-hosted inference server, alternative to Ollama
  const [vllmBaseUrl, setVllmBaseUrl] = useState("");
  const [vllmModel, setVllmModel] = useState("meta-llama/Llama-3.1-8B-Instruct");
  const [vllmMaxConcurrent, setVllmMaxConcurrent] = useState(64);

  // Chinese Top 3 (2026, OpenAI-compatible)
  const [deepseekApiKey, setDeepseekApiKey] = useState("");
  const [deepseekKeySet, setDeepseekKeySet] = useState(false);
  const [deepseekBaseUrl, setDeepseekBaseUrl] = useState("https://api.deepseek.com");
  const [deepseekModel, setDeepseekModel] = useState("deepseek-chat");
  const [showDeepseekKey, setShowDeepseekKey] = useState(false);
  const [qwenApiKey, setQwenApiKey] = useState("");
  const [qwenKeySet, setQwenKeySet] = useState(false);
  const [qwenBaseUrl, setQwenBaseUrl] = useState(
    "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
  );
  const [qwenModel, setQwenModel] = useState("qwen3-max");
  const [showQwenKey, setShowQwenKey] = useState(false);
  const [moonshotApiKey, setMoonshotApiKey] = useState("");
  const [moonshotKeySet, setMoonshotKeySet] = useState(false);
  const [moonshotBaseUrl, setMoonshotBaseUrl] = useState("https://api.moonshot.ai/v1");
  const [moonshotModel, setMoonshotModel] = useState("kimi-k2.5");
  const [showMoonshotKey, setShowMoonshotKey] = useState(false);
  const [glmApiKey, setGlmApiKey] = useState("");
  const [glmKeySet, setGlmKeySet] = useState(false);
  const [glmBaseUrl, setGlmBaseUrl] = useState("https://open.bigmodel.cn/api/paas/v4/");
  const [glmModel, setGlmModel] = useState("glm-5.1");
  const [showGlmKey, setShowGlmKey] = useState(false);

  // Simulation
  const [slmLlmRatio, setSlmLlmRatio] = useState(0.5);
  const [tier3Ratio, setTier3Ratio] = useState(0.1);
  const [cacheTtl, setCacheTtl] = useState(3600);
  // Default max_steps for new simulations — stored client-side in
  // localStorage (the backend exposes this via SIM_DEFAULT_MAX_STEPS
  // but the GET /settings endpoint does not surface it yet, so we
  // override per-workstation). Initial read happens once in useEffect
  // below so SSR/test envs with stubbed `window` don't crash here.
  const [defaultMaxSteps, setDefaultMaxSteps] = useState<number>(DEFAULT_MAX_STEPS);

  // Ollama models list
  const [ollamaModels, setOllamaModels] = useState<string[]>([]);

  // API key visibility toggles
  const [showAnthropicKey, setShowAnthropicKey] = useState(false);
  const [showOpenaiKey, setShowOpenaiKey] = useState(false);

  // Test connection
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<OllamaTestResult | null>(null);

  /* ---------- load ---------- */
  const fetchSettings = useCallback(async () => {
    try {
      const data: SettingsResponse = await apiClient.settings.get();
      setDefaultProvider(data.llm.default_provider);
      setOllamaBaseUrl(data.llm.ollama_base_url);
      setOllamaDefaultModel(data.llm.ollama_default_model);
      setSlmModel(data.llm.slm_model);
      setOllamaEmbedModel(data.llm.ollama_embed_model);
      setAnthropicModel(data.llm.anthropic_model);
      setAnthropicKeySet(data.llm.anthropic_api_key_set);
      setOpenaiModel(data.llm.openai_model);
      setOpenaiKeySet(data.llm.openai_api_key_set);
      // Gemini
      setGeminiModel(data.llm.gemini_model);
      setGeminiEmbedModel(data.llm.gemini_embed_model);
      setGeminiKeySet(data.llm.gemini_api_key_set);
      // vLLM
      setVllmBaseUrl(data.llm.vllm_base_url);
      setVllmModel(data.llm.vllm_model);
      setVllmMaxConcurrent(data.llm.vllm_max_concurrent);
      // Chinese Top 3
      setDeepseekBaseUrl(data.llm.deepseek_base_url);
      setDeepseekModel(data.llm.deepseek_model);
      setDeepseekKeySet(data.llm.deepseek_api_key_set);
      setQwenBaseUrl(data.llm.qwen_base_url);
      setQwenModel(data.llm.qwen_model);
      setQwenKeySet(data.llm.qwen_api_key_set);
      setMoonshotBaseUrl(data.llm.moonshot_base_url);
      setMoonshotModel(data.llm.moonshot_model);
      setMoonshotKeySet(data.llm.moonshot_api_key_set);
      setGlmBaseUrl(data.llm.glm_base_url);
      setGlmModel(data.llm.glm_model);
      setGlmKeySet(data.llm.glm_api_key_set);
      setSlmLlmRatio(data.simulation.slm_llm_ratio);
      setTier3Ratio(data.simulation.llm_tier3_ratio);
      setCacheTtl(data.simulation.llm_cache_ttl);
    } catch {
      /* settings page still renders with defaults */
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchOllamaModels = useCallback(async () => {
    try {
      const data = await apiClient.settings.listOllamaModels();
      setOllamaModels(data.models);
    } catch {
      setOllamaModels([]);
    }
  }, []);

  useEffect(() => {
    fetchSettings();
    fetchOllamaModels();
    setDefaultMaxSteps(getDefaultMaxSteps());
  }, [fetchSettings, fetchOllamaModels]);

  /* ---------- actions ---------- */
  async function handleSave() {
    setSaving(true);
    setSaveSuccess(null);
    try {
      const payload: Record<string, unknown> = {
        llm: {
          default_provider: defaultProvider,
          ollama_base_url: ollamaBaseUrl,
          ollama_default_model: ollamaDefaultModel,
          slm_model: slmModel,
          ollama_embed_model: ollamaEmbedModel,
          anthropic_model: anthropicModel,
          openai_model: openaiModel,
          gemini_model: geminiModel,
          gemini_embed_model: geminiEmbedModel,
          vllm_base_url: vllmBaseUrl,
          vllm_model: vllmModel,
          vllm_max_concurrent: vllmMaxConcurrent,
          // Chinese Top 3
          deepseek_base_url: deepseekBaseUrl,
          deepseek_model: deepseekModel,
          qwen_base_url: qwenBaseUrl,
          qwen_model: qwenModel,
          moonshot_base_url: moonshotBaseUrl,
          moonshot_model: moonshotModel,
          glm_base_url: glmBaseUrl,
          glm_model: glmModel,
          // Secrets are write-only — only send when the user typed a new
          // value. An empty string would wipe the stored key.
          ...(anthropicApiKey ? { anthropic_api_key: anthropicApiKey } : {}),
          ...(openaiApiKey ? { openai_api_key: openaiApiKey } : {}),
          ...(geminiApiKey ? { gemini_api_key: geminiApiKey } : {}),
          ...(deepseekApiKey ? { deepseek_api_key: deepseekApiKey } : {}),
          ...(qwenApiKey ? { qwen_api_key: qwenApiKey } : {}),
          ...(moonshotApiKey ? { moonshot_api_key: moonshotApiKey } : {}),
          ...(glmApiKey ? { glm_api_key: glmApiKey } : {}),
        },
        simulation: {
          slm_llm_ratio: slmLlmRatio,
          llm_tier3_ratio: tier3Ratio,
          llm_cache_ttl: cacheTtl,
        },
      };
      await apiClient.settings.update(payload as never);
      // Persist the frontend-only simulation default (max_steps).
      try {
        window.localStorage.setItem(
          LS_KEY_DEFAULT_MAX_STEPS,
          String(defaultMaxSteps),
        );
      } catch {
        /* localStorage unavailable (private mode, quota) — non-fatal */
      }
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(null), 3000);
    } catch {
      setSaveSuccess(false);
    } finally {
      setSaving(false);
    }
  }

  async function handleTestOllama() {
    setTesting(true);
    setTestResult(null);
    try {
      const result = await apiClient.settings.testOllama();
      setTestResult(result as OllamaTestResult);
    } catch {
      setTestResult({ status: "error", message: "Request failed" });
    } finally {
      setTesting(false);
    }
  }

  /* ---------- helpers ---------- */
  function modelSelect(
    testId: string,
    value: string,
    onChange: (v: string) => void,
    models: string[],
  ) {
    return (
      <select
        id={testId}
        data-testid={testId}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full h-9 rounded-md border border-[var(--border)] bg-[var(--card)] px-3 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
      >
        {/* Always include current value even if not in list */}
        {!models.includes(value) && <option value={value}>{value}</option>}
        {models.map((m) => (
          <option key={m} value={m}>
            {m}
          </option>
        ))}
      </select>
    );
  }

  /* ---------- render ---------- */
  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center h-full">
        <Loader2 className="w-6 h-6 animate-spin text-[var(--muted-foreground)]" />
      </div>
    );
  }

  return (
    <div className="h-full bg-[var(--background)]">
      <main className="overflow-y-auto p-8">
        <h1 className="text-2xl font-bold font-display text-[var(--foreground)] mb-6">Settings</h1>

        {/* ---- LLM Provider Configuration ---- */}
        <section className="bg-[var(--card)] rounded-lg border border-[var(--border)] p-6 mb-6">
          <h2 className="text-lg font-semibold text-[var(--foreground)] mb-4">
            LLM Provider Configuration
          </h2>

          {/* Default Provider */}
          <div className="mb-5">
            <label htmlFor="default-provider-select" className="flex items-center gap-1.5 text-sm font-medium text-[var(--muted-foreground)] mb-1.5">
              Default Provider
              <HelpTooltip term="settingsDefaultProvider" />
            </label>
            <select
              id="default-provider-select"
              data-testid="default-provider-select"
              value={defaultProvider}
              onChange={(e) => setDefaultProvider(e.target.value)}
              className="w-64 h-9 rounded-md border border-[var(--border)] bg-[var(--card)] px-3 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
            >
              <option value="ollama">Ollama (On-Premise)</option>
              <option value="vllm">vLLM (Self-Hosted)</option>
              <option value="claude">Claude API</option>
              <option value="openai">OpenAI API</option>
              <option value="gemini">Gemini API</option>
              <option value="deepseek">DeepSeek (CN)</option>
              <option value="qwen">Qwen / Alibaba (CN)</option>
              <option value="moonshot">Moonshot Kimi (CN)</option>
              <option value="glm">Zhipu GLM (CN)</option>
            </select>
          </div>

          <hr className="my-5 border-[var(--border)]" />

          {/* --- Ollama --- */}
          <h3 className="text-sm font-semibold text-[var(--foreground)] mb-3">
            Ollama (On-Premise)
          </h3>
          <div className="grid grid-cols-2 gap-4 mb-4">
            <div>
              <label htmlFor="ollama-base-url" className="flex items-center gap-1.5 text-sm text-[var(--muted-foreground)] mb-1">
                Base URL
                <HelpTooltip term="settingsProviderBaseUrl" />
              </label>
              <input
                id="ollama-base-url"
                data-testid="ollama-base-url"
                type="url"
                autoComplete="url"
                value={ollamaBaseUrl}
                onChange={(e) => setOllamaBaseUrl(e.target.value)}
                className="w-full h-9 rounded-md border border-[var(--border)] px-3 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
              />
            </div>
            <div>
              <label htmlFor="ollama-default-model" className="flex items-center gap-1.5 text-sm text-[var(--muted-foreground)] mb-1">
                Default Model
                <HelpTooltip term="settingsProviderModel" />
              </label>
              {modelSelect("ollama-default-model", ollamaDefaultModel, setOllamaDefaultModel, ollamaModels)}
            </div>
            <div>
              <label htmlFor="ollama-slm-model" className="flex items-center gap-1.5 text-sm text-[var(--muted-foreground)] mb-1">
                SLM Model (Tier 1)
                <HelpTooltip term="settingsSlmModel" />
              </label>
              {modelSelect("ollama-slm-model", slmModel, setSlmModel, ollamaModels)}
            </div>
            <div>
              <label htmlFor="ollama-embed-model" className="flex items-center gap-1.5 text-sm text-[var(--muted-foreground)] mb-1">
                Embed Model
                <HelpTooltip term="settingsEmbedModel" />
              </label>
              {modelSelect("ollama-embed-model", ollamaEmbedModel, setOllamaEmbedModel, ollamaModels)}
            </div>
          </div>

          {/* Test Connection */}
          <div className="flex items-center gap-3 mb-5">
            <button
              onClick={handleTestOllama}
              disabled={testing}
              className="inline-flex items-center gap-2 h-9 px-4 rounded-md border border-[var(--border)] bg-[var(--card)] text-sm font-medium text-[var(--foreground)] hover:bg-[var(--accent)] disabled:opacity-50"
            >
              {testing ? (
                <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" />
              ) : (
                <TestTube2 className="w-4 h-4" aria-hidden="true" />
              )}
              Test Connection
            </button>
            {testResult && (
              <span
                className={`inline-flex items-center gap-1.5 text-sm ${
                  testResult.status === "ok" ? "text-[var(--sentiment-positive)]" : "text-[var(--destructive)]"
                }`}
              >
                {testResult.status === "ok" ? (
                  <>
                    <CheckCircle2 className="w-4 h-4" aria-hidden="true" />
                    Connected ({testResult.latency_ms}ms)
                  </>
                ) : (
                  <>
                    <XCircle className="w-4 h-4" aria-hidden="true" />
                    {testResult.message || "Connection failed"}
                  </>
                )}
              </span>
            )}
          </div>

          <hr className="my-5 border-[var(--border)]" />

          {/* --- Claude API --- */}
          <h3 className="text-sm font-semibold text-[var(--foreground)] mb-3">
            Claude API (External)
          </h3>
          <div className="grid grid-cols-2 gap-4 mb-5">
            <div>
              <label htmlFor="anthropic-api-key" className="flex items-center gap-1.5 text-sm text-[var(--muted-foreground)] mb-1">
                API Key
                <HelpTooltip term="settingsProviderApiKey" />
              </label>
              <div className="relative">
                <input
                  id="anthropic-api-key"
                  data-testid="anthropic-api-key"
                  type={showAnthropicKey ? "text" : "password"}
                  autoComplete="off"
                  value={anthropicApiKey}
                  onChange={(e) => setAnthropicApiKey(e.target.value)}
                  placeholder={anthropicKeySet ? "sk-ant-*******" : "Not set"}
                  className="w-full h-9 rounded-md border border-[var(--border)] px-3 pr-10 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
                />
                <button
                  type="button"
                  onClick={() => setShowAnthropicKey((v) => !v)}
                  aria-label={showAnthropicKey ? "Hide API key" : "Show API key"}
                  className="absolute inset-y-0 right-0 flex items-center px-2.5 text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
                >
                  {showAnthropicKey ? <EyeOffIcon /> : <EyeIcon />}
                </button>
              </div>
              <p className="mt-1 text-[11px] text-[var(--muted-foreground)]">
                API key is sent only when saving. Stored keys are not retrievable.
              </p>
            </div>
            <div>
              <label htmlFor="anthropic-model" className="flex items-center gap-1.5 text-sm text-[var(--muted-foreground)] mb-1">
                Model
                <HelpTooltip term="settingsProviderModel" />
              </label>
              <input
                id="anthropic-model"
                data-testid="anthropic-model"
                type="text"
                value={anthropicModel}
                onChange={(e) => setAnthropicModel(e.target.value)}
                placeholder="claude-sonnet-4-6"
                className="w-full h-9 rounded-md border border-[var(--border)] bg-[var(--card)] px-3 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
              />
              <p className="mt-1 text-[11px] text-[var(--muted-foreground)]">
                Any Anthropic model id (e.g. claude-sonnet-4-6, claude-opus-4-6). Free-text so new models don&apos;t require a UI release.
              </p>
            </div>
          </div>

          <hr className="my-5 border-[var(--border)]" />

          {/* --- OpenAI API --- */}
          <h3 className="text-sm font-semibold text-[var(--foreground)] mb-3">
            OpenAI API (External)
          </h3>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label htmlFor="openai-api-key" className="flex items-center gap-1.5 text-sm text-[var(--muted-foreground)] mb-1">
                API Key
                <HelpTooltip term="settingsProviderApiKey" />
              </label>
              <div className="relative">
                <input
                  id="openai-api-key"
                  data-testid="openai-api-key"
                  type={showOpenaiKey ? "text" : "password"}
                  autoComplete="off"
                  value={openaiApiKey}
                  onChange={(e) => setOpenaiApiKey(e.target.value)}
                  placeholder={openaiKeySet ? "sk-*******" : "Not set"}
                  className="w-full h-9 rounded-md border border-[var(--border)] px-3 pr-10 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
                />
                <button
                  type="button"
                  onClick={() => setShowOpenaiKey((v) => !v)}
                  aria-label={showOpenaiKey ? "Hide API key" : "Show API key"}
                  className="absolute inset-y-0 right-0 flex items-center px-2.5 text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
                >
                  {showOpenaiKey ? <EyeOffIcon /> : <EyeIcon />}
                </button>
              </div>
              <p className="mt-1 text-[11px] text-[var(--muted-foreground)]">
                API key is sent only when saving. Stored keys are not retrievable.
              </p>
            </div>
            <div>
              <label htmlFor="openai-model" className="flex items-center gap-1.5 text-sm text-[var(--muted-foreground)] mb-1">
                Model
                <HelpTooltip term="settingsProviderModel" />
              </label>
              <input
                id="openai-model"
                data-testid="openai-model"
                type="text"
                value={openaiModel}
                onChange={(e) => setOpenaiModel(e.target.value)}
                placeholder="gpt-4o"
                className="w-full h-9 rounded-md border border-[var(--border)] bg-[var(--card)] px-3 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
              />
              <p className="mt-1 text-[11px] text-[var(--muted-foreground)]">
                Any OpenAI model id (e.g. gpt-4o, gpt-4o-mini, gpt-5, o3). Free-text so new models don&apos;t require a UI release.
              </p>
            </div>
          </div>

          <hr className="my-5 border-[var(--border)]" />

          {/* --- Gemini API --- */}
          <h3 className="text-sm font-semibold text-[var(--foreground)] mb-3">
            Gemini API (External)
          </h3>
          <div className="grid grid-cols-2 gap-4 mb-5">
            <div>
              <label htmlFor="gemini-api-key" className="flex items-center gap-1.5 text-sm text-[var(--muted-foreground)] mb-1">
                API Key
                <HelpTooltip term="settingsProviderApiKey" />
              </label>
              <div className="relative">
                <input
                  id="gemini-api-key"
                  data-testid="gemini-api-key"
                  type={showGeminiKey ? "text" : "password"}
                  autoComplete="off"
                  value={geminiApiKey}
                  onChange={(e) => setGeminiApiKey(e.target.value)}
                  placeholder={geminiKeySet ? "AIza*******" : "Not set"}
                  className="w-full h-9 rounded-md border border-[var(--border)] px-3 pr-10 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
                />
                <button
                  type="button"
                  onClick={() => setShowGeminiKey((v) => !v)}
                  aria-label={showGeminiKey ? "Hide API key" : "Show API key"}
                  className="absolute inset-y-0 right-0 flex items-center px-2.5 text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
                >
                  {showGeminiKey ? <EyeOffIcon /> : <EyeIcon />}
                </button>
              </div>
              <p className="mt-1 text-[11px] text-[var(--muted-foreground)]">
                API key is sent only when saving. Stored keys are not retrievable.
              </p>
            </div>
            <div>
              <label htmlFor="gemini-model" className="flex items-center gap-1.5 text-sm text-[var(--muted-foreground)] mb-1">
                Model
                <HelpTooltip term="settingsProviderModel" />
              </label>
              <input
                id="gemini-model"
                data-testid="gemini-model"
                type="text"
                value={geminiModel}
                onChange={(e) => setGeminiModel(e.target.value)}
                placeholder="gemini-2.0-flash"
                className="w-full h-9 rounded-md border border-[var(--border)] bg-[var(--card)] px-3 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
              />
              <p className="mt-1 text-[11px] text-[var(--muted-foreground)]">
                e.g. gemini-2.0-flash, gemini-2.0-pro, gemini-1.5-flash.
              </p>
            </div>
            <div>
              <label htmlFor="gemini-embed-model" className="flex items-center gap-1.5 text-sm text-[var(--muted-foreground)] mb-1">
                Embed Model
                <HelpTooltip term="settingsEmbedModel" />
              </label>
              <input
                id="gemini-embed-model"
                data-testid="gemini-embed-model"
                type="text"
                value={geminiEmbedModel}
                onChange={(e) => setGeminiEmbedModel(e.target.value)}
                placeholder="models/text-embedding-004"
                className="w-full h-9 rounded-md border border-[var(--border)] bg-[var(--card)] px-3 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
              />
            </div>
          </div>
        </section>

        {/* ---- Chinese Top 3 (2026, OpenAI-compatible) ---- */}
        <section className="bg-[var(--card)] rounded-lg border border-[var(--border)] p-6 mb-6">
          <h2 className="text-lg font-semibold text-[var(--foreground)] mb-1">
            Chinese LLM APIs (2026)
          </h2>
          <p className="text-[12px] text-[var(--muted-foreground)] mb-4">
            All four (DeepSeek / Qwen / Moonshot / Zhipu GLM) expose
            OpenAI-compatible chat endpoints, so they reuse the same adapter
            path with only the base URL swapped. Override base URL if you
            need the mainland-CN endpoint variant.
          </p>

          {/* --- DeepSeek --- */}
          <h3 className="text-sm font-semibold text-[var(--foreground)] mb-3">
            DeepSeek
          </h3>
          <div className="grid grid-cols-2 gap-4 mb-4">
            <div>
              <label htmlFor="deepseek-api-key" className="flex items-center gap-1.5 text-sm text-[var(--muted-foreground)] mb-1">
                API Key
              </label>
              <div className="relative">
                <input
                  id="deepseek-api-key"
                  data-testid="deepseek-api-key"
                  type={showDeepseekKey ? "text" : "password"}
                  autoComplete="off"
                  value={deepseekApiKey}
                  onChange={(e) => setDeepseekApiKey(e.target.value)}
                  placeholder={deepseekKeySet ? "sk-*******" : "Not set"}
                  className="w-full h-9 rounded-md border border-[var(--border)] px-3 pr-10 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
                />
                <button
                  type="button"
                  onClick={() => setShowDeepseekKey((v) => !v)}
                  aria-label={showDeepseekKey ? "Hide API key" : "Show API key"}
                  className="absolute inset-y-0 right-0 flex items-center px-2.5 text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
                >
                  {showDeepseekKey ? <EyeOffIcon /> : <EyeIcon />}
                </button>
              </div>
            </div>
            <div>
              <label htmlFor="deepseek-model" className="flex items-center gap-1.5 text-sm text-[var(--muted-foreground)] mb-1">
                Model
              </label>
              <input
                id="deepseek-model"
                data-testid="deepseek-model"
                type="text"
                value={deepseekModel}
                onChange={(e) => setDeepseekModel(e.target.value)}
                placeholder="deepseek-chat"
                className="w-full h-9 rounded-md border border-[var(--border)] bg-[var(--card)] px-3 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
              />
              <p className="mt-1 text-[11px] text-[var(--muted-foreground)]">
                2026-04: <span className="font-mono">deepseek-chat</span> auto-routes to V3.2 non-thinking; <span className="font-mono">deepseek-reasoner</span> for thinking mode. V4 (2026-03 flagship) coming to the same aliases.
              </p>
            </div>
            <div className="col-span-2">
              <label htmlFor="deepseek-base-url" className="flex items-center gap-1.5 text-sm text-[var(--muted-foreground)] mb-1">
                Base URL
              </label>
              <input
                id="deepseek-base-url"
                data-testid="deepseek-base-url"
                type="url"
                value={deepseekBaseUrl}
                onChange={(e) => setDeepseekBaseUrl(e.target.value)}
                placeholder="https://api.deepseek.com"
                className="w-full h-9 rounded-md border border-[var(--border)] px-3 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
              />
            </div>
          </div>

          <hr className="my-5 border-[var(--border)]" />

          {/* --- Qwen --- */}
          <h3 className="text-sm font-semibold text-[var(--foreground)] mb-3">
            Qwen (Alibaba DashScope)
          </h3>
          <div className="grid grid-cols-2 gap-4 mb-4">
            <div>
              <label htmlFor="qwen-api-key" className="flex items-center gap-1.5 text-sm text-[var(--muted-foreground)] mb-1">
                API Key
              </label>
              <div className="relative">
                <input
                  id="qwen-api-key"
                  data-testid="qwen-api-key"
                  type={showQwenKey ? "text" : "password"}
                  autoComplete="off"
                  value={qwenApiKey}
                  onChange={(e) => setQwenApiKey(e.target.value)}
                  placeholder={qwenKeySet ? "sk-*******" : "Not set"}
                  className="w-full h-9 rounded-md border border-[var(--border)] px-3 pr-10 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
                />
                <button
                  type="button"
                  onClick={() => setShowQwenKey((v) => !v)}
                  aria-label={showQwenKey ? "Hide API key" : "Show API key"}
                  className="absolute inset-y-0 right-0 flex items-center px-2.5 text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
                >
                  {showQwenKey ? <EyeOffIcon /> : <EyeIcon />}
                </button>
              </div>
            </div>
            <div>
              <label htmlFor="qwen-model" className="flex items-center gap-1.5 text-sm text-[var(--muted-foreground)] mb-1">
                Model
              </label>
              <input
                id="qwen-model"
                data-testid="qwen-model"
                type="text"
                value={qwenModel}
                onChange={(e) => setQwenModel(e.target.value)}
                placeholder="qwen3-max"
                className="w-full h-9 rounded-md border border-[var(--border)] bg-[var(--card)] px-3 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
              />
              <p className="mt-1 text-[11px] text-[var(--muted-foreground)]">
                2026-04: <span className="font-mono">qwen3-max</span> (flagship, 2026-01-23 snapshot), <span className="font-mono">qwen3.5-plus</span> (1M ctx, 2026-02-15), <span className="font-mono">qwen3.5-flash</span>.
              </p>
            </div>
            <div className="col-span-2">
              <label htmlFor="qwen-base-url" className="flex items-center gap-1.5 text-sm text-[var(--muted-foreground)] mb-1">
                Base URL
              </label>
              <input
                id="qwen-base-url"
                data-testid="qwen-base-url"
                type="url"
                value={qwenBaseUrl}
                onChange={(e) => setQwenBaseUrl(e.target.value)}
                placeholder="https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
                className="w-full h-9 rounded-md border border-[var(--border)] px-3 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
              />
              <p className="mt-1 text-[11px] text-[var(--muted-foreground)]">
                Mainland CN: swap host to <span className="font-mono">dashscope.aliyuncs.com</span>.
              </p>
            </div>
          </div>

          <hr className="my-5 border-[var(--border)]" />

          {/* --- Moonshot Kimi --- */}
          <h3 className="text-sm font-semibold text-[var(--foreground)] mb-3">
            Moonshot (Kimi)
          </h3>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label htmlFor="moonshot-api-key" className="flex items-center gap-1.5 text-sm text-[var(--muted-foreground)] mb-1">
                API Key
              </label>
              <div className="relative">
                <input
                  id="moonshot-api-key"
                  data-testid="moonshot-api-key"
                  type={showMoonshotKey ? "text" : "password"}
                  autoComplete="off"
                  value={moonshotApiKey}
                  onChange={(e) => setMoonshotApiKey(e.target.value)}
                  placeholder={moonshotKeySet ? "sk-*******" : "Not set"}
                  className="w-full h-9 rounded-md border border-[var(--border)] px-3 pr-10 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
                />
                <button
                  type="button"
                  onClick={() => setShowMoonshotKey((v) => !v)}
                  aria-label={showMoonshotKey ? "Hide API key" : "Show API key"}
                  className="absolute inset-y-0 right-0 flex items-center px-2.5 text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
                >
                  {showMoonshotKey ? <EyeOffIcon /> : <EyeIcon />}
                </button>
              </div>
            </div>
            <div>
              <label htmlFor="moonshot-model" className="flex items-center gap-1.5 text-sm text-[var(--muted-foreground)] mb-1">
                Model
              </label>
              <input
                id="moonshot-model"
                data-testid="moonshot-model"
                type="text"
                value={moonshotModel}
                onChange={(e) => setMoonshotModel(e.target.value)}
                placeholder="kimi-k2.5"
                className="w-full h-9 rounded-md border border-[var(--border)] bg-[var(--card)] px-3 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
              />
              <p className="mt-1 text-[11px] text-[var(--muted-foreground)]">
                2026-04: <span className="font-mono">kimi-k2.5</span> (flagship, 256K ctx, Agent Swarm — 2026-01), legacy <span className="font-mono">moonshot-v1-8k / 32k / 128k</span>.
              </p>
            </div>
            <div className="col-span-2">
              <label htmlFor="moonshot-base-url" className="flex items-center gap-1.5 text-sm text-[var(--muted-foreground)] mb-1">
                Base URL
              </label>
              <input
                id="moonshot-base-url"
                data-testid="moonshot-base-url"
                type="url"
                value={moonshotBaseUrl}
                onChange={(e) => setMoonshotBaseUrl(e.target.value)}
                placeholder="https://api.moonshot.ai/v1"
                className="w-full h-9 rounded-md border border-[var(--border)] px-3 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
              />
              <p className="mt-1 text-[11px] text-[var(--muted-foreground)]">
                Mainland CN: swap host to <span className="font-mono">api.moonshot.cn</span>.
              </p>
            </div>
          </div>

          <hr className="my-5 border-[var(--border)]" />

          {/* --- Zhipu GLM --- */}
          <h3 className="text-sm font-semibold text-[var(--foreground)] mb-3">
            Zhipu GLM (BigModel / Z.ai)
          </h3>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label htmlFor="glm-api-key" className="flex items-center gap-1.5 text-sm text-[var(--muted-foreground)] mb-1">
                API Key
              </label>
              <div className="relative">
                <input
                  id="glm-api-key"
                  data-testid="glm-api-key"
                  type={showGlmKey ? "text" : "password"}
                  autoComplete="off"
                  value={glmApiKey}
                  onChange={(e) => setGlmApiKey(e.target.value)}
                  placeholder={glmKeySet ? "****.*******" : "Not set"}
                  className="w-full h-9 rounded-md border border-[var(--border)] px-3 pr-10 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
                />
                <button
                  type="button"
                  onClick={() => setShowGlmKey((v) => !v)}
                  aria-label={showGlmKey ? "Hide API key" : "Show API key"}
                  className="absolute inset-y-0 right-0 flex items-center px-2.5 text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
                >
                  {showGlmKey ? <EyeOffIcon /> : <EyeIcon />}
                </button>
              </div>
            </div>
            <div>
              <label htmlFor="glm-model" className="flex items-center gap-1.5 text-sm text-[var(--muted-foreground)] mb-1">
                Model
              </label>
              <input
                id="glm-model"
                data-testid="glm-model"
                type="text"
                value={glmModel}
                onChange={(e) => setGlmModel(e.target.value)}
                placeholder="glm-5.1"
                className="w-full h-9 rounded-md border border-[var(--border)] bg-[var(--card)] px-3 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
              />
              <p className="mt-1 text-[11px] text-[var(--muted-foreground)]">
                2026-04: <span className="font-mono">glm-5.1</span> (flagship, 200K ctx, #1 SWE-Bench Pro — 2026-04), <span className="font-mono">glm-5</span>, <span className="font-mono">glm-4.6</span>, <span className="font-mono">glm-4-flash</span>.
              </p>
            </div>
            <div className="col-span-2">
              <label htmlFor="glm-base-url" className="flex items-center gap-1.5 text-sm text-[var(--muted-foreground)] mb-1">
                Base URL
              </label>
              <input
                id="glm-base-url"
                data-testid="glm-base-url"
                type="url"
                value={glmBaseUrl}
                onChange={(e) => setGlmBaseUrl(e.target.value)}
                placeholder="https://open.bigmodel.cn/api/paas/v4/"
                className="w-full h-9 rounded-md border border-[var(--border)] px-3 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
              />
              <p className="mt-1 text-[11px] text-[var(--muted-foreground)]">
                International: <span className="font-mono">https://api.z.ai/api/paas/v4/</span>.
              </p>
            </div>
          </div>
        </section>

        {/* ---- Self-Hosted Inference: vLLM ---- */}
        <section className="bg-[var(--card)] rounded-lg border border-[var(--border)] p-6 mb-6">
          <h2 className="text-lg font-semibold text-[var(--foreground)] mb-4">
            Self-Hosted: vLLM
          </h2>
          <p className="text-[12px] text-[var(--muted-foreground)] mb-4">
            Alternative to Ollama for higher-throughput workloads on GPU
            hardware. Leave Base URL empty if you&apos;re not running a vLLM server.
          </p>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label htmlFor="vllm-base-url" className="flex items-center gap-1.5 text-sm text-[var(--muted-foreground)] mb-1">
                Base URL
                <HelpTooltip term="settingsProviderBaseUrl" />
              </label>
              <input
                id="vllm-base-url"
                data-testid="vllm-base-url"
                type="url"
                autoComplete="url"
                value={vllmBaseUrl}
                onChange={(e) => setVllmBaseUrl(e.target.value)}
                placeholder="http://localhost:8000 (empty = disabled)"
                className="w-full h-9 rounded-md border border-[var(--border)] px-3 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
              />
            </div>
            <div>
              <label htmlFor="vllm-model" className="flex items-center gap-1.5 text-sm text-[var(--muted-foreground)] mb-1">
                Model
                <HelpTooltip term="settingsProviderModel" />
              </label>
              <input
                id="vllm-model"
                data-testid="vllm-model"
                type="text"
                value={vllmModel}
                onChange={(e) => setVllmModel(e.target.value)}
                placeholder="meta-llama/Llama-3.1-8B-Instruct"
                className="w-full h-9 rounded-md border border-[var(--border)] bg-[var(--card)] px-3 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
              />
            </div>
            <div>
              <label htmlFor="vllm-max-concurrent" className="flex items-center gap-1.5 text-sm text-[var(--muted-foreground)] mb-1">
                Max Concurrent Requests
                <HelpTooltip term="settingsVllmMaxConcurrent" />
              </label>
              <input
                id="vllm-max-concurrent"
                data-testid="vllm-max-concurrent"
                type="number"
                min={1}
                max={512}
                step={1}
                value={vllmMaxConcurrent}
                onChange={(e) => setVllmMaxConcurrent(Number(e.target.value))}
                className="w-32 h-9 rounded-md border border-[var(--border)] px-3 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
              />
              <p className="mt-1 text-[11px] text-[var(--muted-foreground)]">
                1-512. Higher = more parallelism, more GPU memory pressure.
              </p>
            </div>
          </div>
        </section>

        {/* ---- Simulation Defaults ---- */}
        <section className="bg-[var(--card)] rounded-lg border border-[var(--border)] p-6 mb-6">
          <h2 className="text-lg font-semibold text-[var(--foreground)] mb-4">
            Simulation Defaults
          </h2>

          <div className="space-y-4">
            {/* Default Max Steps */}
            <div>
              <label
                htmlFor="default-max-steps"
                className="flex items-center gap-1.5 text-sm text-[var(--muted-foreground)] mb-1"
              >
                Default Max Steps
              </label>
              <input
                id="default-max-steps"
                data-testid="default-max-steps"
                type="number"
                min={1}
                max={MAX_SIMULATION_STEPS}
                step={1}
                value={defaultMaxSteps}
                onChange={(e) => {
                  const parsed = Number.parseInt(e.target.value, 10);
                  if (!Number.isFinite(parsed)) return;
                  const clamped = Math.max(
                    1,
                    Math.min(MAX_SIMULATION_STEPS, parsed),
                  );
                  setDefaultMaxSteps(clamped);
                }}
                className="w-32 h-9 rounded-md border border-[var(--border)] px-3 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
              />
              <p className="mt-1 text-[11px] text-[var(--muted-foreground)]">
                Number of ticks a new simulation runs by default (1–
                {MAX_SIMULATION_STEPS}). A step is one full agent cycle, not a
                calendar day. Backend default: {DEFAULT_MAX_STEPS}.
              </p>
            </div>

            {/* SLM/LLM Ratio */}
            <div>
              <label htmlFor="slm-llm-ratio" className="flex items-center gap-1.5 text-sm text-[var(--muted-foreground)] mb-1">
                SLM/LLM Ratio: <span className="font-mono">{slmLlmRatio.toFixed(2)}</span>
                <HelpTooltip term="slmLlmRatio" />
              </label>
              <input
                id="slm-llm-ratio"
                data-testid="slm-llm-ratio"
                type="range"
                min={0}
                max={1}
                step={0.01}
                value={slmLlmRatio}
                onChange={(e) => setSlmLlmRatio(Number(e.target.value))}
                className="w-80 accent-[var(--foreground)]"
              />
            </div>

            {/* Tier 3 Ratio */}
            <div>
              <label htmlFor="tier3-ratio" className="flex items-center gap-1.5 text-sm text-[var(--muted-foreground)] mb-1">
                LLM Tier 3 Ratio
                <HelpTooltip term="settingsTier3Ratio" />
              </label>
              <input
                id="tier3-ratio"
                data-testid="tier3-ratio"
                type="number"
                min={0}
                max={1}
                step={0.01}
                value={tier3Ratio}
                onChange={(e) => setTier3Ratio(Number(e.target.value))}
                className="w-32 h-9 rounded-md border border-[var(--border)] px-3 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
              />
            </div>

            {/* Cache TTL */}
            <div>
              <label htmlFor="cache-ttl" className="flex items-center gap-1.5 text-sm text-[var(--muted-foreground)] mb-1">
                LLM Cache TTL (seconds)
                <HelpTooltip term="settingsCacheTtl" />
              </label>
              <input
                id="cache-ttl"
                data-testid="cache-ttl"
                type="number"
                min={0}
                step={60}
                value={cacheTtl}
                onChange={(e) => setCacheTtl(Number(e.target.value))}
                className="w-32 h-9 rounded-md border border-[var(--border)] px-3 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
              />
            </div>
          </div>
        </section>

        {/* Platform / RecSys selection lives on the Campaign Setup page where
         * each simulation picks its own — there is no global default, so a
         * Settings-level dropdown would be a no-op. Removed on 2026-04-11. */}

        {/* ---- Save ---- */}
        <div className="flex items-center gap-3">
          <button
            onClick={handleSave}
            disabled={saving}
            className="inline-flex items-center gap-2 h-10 px-6 rounded-md bg-[var(--primary)] text-[var(--primary-foreground)] text-sm font-medium hover:bg-[var(--primary)]/90 disabled:opacity-50"
          >
            {saving ? (
              <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" />
            ) : (
              <Save className="w-4 h-4" aria-hidden="true" />
            )}
            Save Settings
          </button>
          {saveSuccess === true && (
            <span className="text-sm text-[var(--sentiment-positive)] flex items-center gap-1">
              <CheckCircle2 className="w-4 h-4" aria-hidden="true" /> Saved
            </span>
          )}
          {saveSuccess === false && (
            <span className="text-sm text-[var(--destructive)] flex items-center gap-1">
              <XCircle className="w-4 h-4" aria-hidden="true" /> Save failed
            </span>
          )}
        </div>
      </main>
    </div>
  );
}

/* Inline eye icons for API key visibility toggles */
function EyeIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  );
}

function EyeOffIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94" />
      <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19" />
      <line x1="1" y1="1" x2="23" y2="23" />
    </svg>
  );
}
