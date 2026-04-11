/**
 * CampaignSetupPage — Campaign creation form with simulation parameters.
 * @spec docs/spec/ui/UI_16_CAMPAIGN_SETUP.md
 *
 * Thin orchestrator: all state lives in useCampaignForm; all markup lives
 * in section components under src/components/campaign/. This page just
 * wires them together.
 */
import { useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import PageNav from "../components/shared/PageNav";
import { useCampaignForm } from "../hooks/useCampaignForm";
import ProjectSelector from "../components/campaign/ProjectSelector";
import CampaignInfoSection from "../components/campaign/CampaignInfoSection";
import TargetCommunitiesSection from "../components/campaign/TargetCommunitiesSection";
import CampaignAttributesSection from "../components/campaign/CampaignAttributesSection";
import CommunityConfigurationSection from "../components/campaign/CommunityConfigurationSection";
import AdvancedSettingsSection from "../components/campaign/AdvancedSettingsSection";
import FormProgressBanner from "../components/campaign/FormProgressBanner";
import SimilarityWarningBanner from "../components/campaign/SimilarityWarningBanner";
import { analyzeCommunitySimilarity } from "../components/campaign/communitySimilarity";

export default function CampaignSetupPage() {
  const { projectId: urlProjectId } = useParams<{ projectId: string }>();
  const form = useCampaignForm({ urlProjectId });
  const [quickStart, setQuickStart] = useState(false);

  // Required fields for a minimum-viable submission. The "Quick Start"
  // toggle hides everything that isn't in this list.
  const requiredFields = [
    { label: "Project", satisfied: !!form.selectedProjectId },
    { label: "Campaign name", satisfied: form.name.trim().length > 0 },
    { label: "Message", satisfied: form.message.trim().length > 0 },
    { label: "Channel", satisfied: form.channels.size > 0 },
  ];

  // Round 7-b: pre-flight similarity advisor — warn the user when their
  // community personality_profiles are too similar to produce meaningful
  // diffusion differentiation. Recomputed only when the communities array
  // changes; the calculation is microsecond-cheap.
  const similarityReport = useMemo(
    () => analyzeCommunitySimilarity(form.communities),
    [form.communities],
  );

  return (
    <div data-testid="campaign-setup-page" className="min-h-screen bg-[var(--background)] flex flex-col">
      <PageNav
        breadcrumbs={[
          { label: "Projects", href: "/projects" },
          ...(urlProjectId ? [{ label: "Project", href: `/projects/${urlProjectId}` }] : []),
          { label: "Campaign Setup" },
        ]}
      />

      <div className="flex-1 p-6 flex justify-center overflow-auto">
        <form onSubmit={form.handleSubmit} className="w-full max-w-2xl flex flex-col gap-6">
          <h1 className="text-xl font-bold font-display text-[var(--foreground)]">
            Create New Simulation
          </h1>

          <FormProgressBanner
            fields={requiredFields}
            quickStart={quickStart}
            onToggleQuickStart={() => setQuickStart((v) => !v)}
          />

          <ProjectSelector
            projects={form.projects}
            selectedProjectId={form.selectedProjectId}
            onSelectProject={form.setSelectedProjectId}
            urlProjectId={urlProjectId}
          />

          <CampaignInfoSection
            name={form.name}
            onNameChange={form.setName}
            budget={form.budget}
            onBudgetChange={form.setBudget}
            channels={form.channels}
            onToggleChannel={form.toggleChannel}
            message={form.message}
            onMessageChange={form.setMessage}
          />

          <TargetCommunitiesSection
            options={form.communityOptions}
            selected={form.targetCommunities}
            onToggle={form.toggleCommunity}
          />

          {!quickStart && (
            <>
              <CampaignAttributesSection
                controversy={form.controversy}
                onControversyChange={form.setControversy}
                novelty={form.novelty}
                onNoveltyChange={form.setNovelty}
                utility={form.utility}
                onUtilityChange={form.setUtility}
              />

              <CommunityConfigurationSection
                communities={form.communities}
                open={form.communityOpen}
                onToggleOpen={form.setCommunityOpen}
                onLoadTemplates={form.loadTemplates}
                onUpdateCommunity={form.updateCommunity}
                onUpdatePersonality={form.updatePersonality}
                onRemoveCommunity={form.removeCommunity}
                onAddCommunity={form.addCommunity}
              />

              <SimilarityWarningBanner report={similarityReport} />

              <AdvancedSettingsSection
                maxSteps={form.maxSteps}
                onMaxStepsChange={form.setMaxSteps}
                randomSeed={form.randomSeed}
                onRandomSeedChange={form.setRandomSeed}
                llmProvider={form.llmProvider}
                onLlmProviderChange={form.setLlmProvider}
                slmLlmRatio={form.slmLlmRatio}
                onSlmLlmRatioChange={form.setSlmLlmRatio}
              />
            </>
          )}

          {form.error && (
            <div className="rounded-md bg-[var(--destructive)]/10 border border-[var(--destructive)]/30 p-3 text-sm text-[var(--destructive)]">
              {form.error}
            </div>
          )}

          <button
            type="submit"
            disabled={form.submitting || !form.name || !form.selectedProjectId}
            className="h-11 px-6 text-sm font-medium text-[var(--primary-foreground)] bg-[var(--primary)] rounded-md hover:bg-[var(--primary)]/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {form.submitting ? "Creating..." : "Create Simulation"}
          </button>
        </form>
      </div>
    </div>
  );
}
