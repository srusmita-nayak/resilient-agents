import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Shield, Play, BarChart2, Activity, AlertTriangle, CheckCircle, Database, Clock } from 'lucide-react';
import { api } from '../api/client';
import { ExperimentRecord, SimEvent, SystemStatus } from '../api/types';

interface OverviewPageProps {
  lastEvent: SimEvent | null;
  eventsFeed: SimEvent[];
}

export const OverviewPage: React.FC<OverviewPageProps> = ({ eventsFeed }) => {
  const [latestExp, setLatestExp] = useState<ExperimentRecord | null>(null);
  const [sysStatus, setSysStatus] = useState<SystemStatus | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const [expRes, statusRes] = await Promise.all([
          api.listExperiments({ limit: 1 }),
          api.getSystemStatus(),
        ]);
        if (expRes.experiments.length > 0) {
          const detail = await api.getExperiment(expRes.experiments[0].id);
          setLatestExp(detail);
        }
        setSysStatus(statusRes);
      } catch (err) {
        console.error('Failed to load overview data', err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  const runs = latestExp?.runs || [];
  const completedRuns = runs.filter((r) => r.status === 'completed');
  const validRuns = runs.filter((r) => r.validation_valid);
  const deadlockRuns = runs.filter((r) => r.termination_reason === 'deadlock' || r.termination_reason === 'stall');
  
  const successRate = runs.length > 0 ? Math.round((validRuns.length / runs.length) * 100) : 0;
  const deadlockRate = runs.length > 0 ? Math.round((deadlockRuns.length / runs.length) * 100) : 0;

  return (
    <div className="space-y-6">
      {/* Hero / Objective Banner */}
      <div className="bg-gradient-to-r from-lab-900 to-lab-850 border border-lab-800 rounded-xl p-6 shadow-lg">
        <div className="max-w-3xl">
          <div className="flex items-center space-x-2 text-accent-blue font-mono text-xs mb-2">
            <Shield className="w-4 h-4" />
            <span>DISTRIBUTED SYSTEMS RESEARCH PLATFORM</span>
          </div>
          <h1 className="text-2xl font-bold text-white mb-2">
            Fault-Tolerant Multi-Agent Coordination Protocol
          </h1>
          <p className="text-sm text-lab-300 leading-relaxed mb-4">
            Investigating distributed constraint reasoning resilience under packet loss, reordering, duplicate delivery,
            and temporary network partitions. Evaluating baseline synchronous barriers versus protected middleware
            featuring monotonic versioning, bounded retry exponential backoff, and state reconciliation.
          </p>
          <div className="flex flex-wrap gap-3">
            <Link
              to="/lab"
              className="inline-flex items-center space-x-2 px-4 py-2 bg-accent-blue hover:bg-blue-600 text-white rounded-lg text-xs font-semibold shadow-md transition"
            >
              <Play className="w-3.5 h-3.5" />
              <span>Launch Experiment Lab</span>
            </Link>
            <Link
              to="/analytics"
              className="inline-flex items-center space-x-2 px-4 py-2 bg-lab-800 hover:bg-lab-750 text-lab-200 border border-lab-700 rounded-lg text-xs font-semibold transition"
            >
              <BarChart2 className="w-3.5 h-3.5" />
              <span>Explore Analytics</span>
            </Link>
          </div>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-lab-900 border border-lab-800 rounded-xl p-4">
          <div className="flex items-center justify-between text-xs text-lab-400 mb-1">
            <span>Valid Solution Rate</span>
            <CheckCircle className="w-4 h-4 text-accent-emerald" />
          </div>
          <div className="text-2xl font-bold font-mono text-white">
            {runs.length > 0 ? `${successRate}%` : '—'}
          </div>
          <div className="text-[11px] text-lab-400 mt-1">
            {runs.length > 0 ? `${validRuns.length} of ${runs.length} runs validated` : 'No runs recorded'}
          </div>
        </div>

        <div className="bg-lab-900 border border-lab-800 rounded-xl p-4">
          <div className="flex items-center justify-between text-xs text-lab-400 mb-1">
            <span>Deadlock / Stall Rate</span>
            <AlertTriangle className="w-4 h-4 text-accent-rose" />
          </div>
          <div className="text-2xl font-bold font-mono text-white">
            {runs.length > 0 ? `${deadlockRate}%` : '—'}
          </div>
          <div className="text-[11px] text-lab-400 mt-1">
            {runs.length > 0 ? `${deadlockRuns.length} runs stalled` : 'No runs recorded'}
          </div>
        </div>

        <div className="bg-lab-900 border border-lab-800 rounded-xl p-4">
          <div className="flex items-center justify-between text-xs text-lab-400 mb-1">
            <span>Latest Experiment</span>
            <Activity className="w-4 h-4 text-accent-blue" />
          </div>
          <div className="text-sm font-semibold text-white truncate">
            {latestExp ? latestExp.name : 'None yet'}
          </div>
          <div className="text-[11px] font-mono text-lab-400 mt-1">
            {latestExp ? `${latestExp.agent_type.toUpperCase()} • ${latestExp.status}` : 'Configure in lab'}
          </div>
        </div>

        <div className="bg-lab-900 border border-lab-800 rounded-xl p-4">
          <div className="flex items-center justify-between text-xs text-lab-400 mb-1">
            <span>Database Storage</span>
            <Database className="w-4 h-4 text-accent-violet" />
          </div>
          <div className="text-2xl font-bold font-mono text-white">
            {sysStatus ? `${sysStatus.database_stats.size_mb} MB` : '—'}
          </div>
          <div className="text-[11px] text-lab-400 mt-1">
            {sysStatus ? `${sysStatus.database_stats.runs_count} runs • ${sysStatus.database_stats.events_count} events` : 'SQLite WAL active'}
          </div>
        </div>
      </div>

      {/* Main Grid: Latest Run Breakdown + Live Activity Stream */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Latest Experiment Breakdown */}
        <div className="lg:col-span-2 bg-lab-900 border border-lab-800 rounded-xl p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-bold text-white uppercase tracking-wider flex items-center space-x-2">
              <Clock className="w-4 h-4 text-accent-blue" />
              <span>Latest Experiment Runs ({latestExp ? latestExp.name : 'None'})</span>
            </h2>
            {latestExp && (
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-lab-800 border border-lab-700 text-lab-300">
                ID: {latestExp.id}
              </span>
            )}
          </div>

          {runs.length === 0 ? (
            <div className="text-center py-12 text-lab-400 text-xs">
              No experiment runs recorded yet. Start your first experiment from the{' '}
              <Link to="/lab" className="text-accent-blue underline">Experiment Lab</Link>.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-lab-800 text-lab-400 font-mono text-[11px]">
                    <th className="pb-2">Mode</th>
                    <th className="pb-2">Seed</th>
                    <th className="pb-2">Status</th>
                    <th className="pb-2">Outcome</th>
                    <th className="pb-2">Sim Time</th>
                    <th className="pb-2">Messages</th>
                    <th className="pb-2">Recoveries</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-lab-850">
                  {runs.slice(0, 8).map((run) => (
                    <tr key={run.id} className="hover:bg-lab-850/40">
                      <td className="py-2.5 font-medium text-lab-200">{run.mode}</td>
                      <td className="py-2.5 font-mono text-lab-400">{run.seed}</td>
                      <td className="py-2.5">
                        <span
                          className={`px-1.5 py-0.5 rounded text-[10px] font-mono ${
                            run.status === 'completed'
                              ? 'bg-accent-emerald/10 text-accent-emerald border border-accent-emerald/20'
                              : run.status === 'running'
                              ? 'bg-accent-blue/10 text-accent-blue border border-accent-blue/20'
                              : 'bg-accent-rose/10 text-accent-rose border border-accent-rose/20'
                          }`}
                        >
                          {run.status}
                        </span>
                      </td>
                      <td className="py-2.5">
                        <span
                          className={`font-semibold ${
                            run.validation_valid ? 'text-accent-emerald' : 'text-accent-amber'
                          }`}
                        >
                          {run.validation_valid ? 'Valid' : run.termination_reason}
                        </span>
                      </td>
                      <td className="py-2.5 font-mono text-lab-300">{run.simulated_time} u</td>
                      <td className="py-2.5 font-mono text-lab-300">
                        {run.metrics_summary?.messages_sent || 0}
                      </td>
                      <td className="py-2.5 font-mono text-lab-300">
                        {run.metrics_summary?.messages_recovered || 0}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Live Activity Feed */}
        <div className="bg-lab-900 border border-lab-800 rounded-xl p-5 flex flex-col h-[400px]">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-bold text-white uppercase tracking-wider flex items-center space-x-2">
              <Activity className="w-4 h-4 text-accent-emerald animate-pulse" />
              <span>Live Event Stream</span>
            </h2>
            <span className="text-[10px] font-mono text-lab-400">Buffered: {eventsFeed.length}</span>
          </div>

          <div className="flex-1 overflow-y-auto space-y-2 font-mono text-[11px] pr-1">
            {eventsFeed.length === 0 ? (
              <div className="text-center py-16 text-lab-500">
                Waiting for simulation events...
              </div>
            ) : (
              eventsFeed.slice(-30).reverse().map((ev, idx) => (
                <div key={idx} className="p-2 rounded bg-lab-850/60 border border-lab-800/80">
                  <div className="flex items-center justify-between text-[10px] text-lab-400 mb-0.5">
                    <span className="text-accent-blue font-bold">{ev.type}</span>
                    <span>t={ev.sim_time.toFixed(1)} u</span>
                  </div>
                  <div className="text-lab-300 truncate">
                    {ev.agent_id ? `${ev.agent_id} → ${ev.target_agent_id || '*'}` : 'SYSTEM'}
                    {ev.msg_id ? ` [${ev.msg_id}]` : ''}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
