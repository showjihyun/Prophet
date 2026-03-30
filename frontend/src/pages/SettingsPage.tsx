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
import AppSidebar from "../components/shared/AppSidebar";
import { apiClient } from "../api/client";
import type { SettingsResponse } from "../api/client";

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

  // Simulation
  const [slmLlmRatio, setSlmLlmRatio] = useState(0.5);
  const [tier3Ratio, setTier3Ratio] = useState(0.1);
  const [cacheTtl, setCacheTtl] = useState(3600);

  // Ollama models list
  const [ollamaModels, setOllamaModels] = useState<string[]>([]);

  // Platform & RecSys
  const [platforms, setPlatforms] = useState<{ name: string; display_name: string }[]>([]);
  const [recsysAlgos, setRecsysAlgos] = useState<{ name: string }[]>([]);
  const [platform, setPlatform] = useState("default");
  const [recsys, setRecsys] = useState("weighted");

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
    apiClient.settings.listPlatforms().then(d => setPlatforms((d.platforms || []) as { name: string; display_name: string }[])).catch(() => {});
    apiClient.settings.listRecsys().then(d => setRecsysAlgos((d.algorithms || []) as { name: string }[])).catch(() => {});
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
          ...(anthropicApiKey ? { anthropic_api_key: anthropicApiKey } : {}),
          ...(openaiApiKey ? { openai_api_key: openaiApiKey } : {}),
        },
        simulation: {
          slm_llm_ratio: slmLlmRatio,
          llm_tier3_ratio: tier3Ratio,
          llm_cache_ttl: cacheTtl,
        },
      };
      await apiClient.settings.update(payload as never);
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
            <label className="block text-sm font-medium text-[var(--muted-foreground)] mb-1.5">
              Default Provider
            </label>
            <select
              data-testid="default-provider-select"
              value={defaultProvider}
              onChange={(e) => setDefaultProvider(e.target.value)}
              className="w-64 h-9 rounded-md border border-[var(--border)] bg-[var(--card)] px-3 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
            >
              <option value="ollama">Ollama (On-Premise)</option>
              <option value="claude">Claude API</option>
              <option value="openai">OpenAI API</option>
            </select>
          </div>

          <hr className="my-5 border-[var(--border)]" />

          {/* --- Ollama --- */}
          <h3 className="text-sm font-semibold text-[var(--foreground)] mb-3">
            Ollama (On-Premise)
          </h3>
          <div className="grid grid-cols-2 gap-4 mb-4">
            <div>
              <label className="block text-sm text-[var(--muted-foreground)] mb-1">Base URL</label>
              <input
                data-testid="ollama-base-url"
                type="text"
                value={ollamaBaseUrl}
                onChange={(e) => setOllamaBaseUrl(e.target.value)}
                className="w-full h-9 rounded-md border border-[var(--border)] px-3 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
              />
            </div>
            <div>
              <label className="block text-sm text-[var(--muted-foreground)] mb-1">Default Model</label>
              {modelSelect("ollama-default-model", ollamaDefaultModel, setOllamaDefaultModel, ollamaModels)}
            </div>
            <div>
              <label className="block text-sm text-[var(--muted-foreground)] mb-1">SLM Model (Tier 1)</label>
              {modelSelect("ollama-slm-model", slmModel, setSlmModel, ollamaModels)}
            </div>
            <div>
              <label className="block text-sm text-[var(--muted-foreground)] mb-1">Embed Model</label>
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
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <TestTube2 className="w-4 h-4" />
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
                    <CheckCircle2 className="w-4 h-4" />
                    Connected ({testResult.latency_ms}ms)
                  </>
                ) : (
                  <>
                    <XCircle className="w-4 h-4" />
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
              <label className="block text-sm text-[var(--muted-foreground)] mb-1">API Key</label>
              <input
                data-testid="anthropic-api-key"
                type="password"
                value={anthropicApiKey}
                onChange={(e) => setAnthropicApiKey(e.target.value)}
                placeholder={anthropicKeySet ? "sk-ant-*******" : "Not set"}
                className="w-full h-9 rounded-md border border-[var(--border)] px-3 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
              />
            </div>
            <div>
              <label className="block text-sm text-[var(--muted-foreground)] mb-1">Model</label>
              <select
                data-testid="anthropic-model"
                value={anthropicModel}
                onChange={(e) => setAnthropicModel(e.target.value)}
                className="w-full h-9 rounded-md border border-[var(--border)] bg-[var(--card)] px-3 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
              >
                <option value="claude-sonnet-4-6">claude-sonnet-4-6</option>
                <option value="claude-opus-4-6">claude-opus-4-6</option>
                <option value="claude-haiku-4-5">claude-haiku-4-5</option>
              </select>
            </div>
          </div>

          <hr className="my-5 border-[var(--border)]" />

          {/* --- OpenAI API --- */}
          <h3 className="text-sm font-semibold text-[var(--foreground)] mb-3">
            OpenAI API (External)
          </h3>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-[var(--muted-foreground)] mb-1">API Key</label>
              <input
                data-testid="openai-api-key"
                type="password"
                value={openaiApiKey}
                onChange={(e) => setOpenaiApiKey(e.target.value)}
                placeholder={openaiKeySet ? "sk-*******" : "Not set"}
                className="w-full h-9 rounded-md border border-[var(--border)] px-3 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
              />
            </div>
            <div>
              <label className="block text-sm text-[var(--muted-foreground)] mb-1">Model</label>
              <select
                data-testid="openai-model"
                value={openaiModel}
                onChange={(e) => setOpenaiModel(e.target.value)}
                className="w-full h-9 rounded-md border border-[var(--border)] bg-[var(--card)] px-3 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
              >
                <option value="gpt-4o">gpt-4o</option>
                <option value="gpt-4o-mini">gpt-4o-mini</option>
                <option value="gpt-4-turbo">gpt-4-turbo</option>
              </select>
            </div>
          </div>
        </section>

        {/* ---- Simulation Defaults ---- */}
        <section className="bg-[var(--card)] rounded-lg border border-[var(--border)] p-6 mb-6">
          <h2 className="text-lg font-semibold text-[var(--foreground)] mb-4">
            Simulation Defaults
          </h2>

          <div className="space-y-4">
            {/* SLM/LLM Ratio */}
            <div>
              <label className="block text-sm text-[var(--muted-foreground)] mb-1">
                SLM/LLM Ratio: <span className="font-mono">{slmLlmRatio.toFixed(2)}</span>
              </label>
              <input
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
              <label className="block text-sm text-[var(--muted-foreground)] mb-1">LLM Tier 3 Ratio</label>
              <input
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
              <label className="block text-sm text-[var(--muted-foreground)] mb-1">
                LLM Cache TTL (seconds)
              </label>
              <input
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

        {/* ---- Platform Configuration ---- */}
        <section className="bg-[var(--card)] rounded-lg border border-[var(--border)] p-6 mb-6">
          <h2 className="text-lg font-semibold text-[var(--foreground)] mb-4">
            Platform Simulation
          </h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-[var(--muted-foreground)] mb-1">
                Platform
              </label>
              <select
                value={platform}
                onChange={(e) => setPlatform(e.target.value)}
                className="w-full h-9 rounded-md border border-[var(--border)] bg-[var(--card)] px-3 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
              >
                {platforms.map((p) => (
                  <option key={p.name} value={p.name}>
                    {p.display_name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-[var(--muted-foreground)] mb-1">
                RecSys Algorithm
              </label>
              <select
                value={recsys}
                onChange={(e) => setRecsys(e.target.value)}
                className="w-full h-9 rounded-md border border-[var(--border)] bg-[var(--card)] px-3 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
              >
                {recsysAlgos.map((r) => (
                  <option key={r.name} value={r.name}>
                    {r.name}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </section>

        {/* ---- Save ---- */}
        <div className="flex items-center gap-3">
          <button
            onClick={handleSave}
            disabled={saving}
            className="inline-flex items-center gap-2 h-10 px-6 rounded-md bg-[var(--foreground)] text-white text-sm font-medium hover:bg-[var(--foreground)]/90 disabled:opacity-50"
          >
            {saving ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Save className="w-4 h-4" />
            )}
            Save Settings
          </button>
          {saveSuccess === true && (
            <span className="text-sm text-[var(--sentiment-positive)] flex items-center gap-1">
              <CheckCircle2 className="w-4 h-4" /> Saved
            </span>
          )}
          {saveSuccess === false && (
            <span className="text-sm text-[var(--destructive)] flex items-center gap-1">
              <XCircle className="w-4 h-4" /> Save failed
            </span>
          )}
        </div>
      </main>
    </div>
  );
}
