/**
 * CommunityManagePage — CRUD interface for community templates.
 * @spec docs/spec/07_FRONTEND_SPEC.md#community-manage-page
 */
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import PageNav from "../components/shared/PageNav";
import { apiClient, type CommunityTemplate, type CommunityTemplateInput } from "../api/client";

const PERSONALITY_FIELDS = [
  "openness",
  "skepticism",
  "trend_following",
  "brand_loyalty",
  "social_influence",
] as const;

type PersonalityField = typeof PERSONALITY_FIELDS[number];

const AGENT_TYPES = [
  "consumer",
  "early_adopter",
  "skeptic",
  "expert",
  "influencer",
  "bridge",
];

interface TemplateFormState {
  name: string;
  agent_type: string;
  default_size: number;
  description: string;
  personality_profile: Record<PersonalityField, number>;
}

const DEFAULT_FORM: TemplateFormState = {
  name: "",
  agent_type: "consumer",
  default_size: 100,
  description: "",
  personality_profile: {
    openness: 0.5,
    skepticism: 0.5,
    trend_following: 0.5,
    brand_loyalty: 0.5,
    social_influence: 0.5,
  },
};

function templateToForm(t: CommunityTemplate): TemplateFormState {
  return {
    name: t.name,
    agent_type: t.agent_type,
    default_size: t.default_size,
    description: t.description,
    personality_profile: {
      openness: t.personality_profile["openness"] ?? 0.5,
      skepticism: t.personality_profile["skepticism"] ?? 0.5,
      trend_following: t.personality_profile["trend_following"] ?? 0.5,
      brand_loyalty: t.personality_profile["brand_loyalty"] ?? 0.5,
      social_influence: t.personality_profile["social_influence"] ?? 0.5,
    },
  };
}

