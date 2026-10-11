import React, { useState, useEffect, useRef } from 'react';
import { Play, Pause, RotateCcw, FastForward, Filter, Info, Shield, Layers } from 'lucide-react';
import { api } from '../api/client';
import { ExperimentRecord, RunRecord, SimEvent } from '../api/types';

interface WorkspacePageProps {
  liveEvents: SimEvent[];
}

export const WorkspacePage: React.FC<WorkspacePageProps> = ({ liveEvents }) => {
  const [experiments, setExperiments] = useState<ExperimentRecord[]>([]);
  const [selectedExpId, setSelectedExpId] = useState<string>('');
  const [runs, setRuns] = useState<RunRecord[]>([]);
  const [selectedRunId, setSelectedRunId] = useState<string>('');
  const [runEvents, setRunEvents] = useState<SimEvent[]>([]);
  const [mode, setMode] = useState<'replay' | 'live'>('replay');

  // Playback state
  const [playbackIdx, setPlaybackIdx] = useState<number>(0);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [playbackSpeed, setPlaybackSpeed] = useState<number>(1);
  const [selectedEntity, setSelectedEntity] = useState<any | null>(null);
  const [filterType, setFilterType] = useState<string>('ALL');

  useEffect(() => {
    async function fetchExperiments() {
      try {
        const res = await api.listExperiments({ limit: 20 });
        setExperiments(res.experiments);
        if (res.experiments.length > 0) {
          setSelectedExpId(res.experiments[0].id);
        }
      } catch (err) {
        console.error('Failed to load experiments', err);
      }
    }
    fetchExperiments();
  }, []);

  useEffect(() => {
    if (!selectedExpId) return;
    async function fetchRuns() {
      try {
        const res = await api.listRuns(selectedExpId);
        setRuns(res.runs);
        if (res.runs.length > 0) {
          setSelectedRunId(res.runs[0].id);
        }
      } catch (err) {
        console.error('Failed to load runs', err);
      }
    }
    fetchRuns();
  }, [selectedExpId]);

  useEffect(() => {
    if (!selectedRunId) return;
    async function fetchEvents() {
      try {
        const res = await api.getRunEvents(selectedRunId, 0, 1000);
        setRunEvents(res.events);
        setPlaybackIdx(res.events.length > 0 ? res.events.length - 1 : 0);
      } catch (err) {
        console.error('Failed to load events for run', err);
      }
    }
    fetchEvents();
  }, [selectedRunId]);

  // Replay timer
  useEffect(() => {
    if (!isPlaying) return;
    const intervalTime = Math.max(50, 400 / playbackSpeed);
    const timer = setInterval(() => {
      setPlaybackIdx((prev) => {
        if (prev >= runEvents.length - 1) {
          setIsPlaying(false);
          return prev;
        }
        return prev + 1;
      });
    }, intervalTime);
    return () => clearInterval(timer);
  }, [isPlaying, playbackSpeed, runEvents.length]);

  const displayedEvents = mode === 'live' ? liveEvents : runEvents.slice(0, playbackIdx + 1);
  const currentEvent = runEvents[playbackIdx] || null;

  // Derive agent states from events up to playbackIdx
  const agentIds = ['agent_0', 'agent_1', 'agent_2'];
  const agentStates: Record<string, { role: string; round: number; lastAction: string }> = {
    agent_0: { role: 'coordinator', round: 0, lastAction: 'IDLE' },
    agent_1: { role: 'solver', round: 0, lastAction: 'IDLE' },
    agent_2: { role: 'solver', round: 0, lastAction: 'IDLE' },
  };

  displayedEvents.forEach((ev) => {
    if (ev.agent_id && agentStates[ev.agent_id]) {
      agentStates[ev.agent_id].lastAction = ev.type;
      if (ev.payload?.round !== undefined) {
        agentStates[ev.agent_id].round = ev.payload.round;
      }
    }
  });

  // Filtered timeline
  const filteredTimeline = (mode === 'live' ? liveEvents : runEvents).filter(
    (ev) => filterType === 'ALL' || ev.type === filterType
  );

  return (
    <div className="space-y-6">
      {/* Top Controls Bar */}
      <div className="bg-lab-900 border border-lab-800 rounded-xl p-4 flex flex-wrap items-center justify-between gap-4">
        <div className="flex flex-wrap items-center gap-3">
          {/* Mode Switcher */}
          <div className="flex rounded-lg bg-lab-850 p-1 border border-lab-750">
            <button
              onClick={() => { setMode('replay'); setIsPlaying(false); }}
              className={`px-3 py-1 rounded-md text-xs font-semibold ${
                mode === 'replay' ? 'bg-accent-blue text-white shadow' : 'text-lab-400 hover:text-lab-200'
              }`}
            >
              Replay Stored Run
            </button>
            <button
              onClick={() => { setMode('live'); setIsPlaying(false); }}
              className={`px-3 py-1 rounded-md text-xs font-semibold ${
                mode === 'live' ? 'bg-accent-emerald text-white shadow' : 'text-lab-400 hover:text-lab-200'
              }`}
            >
              Live Monitor
            </button>
          </div>

          {/* Select Experiment & Run */}
          {mode === 'replay' && (
            <>
              <select
                value={selectedExpId}
                onChange={(e) => setSelectedExpId(e.target.value)}
                className="bg-lab-850 border border-lab-750 text-lab-200 rounded-lg px-2.5 py-1 text-xs focus:ring-1 focus:ring-accent-blue"
              >
                {experiments.map((exp) => (
                  <option key={exp.id} value={exp.id}>
                    {exp.name} ({exp.agent_type})
                  </option>
                ))}
              </select>

              <select
                value={selectedRunId}
                onChange={(e) => setSelectedRunId(e.target.value)}
                className="bg-lab-850 border border-lab-750 text-lab-200 rounded-lg px-2.5 py-1 text-xs focus:ring-1 focus:ring-accent-blue"
              >
                {runs.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.mode} | Seed {r.seed} | {r.outcome}
                  </option>
                ))}
              </select>
            </>
          )}
        </div>

        {/* Playback Controls (if replay) */}
        {mode === 'replay' && (
          <div className="flex items-center space-x-2">
            <button
              onClick={() => setPlaybackIdx(0)}
              className="p-1.5 rounded bg-lab-850 hover:bg-lab-800 text-lab-300"
              title="Reset"
            >
              <RotateCcw className="w-4 h-4" />
            </button>
            <button
              onClick={() => setIsPlaying(!isPlaying)}
              className="p-1.5 px-3 rounded bg-accent-blue hover:bg-blue-600 text-white font-medium flex items-center space-x-1 text-xs"
            >
              {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
              <span>{isPlaying ? 'Pause' : 'Play'}</span>
            </button>
            <button
              onClick={() => setPlaybackSpeed((s) => (s === 1 ? 2 : s === 2 ? 5 : 1))}
              className="px-2 py-1 rounded bg-lab-850 border border-lab-750 text-lab-300 text-xs font-mono"
            >
              {playbackSpeed}x
            </button>
          </div>
        )}
      </div>

      {/* Main Graph Visualization + Timeline Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* SVG Multi-Agent Topology Canvas */}
        <div className="lg:col-span-2 bg-lab-900 border border-lab-800 rounded-xl p-5 flex flex-col">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center space-x-2">
              <Layers className="w-4 h-4 text-accent-blue" />
              <h2 className="text-sm font-bold text-white uppercase tracking-wider">
                Multi-Agent Communication Topology
              </h2>
            </div>
            <div className="text-[11px] font-mono text-lab-400">
              {mode === 'replay' ? `Event ${playbackIdx + 1} of ${runEvents.length}` : 'Streaming Live'}
            </div>
          </div>

          {/* SVG Canvas */}
          <div className="relative w-full h-[360px] bg-lab-950 border border-lab-850 rounded-lg flex items-center justify-center overflow-hidden">
            <svg viewBox="0 0 600 340" className="w-full h-full">
              {/* Background Network Grid Lines */}
              <defs>
                <pattern id="grid" width="30" height="30" patternUnits="userSpaceOnUse">
                  <path d="M 30 0 L 0 0 0 30" fill="none" stroke="#11192e" strokeWidth="0.8" />
                </pattern>
                <marker id="arrow" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                  <path d="M 0 0 L 10 5 L 0 10 z" fill="#3b82f6" />
                </marker>
              </defs>
              <rect width="100%" height="100%" fill="url(#grid)" />

              {/* Inter-Agent Channel Edges */}
              <line x1="150" y1="230" x2="450" y2="230" stroke="#233254" strokeWidth="2" strokeDasharray="4 4" />
              <line x1="150" y1="230" x2="300" y2="80" stroke="#233254" strokeWidth="2" strokeDasharray="4 4" />
              <line x1="450" y1="230" x2="300" y2="80" stroke="#233254" strokeWidth="2" strokeDasharray="4 4" />

              {/* Agent Nodes */}
              {/* Agent 0 (Top Coordinator) */}
              <g
                className="cursor-pointer"
                onClick={() => setSelectedEntity({ id: 'agent_0', ...agentStates['agent_0'] })}
              >
                <circle cx="300" cy="80" r="32" fill="#0d1322" stroke="#3b82f6" strokeWidth="2.5" />
                <text x="300" y="75" textAnchor="middle" fill="#ffffff" fontSize="12" fontWeight="bold">Agent 0</text>
                <text x="300" y="92" textAnchor="middle" fill="#6d88c2" fontSize="9" fontFamily="monospace">COORDINATOR</text>
              </g>

              {/* Agent 1 (Bottom Left Solver) */}
              <g
                className="cursor-pointer"
                onClick={() => setSelectedEntity({ id: 'agent_1', ...agentStates['agent_1'] })}
              >
                <circle cx="150" cy="230" r="32" fill="#0d1322" stroke="#8b5cf6" strokeWidth="2.5" />
                <text x="150" y="225" textAnchor="middle" fill="#ffffff" fontSize="12" fontWeight="bold">Agent 1</text>
                <text x="150" y="242" textAnchor="middle" fill="#9bb0de" fontSize="9" fontFamily="monospace">SOLVER</text>
              </g>

              {/* Agent 2 (Bottom Right Solver) */}
              <g
                className="cursor-pointer"
                onClick={() => setSelectedEntity({ id: 'agent_2', ...agentStates['agent_2'] })}
              >
                <circle cx="450" cy="230" r="32" fill="#0d1322" stroke="#10b981" strokeWidth="2.5" />
                <text x="450" y="225" textAnchor="middle" fill="#ffffff" fontSize="12" fontWeight="bold">Agent 2</text>
                <text x="450" y="242" textAnchor="middle" fill="#cbd7f1" fontSize="9" fontFamily="monospace">SOLVER</text>
              </g>

              {/* Real Event Packet Indicator (Rendered strictly from real event) */}
              {currentEvent && currentEvent.agent_id && (
                <g>
                  {/* Position packet near sender */}
                  {currentEvent.agent_id === 'agent_0' && (
                    <circle cx="300" cy="120" r="8" fill={currentEvent.type === 'DROP' ? '#f43f5e' : '#3b82f6'} className="animate-ping" />
                  )}
                  {currentEvent.agent_id === 'agent_1' && (
                    <circle cx="190" cy="210" r="8" fill={currentEvent.type === 'DROP' ? '#f43f5e' : '#8b5cf6'} className="animate-ping" />
                  )}
                  {currentEvent.agent_id === 'agent_2' && (
                    <circle cx="410" cy="210" r="8" fill={currentEvent.type === 'DROP' ? '#f43f5e' : '#10b981'} className="animate-ping" />
                  )}
                </g>
              )}
            </svg>

            {/* Current Active Event Banner */}
            {currentEvent && (
              <div className="absolute bottom-3 left-3 right-3 bg-lab-900/95 border border-lab-800 rounded px-3 py-1.5 flex items-center justify-between text-xs font-mono">
                <div className="flex items-center space-x-2">
                  <span className={`px-1.5 py-0.5 rounded text-[10px] ${
                    currentEvent.type === 'DROP' ? 'bg-accent-rose/20 text-accent-rose' :
                    currentEvent.type === 'ACK_RECEIVED' ? 'bg-accent-emerald/20 text-accent-emerald' :
                    'bg-accent-blue/20 text-accent-blue'
                  }`}>
                    {currentEvent.type}
                  </span>
                  <span className="text-lab-300">
                    {currentEvent.agent_id} → {currentEvent.target_agent_id || 'broadcast'}
                  </span>
                </div>
                <span className="text-lab-400">t={currentEvent.sim_time.toFixed(1)} u</span>
              </div>
            )}
          </div>

          {/* Replay Scrubber Slider */}
          {mode === 'replay' && runEvents.length > 0 && (
            <div className="mt-4 space-y-1">
              <input
                type="range"
                min="0"
                max={runEvents.length - 1}
                value={playbackIdx}
                onChange={(e) => {
                  setPlaybackIdx(Number(e.target.value));
                  setIsPlaying(false);
                }}
                className="w-full accent-accent-blue cursor-pointer h-1.5 bg-lab-800 rounded-lg"
              />
              <div className="flex justify-between text-[10px] font-mono text-lab-400">
                <span>Start (t=0.0)</span>
                <span>Scrubber Position: {playbackIdx + 1} / {runEvents.length}</span>
                <span>End</span>
              </div>
            </div>
          )}
        </div>

        {/* Event Timeline & Inspector Drawer */}
        <div className="bg-lab-900 border border-lab-800 rounded-xl p-5 flex flex-col h-[460px]">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-bold text-white uppercase tracking-wider flex items-center space-x-2">
              <Filter className="w-4 h-4 text-accent-blue" />
              <span>Event Log Timeline</span>
            </h2>
            <select
              value={filterType}
              onChange={(e) => setFilterType(e.target.value)}
              className="bg-lab-850 border border-lab-750 text-lab-300 text-[10px] font-mono rounded px-2 py-0.5"
            >
              <option value="ALL">All Types</option>
              <option value="SEND">SEND</option>
              <option value="DELIVER">DELIVER</option>
              <option value="DROP">DROP</option>
              <option value="TIMEOUT">TIMEOUT</option>
              <option value="RETRY">RETRY</option>
              <option value="ACK_RECEIVED">ACK_RECEIVED</option>
              <option value="DUP_SUPPRESSED">DUP_SUPPRESSED</option>
              <option value="STALE_REJECTED">STALE_REJECTED</option>
              <option value="SYNC_APPLIED">SYNC_APPLIED</option>
            </select>
          </div>

          {/* Timeline List */}
          <div className="flex-1 overflow-y-auto space-y-2 pr-1 font-mono text-[11px]">
            {filteredTimeline.length === 0 ? (
              <div className="text-center py-20 text-lab-500">No matching events.</div>
            ) : (
              filteredTimeline.map((ev, i) => (
                <div
                  key={i}
                  onClick={() => setSelectedEntity(ev)}
                  className="p-2 rounded bg-lab-850/50 hover:bg-lab-800/80 border border-lab-800 cursor-pointer transition"
                >
                  <div className="flex items-center justify-between text-[10px] mb-1">
                    <span className="text-accent-blue font-bold">{ev.type}</span>
                    <span className="text-lab-400">t={ev.sim_time.toFixed(1)} u</span>
                  </div>
                  <div className="text-lab-300 text-[10px] truncate">
                    {ev.agent_id ? `${ev.agent_id} → ${ev.target_agent_id || '*'}` : 'SYSTEM'}
                    {ev.msg_id ? ` [${ev.msg_id}]` : ''}
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Selected Entity Details Drawer */}
          {selectedEntity && (
            <div className="mt-3 p-3 bg-lab-950 border border-lab-750 rounded-lg text-xs font-mono">
              <div className="flex items-center justify-between text-lab-400 mb-1">
                <span className="font-bold text-white flex items-center space-x-1">
                  <Info className="w-3.5 h-3.5 text-accent-blue" />
                  <span>Payload Details</span>
                </span>
                <button
                  onClick={() => setSelectedEntity(null)}
                  className="text-lab-500 hover:text-lab-300 text-[10px]"
                >
                  Close
                </button>
              </div>
              <pre className="text-[10px] text-lab-300 overflow-x-auto max-h-24">
                {JSON.stringify(selectedEntity, null, 2)}
              </pre>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
