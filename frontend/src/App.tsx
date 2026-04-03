/**
 * App root with routing.
 * @spec docs/spec/07_FRONTEND_SPEC.md
 * @spec docs/spec/ui/UI_01_SIMULATION_MAIN.md
 */
import { Component, type ReactNode } from 'react';
import { BrowserRouter, Routes, Route, Outlet, Navigate } from "react-router-dom";
import AppSidebar from "./components/shared/AppSidebar";
import SimulationPage from "./pages/SimulationPage";
import CommunitiesDetailPage from "./pages/CommunitiesDetailPage";
import TopInfluencersPage from "./pages/TopInfluencersPage";
import AgentDetailPage from "./pages/AgentDetailPage";
import GlobalMetricsPage from "./pages/GlobalMetricsPage";
import CampaignSetupPage from "./pages/CampaignSetupPage";
import ProjectsListPage from "./pages/ProjectsListPage";
import ProjectScenariosPage from "./pages/ProjectScenariosPage";
import SettingsPage from "./pages/SettingsPage";
import ScenarioOpinionsPage from "./pages/ScenarioOpinionsPage";
import CommunityOpinionPage from "./pages/CommunityOpinionPage";
import ConversationThreadPage from "./pages/ConversationThreadPage";
import ComparisonPage from "./pages/ComparisonPage";
import CommunityManagePage from "./pages/CommunityManagePage";
import LoginPage from "./pages/LoginPage";

class ErrorBoundary extends Component<
  { children: ReactNode; fallback?: ReactNode },
  { hasError: boolean; error: Error | null }
> {
  state = { hasError: false, error: null as Error | null };

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback || (
        <div className="flex items-center justify-center h-screen bg-[var(--secondary)]">
          <div className="text-center p-8">
            <h2 className="text-xl font-semibold text-[var(--foreground)] mb-2">Something went wrong</h2>
            <p className="text-[var(--muted-foreground)] mb-4">{this.state.error?.message}</p>
            <button
              onClick={() => window.location.reload()}
              className="px-4 py-2 bg-[var(--primary)] text-[var(--primary-foreground)] rounded-md"
            >
              Reload
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

/** Layout with sidebar for all pages except SimulationPage */
function SidebarLayout() {
  return (
    <div className="flex h-screen bg-[var(--background)]">
      <AppSidebar />
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  );
}

function App() {
  return (
    <BrowserRouter>
      <ErrorBoundary>
        <Routes>
          {/* Default: redirect to Projects */}
          <Route path="/" element={<Navigate to="/projects" replace />} />

          {/* Simulation workspace — full screen, no sidebar */}
          <Route path="/simulation" element={<SimulationPage />} />

          {/* Login — no sidebar */}
          <Route path="/login" element={<LoginPage />} />

          {/* All other pages get sidebar */}
          <Route element={<SidebarLayout />}>
            <Route path="/projects" element={<ProjectsListPage />} />
            <Route path="/projects/:projectId" element={<ProjectScenariosPage />} />
            <Route path="/projects/:projectId/new-scenario" element={<CampaignSetupPage />} />
            <Route path="/setup" element={<CampaignSetupPage />} />
            <Route path="/communities" element={<CommunitiesDetailPage />} />
            <Route path="/communities/:communityId" element={<CommunitiesDetailPage />} />
            <Route path="/communities/manage" element={<CommunityManagePage />} />
            <Route path="/influencers" element={<TopInfluencersPage />} />
            <Route path="/agents/:agentId" element={<AgentDetailPage />} />
            <Route path="/metrics" element={<GlobalMetricsPage />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="/opinions" element={<ScenarioOpinionsPage />} />
            <Route path="/opinions/:communityId" element={<CommunityOpinionPage />} />
            <Route path="/opinions/:communityId/thread/:threadId" element={<ConversationThreadPage />} />
            <Route path="/compare/:otherId" element={<ComparisonPage />} />
          </Route>
        </Routes>
      </ErrorBoundary>
    </BrowserRouter>
  );
}

export default App;
