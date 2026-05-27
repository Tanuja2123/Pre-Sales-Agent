import { Navigate, Route, Routes } from "react-router-dom";
import { AuthLayout } from "./AuthLayout";
import { AuthSessionGuard } from "./AuthSessionGuard";
import { AppLayout } from "./AppLayout";
import { ProtectedRoute, PublicOnlyRoute } from "./ProtectedRoute";
import { AgentWorkspacePage } from "../pages/AgentWorkspacePage";
import { AgentsHubPage } from "../pages/AgentsHubPage";
import { AnalysisPage } from "../pages/AnalysisPage";
import { DashboardPage } from "../pages/DashboardPage";
import { HistoryPage } from "../pages/HistoryPage";
import { LoginPage } from "../pages/LoginPage";
import { RegisterPage } from "../pages/RegisterPage";
import { ResultsPage } from "../pages/ResultsPage";
import { UploadPage } from "../pages/UploadPage";

export function App() {
  return (
    <AuthSessionGuard>
      <Routes>
        <Route path="/" element={<Navigate to="/login" replace />} />

        <Route element={<PublicOnlyRoute />}>
          <Route element={<AuthLayout />}>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
          </Route>
        </Route>

        <Route element={<ProtectedRoute />}>
          <Route element={<AppLayout />}>
            <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/intake" element={<UploadPage />} />
          <Route path="/agents" element={<AgentsHubPage />} />
          <Route path="/agents/:agentId" element={<AgentWorkspacePage />} />
          <Route path="/run/:runId/agents" element={<AgentsHubPage />} />
          <Route path="/run/:runId/agents/:agentId" element={<AgentWorkspacePage />} />
          <Route path="/analysis/:runId" element={<AnalysisPage />} />
          <Route path="/results/:runId" element={<ResultsPage />} />
          <Route path="/history" element={<HistoryPage />} />
          <Route path="/upload" element={<Navigate to="/intake" replace />} />
        </Route>
      </Route>

      <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </AuthSessionGuard>
  );
}
