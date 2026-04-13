/**
 * App root with routing.
 * @spec docs/spec/07_FRONTEND_SPEC.md
 * @spec docs/spec/ui/UI_01_SIMULATION_MAIN.md
 */
import { Component, type ReactNode, lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route, Outlet, Navigate } from "react-router-dom";
import AppSidebar from "./components/shared/AppSidebar";
import { LoadingSpinner } from "./components/shared/LoadingSpinner";

// Eager: most-used entry points loaded immediately
import LoginPage from "./pages/LoginPage";
import ProjectsListPage from "./pages/ProjectsListPage";
import ProjectScenariosPage from "./pages/ProjectScenariosPage";

// Lazy: all other pages code-split into separate chunks
// FE-PERF-08: SimulationPage lazy-loaded to keep Cytoscape (~400KB) out of initial bundle
const SimulationPage = lazy(() => import("./pages/SimulationPage"));
const SimulationListPage = lazy(() => import("./pages/SimulationListPage"));
const AnalyticsPage = lazy(() => import("./pages/AnalyticsPage"));
const ComparisonPage = lazy(() => import("./pages/ComparisonPage"));
const GlobalMetricsPage = lazy(() => import("./pages/GlobalMetricsPage"));
const AgentDetailPage = lazy(() => import("./pages/AgentDetailPage"));
const CommunitiesDetailPage = lazy(() => import("./pages/CommunitiesDetailPage"));
const CommunityManagePage = lazy(() => import("./pages/CommunityManagePage"));
const TopInfluencersPage = lazy(() => import("./pages/TopInfluencersPage"));
const ScenarioOpinionsPage = lazy(() => import("./pages/ScenarioOpinionsPage"));
const CommunityOpinionPage = lazy(() => import("./pages/CommunityOpinionPage"));
const ConversationThreadPage = lazy(() => import("./pages/ConversationThreadPage"));
const CampaignSetupPage = lazy(() => import("./pages/CampaignSetupPage"));
const SettingsPage = lazy(() => import("./pages/SettingsPage"));

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

/** Layout with sidebar. Most pages mount with the sidebar expanded;
 *  pass ``defaultCollapsed`` for pages that need more horizontal
 *  room (the 3D simulation workspace starts with a 60px icon rail). */
function SidebarLayout({ defaultCollapsed = false }: { defaultCollapsed?: boolean }) {
  return (
    <div className="flex h-screen bg-[var(--background)]">
      <AppSidebar defaultCollapsed={defaultCollapsed} />
      <main className="flex-1 overflow-auto min-w-0">
        <Outlet />
      </main>
    </div>
  );
}

const PAGE_FALLBACK = (
  <div className="flex items-center justify-center h-screen">
    <LoadingSpinner label="Loading..." />
  </div>
);

function App() {
  return (
    <BrowserRouter>
      <ErrorBoundary>
        <Suspense fallback={PAGE_FALLBACK}>
          <Routes>
            {/* Default: redirect to Projects */}
            <Route path="/" element={<Navigate to="/projects" replace />} />

            {/* Simulation detail workspace — sidebar mounted collapsed
                (60px icon rail) so the 3D graph keeps its horizontal
                room; users click the hamburger to slide the full menu
                open when they need to navigate away. */}
            <Route element={<SidebarLayout defaultCollapsed />}>
              <Route path="/simulation/:simulationId" element={<SimulationPage />} />
              {/* Legacy alias (plural) — keep for any external bookmarks */}
              <Route path="/simulations/:simulationId" element={<SimulationPage />} />
            </Route>

            {/* Login — no sidebar */}
            <Route path="/login" element={<LoginPage />} />

            {/* All other pages get sidebar */}
            <Route element={<SidebarLayout />}>
              {/* Simulation list — landing page for the Simulation menu. */}
              <Route path="/simulation" element={<SimulationListPage />} />
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
              {/* SPEC 24 §2.3 — DecidePanel navigates with both sim IDs in
                  the URL so the comparison link is shareable and survives a
                  page refresh. The legacy `/compare/:otherId` route is kept
                  so existing bookmarks still resolve (ComparisonPage falls
                  back to the active simulation from the Zustand store when
                  simulationId is absent from the URL). */}
              <Route
                path="/simulation/:simulationId/compare/:otherId"
                element={<ComparisonPage />}
              />
              <Route path="/compare/:otherId" element={<ComparisonPage />} />
              <Route path="/analytics" element={<AnalyticsPage />} />
            </Route>
          </Routes>
        </Suspense>
      </ErrorBoundary>
    </BrowserRouter>
  );
}

export default App;
