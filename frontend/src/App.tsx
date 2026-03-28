/**
 * App root with routing.
 * @spec docs/spec/07_FRONTEND_SPEC.md
 * @spec docs/spec/ui/UI_01_SIMULATION_MAIN.md
 */
import { Component, type ReactNode } from 'react';
import { BrowserRouter, Routes, Route } from "react-router-dom";
import SimulationPage from "./pages/SimulationPage";
import CommunitiesDetailPage from "./pages/CommunitiesDetailPage";
import TopInfluencersPage from "./pages/TopInfluencersPage";
import AgentDetailPage from "./pages/AgentDetailPage";
import GlobalMetricsPage from "./pages/GlobalMetricsPage";
import CampaignSetupPage from "./pages/CampaignSetupPage";
import ProjectsListPage from "./pages/ProjectsListPage";
import ProjectScenariosPage from "./pages/ProjectScenariosPage";

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
        <div className="flex items-center justify-center h-screen bg-gray-50">
          <div className="text-center p-8">
            <h2 className="text-xl font-semibold text-gray-900 mb-2">Something went wrong</h2>
            <p className="text-gray-500 mb-4">{this.state.error?.message}</p>
            <button
              onClick={() => window.location.reload()}
              className="px-4 py-2 bg-gray-900 text-white rounded-md"
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

function App() {
  return (
    <BrowserRouter>
      <ErrorBoundary>
        <Routes>
          <Route path="/projects" element={<ProjectsListPage />} />
          <Route path="/projects/:projectId" element={<ProjectScenariosPage />} />
          <Route path="/" element={<SimulationPage />} />
          <Route path="/communities" element={<CommunitiesDetailPage />} />
          <Route path="/communities/:communityId" element={<CommunitiesDetailPage />} />
          <Route path="/influencers" element={<TopInfluencersPage />} />
          <Route path="/agents/:agentId" element={<AgentDetailPage />} />
          <Route path="/metrics" element={<GlobalMetricsPage />} />
          <Route path="/setup" element={<CampaignSetupPage />} />
          <Route path="/campaign/new" element={<CampaignSetupPage />} />
        </Routes>
      </ErrorBoundary>
    </BrowserRouter>
  );
}

export default App;