export default function CommunityManagePage() {
  const navigate = useNavigate();
  const [templates, setTemplates] = useState<CommunityTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [showAddForm, setShowAddForm] = useState(false);
  const [form, setForm] = useState<TemplateFormState>(DEFAULT_FORM);
  const [saving, setSaving] = useState(false);

  const loadTemplates = () => {
    setLoading(true);
    apiClient.communityTemplates
      .list()
      .then((res) => {
        setTemplates(res.templates);
        setError(null);
      })
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadTemplates();
  }, []);

  const startEdit = (t: CommunityTemplate) => {
    setEditingId(t.template_id);
    setForm(templateToForm(t));
    setShowAddForm(false);
  };

  const startAdd = () => {
    setEditingId(null);
    setForm(DEFAULT_FORM);
    setShowAddForm(true);
  };

  const cancelForm = () => {
    setEditingId(null);
    setShowAddForm(false);
    setForm(DEFAULT_FORM);
  };

  const handleSave = async () => {
    setSaving(true);
    const payload: CommunityTemplateInput = {
      name: form.name,
      agent_type: form.agent_type,
      default_size: form.default_size,
      description: form.description,
      personality_profile: { ...form.personality_profile },
    };
    try {
      if (editingId) {
        await apiClient.communityTemplates.update(editingId, payload);
      } else {
        await apiClient.communityTemplates.create(payload);
      }
      cancelForm();
      loadTemplates();
    } catch (e) {
      setError(String(e));
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Delete this template?")) return;
    try {
      await apiClient.communityTemplates.delete(id);
      loadTemplates();
    } catch (e) {
      setError(String(e));
    }
  };

  const updateProfile = (field: PersonalityField, value: number) => {
    setForm((f) => ({
      ...f,
      personality_profile: { ...f.personality_profile, [field]: value },
    }));
  };

  return (
    <div
      data-testid="community-manage-page"
      className="min-h-screen bg-[var(--background)] flex flex-col"
    >
      <PageNav
        breadcrumbs={[
          { label: "Home", href: "/" },
          { label: "Communities", href: "/communities" },
          { label: "Manage Templates" },
        ]}
        actions={
          <button
            onClick={startAdd}
            className="px-3 py-1.5 text-sm font-medium bg-[var(--foreground)] text-[var(--background)] rounded-md hover:opacity-90"
          >
            + Add Template
          </button>
        }
      />

      <div className="flex-1 p-6 flex flex-col gap-6 overflow-auto max-w-4xl mx-auto w-full">
        {error && (
          <div className="bg-[var(--destructive)]/10 border border-[var(--destructive)]/30 rounded-md p-3 text-sm text-[var(--destructive)]">
            {error}
          </div>
        )}

        {/* Add/Edit Form */}
        {(showAddForm || editingId !== null) && (
          <div className="bg-[var(--card)] border border-[var(--border)] rounded-lg p-5 flex flex-col gap-4">
            <h3 className="text-sm font-semibold text-[var(--foreground)]">
              {editingId ? "Edit Template" : "New Template"}
            </h3>

            <div className="grid grid-cols-2 gap-4">
              <div className="flex flex-col gap-1">
                <label className="text-xs text-[var(--muted-foreground)]">Name</label>
                <input
                  className="border border-[var(--border)] rounded-md px-3 py-1.5 text-sm bg-[var(--background)] text-[var(--foreground)]"
                  value={form.name}
                  onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                  placeholder="Template name"
                />
              </div>

              <div className="flex flex-col gap-1">
                <label className="text-xs text-[var(--muted-foreground)]">Agent Type</label>
                <select
                  className="border border-[var(--border)] rounded-md px-3 py-1.5 text-sm bg-[var(--background)] text-[var(--foreground)]"
                  value={form.agent_type}
                  onChange={(e) => setForm((f) => ({ ...f, agent_type: e.target.value }))}
                >
                  {AGENT_TYPES.map((t) => (
                    <option key={t} value={t}>
                      {t}
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex flex-col gap-1">
                <label className="text-xs text-[var(--muted-foreground)]">Default Size</label>
                <input
                  type="number"
                  min={1}
                  className="border border-[var(--border)] rounded-md px-3 py-1.5 text-sm bg-[var(--background)] text-[var(--foreground)]"
                  value={form.default_size}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, default_size: parseInt(e.target.value) || 0 }))
                  }
                />
              </div>

              <div className="flex flex-col gap-1">
                <label className="text-xs text-[var(--muted-foreground)]">Description</label>
                <input
                  className="border border-[var(--border)] rounded-md px-3 py-1.5 text-sm bg-[var(--background)] text-[var(--foreground)]"
                  value={form.description}
                  onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
                  placeholder="Optional description"
                />
              </div>
            </div>

            {/* Personality Sliders */}
            <div>
              <p className="text-xs text-[var(--muted-foreground)] font-medium mb-2">
                Personality Profile
              </p>
              <div className="flex flex-col gap-2">
                {PERSONALITY_FIELDS.map((field) => (
                  <div key={field} className="flex items-center gap-3">
                    <span className="text-xs w-32 capitalize text-[var(--foreground)]">
                      {field.replace("_", " ")}
                    </span>
                    <input
                      type="range"
                      min={0}
                      max={1}
                      step={0.05}
                      value={form.personality_profile[field]}
                      onChange={(e) => updateProfile(field, parseFloat(e.target.value))}
                      className="flex-1"
                    />
                    <span className="text-xs w-8 text-right text-[var(--muted-foreground)]">
                      {form.personality_profile[field].toFixed(2)}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            <div className="flex gap-2 justify-end">
              <button
                onClick={cancelForm}
                className="px-3 py-1.5 text-sm border border-[var(--border)] rounded-md text-[var(--foreground)] hover:bg-[var(--secondary)]"
              >
                Cancel
              </button>
              <button
                onClick={handleSave}
                disabled={saving || !form.name}
                className="px-3 py-1.5 text-sm bg-[var(--foreground)] text-[var(--background)] rounded-md hover:opacity-90 disabled:opacity-50"
              >
                {saving ? "Saving..." : "Save"}
              </button>
            </div>
          </div>
        )}

        {/* Template Cards */}
        {loading ? (
          <div className="text-sm text-[var(--muted-foreground)]">Loading templates...</div>
        ) : templates.length === 0 ? (
          <div className="text-sm text-[var(--muted-foreground)]">
            No templates yet. Click &ldquo;+ Add Template&rdquo; to create one.
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-4">
            {templates.map((t) => (
              <div
                key={t.template_id}
                data-testid={`template-card-${t.template_id}`}
                className="bg-[var(--card)] border border-[var(--border)] rounded-lg p-4 flex flex-col gap-3"
              >
                <div className="flex items-start justify-between">
                  <div>
                    <h4 className="text-sm font-semibold text-[var(--foreground)]">{t.name}</h4>
                    <span className="text-xs text-[var(--muted-foreground)] capitalize">
                      {t.agent_type} · {t.default_size} agents
                    </span>
                  </div>
                  <div className="flex gap-1">
                    <button
                      onClick={() => startEdit(t)}
                      className="px-2 py-1 text-xs border border-[var(--border)] rounded text-[var(--foreground)] hover:bg-[var(--secondary)]"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => handleDelete(t.template_id)}
                      className="px-2 py-1 text-xs border border-[var(--destructive)]/40 rounded text-[var(--destructive)] hover:bg-[var(--destructive)]/10"
                    >
                      Delete
                    </button>
                  </div>
                </div>

                {t.description && (
                  <p className="text-xs text-[var(--muted-foreground)]">{t.description}</p>
                )}

                {/* Personality bars */}
                <div className="flex flex-col gap-1">
                  {PERSONALITY_FIELDS.map((field) => {
                    const val = t.personality_profile[field] ?? 0;
                    return (
                      <div key={field} className="flex items-center gap-2">
                        <span className="text-[10px] w-24 capitalize text-[var(--muted-foreground)]">
                          {field.replace("_", " ")}
                        </span>
                        <div className="flex-1 h-1.5 bg-[var(--secondary)] rounded-full overflow-hidden">
                          <div
                            className="h-full bg-[var(--community-alpha)] rounded-full"
                            style={{ width: `${val * 100}%` }}
                          />
                        </div>
                        <span className="text-[10px] w-6 text-right text-[var(--muted-foreground)]">
                          {val.toFixed(1)}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        )}

        <div className="pt-2">
          <button
            onClick={() => navigate("/communities")}
            className="text-sm text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
          >
            ← Back to Communities
          </button>
        </div>
      </div>
    </div>
  );
}
