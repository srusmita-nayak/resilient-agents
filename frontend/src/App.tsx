import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Header } from './components/Header';
import { OverviewPage } from './pages/OverviewPage';
import { WorkspacePage } from './pages/WorkspacePage';
import { ExperimentLabPage } from './pages/ExperimentLabPage';
import { InspectorPage } from './pages/InspectorPage';
import { AnalyticsPage } from './pages/AnalyticsPage';
import { HistoryPage } from './pages/HistoryPage';
import { ArchitecturePage } from './pages/ArchitecturePage';
import { api } from './api/client';
import { useWebSocket } from './hooks/useWebSocket';
import { HealthStatus, SimEvent } from './api/types';

export const App: React.FC = () => {
  const [health, setHealth] = useState<HealthStatus | null>(null);

  // Real-time WebSocket hook
  const { isConnected, lastEvent, events } = useWebSocket();

  // Health poll on load and every 10 seconds
  useEffect(() => {
    async function checkHealth() {
      try {
        const res = await api.getHealth();
        setHealth(res);
      } catch (err) {
        setHealth(null);
      }
    }
    checkHealth();
    const interval = setInterval(checkHealth, 10000);
    return () => clearInterval(interval);
  }, []);

  return (
    <BrowserRouter>
      <div className="min-h-screen bg-lab-950 text-lab-100 flex flex-col font-sans">
        <Header health={health} wsConnected={isConnected} />
        <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <Routes>
            <Route path="/" element={<OverviewPage lastEvent={lastEvent} eventsFeed={events} />} />
            <Route path="/workspace" element={<WorkspacePage liveEvents={events} />} />
            <Route path="/lab" element={<ExperimentLabPage />} />
            <Route path="/inspector" element={<InspectorPage />} />
            <Route path="/analytics" element={<AnalyticsPage />} />
            <Route path="/history" element={<HistoryPage />} />
            <Route path="/architecture" element={<ArchitecturePage />} />
          </Routes>
        </main>
        <footer className="border-t border-lab-900 bg-lab-950 py-4 text-center text-xs text-lab-500 font-mono">
          Resilient Agents Research Platform • Distributed Multi-Agent Coordination under Software-Emulated Network Faults
        </footer>
      </div>
    </BrowserRouter>
  );
};

export default App;
