/**
 * App root with routing.
 * @spec docs/spec/07_FRONTEND_SPEC.md
 * @spec docs/spec/ui/UI_01_SIMULATION_MAIN.md
 */
import { BrowserRouter, Routes, Route } from "react-router-dom";
import SimulationPage from "./pages/SimulationPage";
import CommunitiesDetailPage from "./pages/CommunitiesDetailPage";
import TopInfluencersPage from "./pages/TopInfluencersPage";
import AgentDetailPage from "./pages/AgentDetailPage";
import GlobalMetricsPage from "./pages/GlobalMetricsPage";
import CampaignSetupPage from "./pages/CampaignSetupPage";
import AnalyticsPage from "./pages/AnalyticsPage";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<SimulationPage />} />
        <Route path="/communities" element={<CommunitiesDetailPage />} />
        <Route path="/influencers" element={<TopInfluencersPage />} />
        <Route path="/agents/:agentId" element={<AgentDetailPage />} />
        <Route path="/metrics" element={<GlobalMetricsPage />} />
        <Route path="/setup" element={<CampaignSetupPage />} />
        <Route path="/campaign/new" element={<CampaignSetupPage />} />
        <Route path="/analytics" element={<AnalyticsPage />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
