import React, { useState, useEffect } from 'react';
import { Play, XCircle, Sliders, Shield, AlertCircle, CheckCircle2, RefreshCw } from 'lucide-react';
import { api } from '../api/client';
import { ExperimentRecord, RunRecord } from '../api/types';

export const ExperimentLabPage: React.FC = () => {
  // Presets & System state
  const [presets, setPresets] = useState<any>(null);
  const [activeExp, setActiveExp] = useState<ExperimentRecord | null>(null);
  const [activeRuns, setActiveRuns] = useState<RunRecord[]>([]);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [cancelModal, setCancelModal] = useState<boolean>(false);
  const [notification, setNotification] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  // Form State
  const [expName, setExpName] = useState('Resilience Evaluation Sweep');
  const [agentType, setAgentType] = useState<'deterministic' | 'llm'>('deterministic');
  const [llmModel, setLlmModel] = useState('gemini-2.5-flash');
  const [llmCallBudget, setLlmCallBudget] = useState(50);
  const [geminiKeyInput, setGeminiKeyInput] = useState('');

  // Problem config
  const [difficultyPreset, setDifficultyPreset] = useState<'easy' | 'medium' | 'hard'>('easy');
  const [numAgents, setNumAgents] = useState(3);
  const [numNodes, setNumNodes] = useState(12);
  const [numColors, setNumColors] = useState(3);
  const [roundBudget, setRoundBudget] = useState(25);

  // Fault config
  const [faultPreset, setFaultPreset] = useState<string>('lossy_medium');
  const [lossRate, setLossRate] = useState(0.25);
  const [minLatency, setMinLatency] = useState(1.0);
  const [maxLatency, setMaxLatency] = useState(2.5);
  const [jitter, setJitter] = useState(0.5);
  const [duplicateRate, setDuplicateRate] = useState(0.0);
  const [reorderRate, setReorderRate] = useState(0.0);
  const [enablePartition, setEnablePartition] = useState(false);

  // Middleware parameters
  const [ackTimeout, setAckTimeout] = useState(3.0);
  const [maxRetries, setMaxRetries] = useState(3);
  const [backoffFactor, setBackoffFactor] = useState(1.5);
  const [barrierTimeout, setBarrierTimeout] = useState(8.0);
  const [roundBarrierTimeout, setRoundBarrierTimeout] = useState(12.0);

  // Ablations
  const [enableRetransmission, setEnableRetransmission] = useState(true);
  const [enableVersionFilter, setEnableVersionFilter] = useState(true);
  const [enableSync, setEnableSync] = useState(true);

  // Modes & Seeds
  const [selectedModes, setSelectedModes] = useState<string[]>(['baseline', 'timeout_baseline', 'protected']);
  const [seedListStr, setSeedListStr] = useState('42, 43, 44');
  const [includeFaultFreeRef, setIncludeFaultFreeRef] = useState(true);

  // Load Presets
  useEffect(() => {
    async function loadPresets() {
      try {
        const res = await api.getPresets();
        setPresets(res);
      } catch (err) {
        console.error('Failed to load presets', err);
      }
    }
    loadPresets();
  }, []);

  // Poll active experiment status if running
  useEffect(() => {
    let timer: any;
    async function checkActive() {
      try {
        const status = await api.getSystemStatus();
        if (status.active_experiment_id) {
          const exp = await api.getExperiment(status.active_experiment_id);
          setActiveExp(exp);
          setActiveRuns(exp.runs || []);
        } else if (activeExp && activeExp.status === 'running') {
          // Finished
          const exp = await api.getExperiment(activeExp.id);
          setActiveExp(exp);
          setActiveRuns(exp.runs || []);
        }
      } catch (err) {
        // ignore
      }
    }
    checkActive();
    timer = setInterval(checkActive, 2000);
    return () => clearInterval(timer);
  }, [activeExp]);

  // Apply Difficulty Preset
  const handleSelectDifficulty = (presetKey: 'easy' | 'medium' | 'hard') => {
    setDifficultyPreset(presetKey);
    if (presets?.difficulty_presets?.[presetKey]) {
      const p = presets.difficulty_presets[presetKey];
      setNumAgents(p.num_agents);
      setNumNodes(p.num_nodes);
      setNumColors(p.num_colors);
      setRoundBudget(p.round_budget);
    }
  };

  // Apply Fault Preset
  const handleSelectFault = (presetKey: string) => {
    setFaultPreset(presetKey);
    if (presets?.fault_presets?.[presetKey]) {
      const f = presets.fault_presets[presetKey];
      setLossRate(f.loss_rate);
      setMinLatency(f.min_latency);
      setMaxLatency(f.max_latency);
      setJitter(f.jitter);
      setDuplicateRate(f.duplicate_rate);
      setReorderRate(f.reorder_rate);
      setEnablePartition(f.partitions && f.partitions.length > 0);
    }
  };

  // Mode Toggle
  const toggleMode = (m: string) => {
    if (selectedModes.includes(m)) {
      if (selectedModes.length > 1) setSelectedModes(selectedModes.filter((x) => x !== m));
    } else {
      setSelectedModes([...selectedModes, m]);
    }
  };

  // Submit Experiment
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setNotification(null);

    try {
      const seeds = seedListStr
        .split(',')
        .map((s) => parseInt(s.trim(), 10))
        .filter((n) => !isNaN(n));

      if (seeds.length === 0) {
        throw new Error('Please enter at least one integer seed');
      }

      const partitions = enablePartition
        ? [{ start_time: 10.0, duration: 15.0, isolated_agents: null }]
        : [];

      const payload = {
        name: expName,
        problem: {
          problem_type: 'graph_coloring',
          num_agents: numAgents,
          num_nodes: numNodes,
          num_colors: numColors,
          round_budget: roundBudget,
        },
        faults: {
          loss_rate: lossRate,
          min_latency: minLatency,
          max_latency: maxLatency,
          jitter: jitter,
          duplicate_rate: duplicateRate,
          reorder_rate: reorderRate,
          partitions: partitions,
        },
        middleware: {
          ack_timeout: ackTimeout,
          max_retries: maxRetries,
          backoff_factor: backoffFactor,
          barrier_timeout: barrierTimeout,
          round_barrier_timeout: roundBarrierTimeout,
          enable_retransmission: enableRetransmission,
          enable_version_filter: enableVersionFilter,
          enable_sync_recoordination: enableSync,
        },
        modes: selectedModes,
        seeds: seeds,
        include_fault_free_reference: includeFaultFreeRef,
        agent_type: agentType,
        provider_model: agentType === 'llm' ? llmModel : null,
        llm_call_budget: llmCallBudget,
        gemini_api_key: agentType === 'llm' && geminiKeyInput ? geminiKeyInput : null,
      };

      const res = await api.createExperiment(payload);
      setNotification({ type: 'success', message: `Experiment ${res.experiment_id} submitted!` });
      const exp = await api.getExperiment(res.experiment_id);
      setActiveExp(exp);
    } catch (err: any) {
      setNotification({ type: 'error', message: err.message || 'Failed to submit experiment' });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCancel = async () => {
    if (!activeExp) return;
    try {
      await api.cancelExperiment(activeExp.id);
      setCancelModal(false);
      setNotification({ type: 'success', message: 'Cancellation signal sent.' });
    } catch (err: any) {
      setNotification({ type: 'error', message: err.message });
    }
  };

  const progressPercent = activeExp && activeExp.total_runs > 0
    ? Math.round((activeExp.completed_runs / activeExp.total_runs) * 100)
    : 0;

  return (
    <div className="space-y-6">
      {/* Banner Displaying Research Mode */}
      <div className={`p-4 rounded-xl border flex items-center justify-between ${
        agentType === 'deterministic'
          ? 'bg-lab-900 border-accent-blue/30 text-white'
          : 'bg-lab-900 border-accent-violet/30 text-white'
      }`}>
        <div className="flex items-center space-x-3">
          <Shield className={`w-5 h-5 ${agentType === 'deterministic' ? 'text-accent-blue' : 'text-accent-violet'}`} />
          <div>
            <div className="text-xs uppercase tracking-wider font-mono font-bold">
              {agentType === 'deterministic' ? 'DETERMINISTIC AGENTS MODE' : `LLM AGENTS MODE (${llmModel})`}
            </div>
            <div className="text-[11px] text-lab-300">
              {agentType === 'deterministic'
                ? 'Min-conflict heuristic with seeded RNG. Guaranteed fair comparative baseline across identical graph instances.'
                : 'Structured JSON proposal policy via Gemini with strict budget cap and deterministic min-conflict fallback.'}
            </div>
          </div>
        </div>
        <div className="flex rounded bg-lab-850 p-1 border border-lab-750 text-xs">
          <button
            type="button"
            onClick={() => setAgentType('deterministic')}
            className={`px-3 py-1 rounded font-medium ${
              agentType === 'deterministic' ? 'bg-accent-blue text-white shadow' : 'text-lab-400'
            }`}
          >
            Deterministic
          </button>
          <button
            type="button"
            onClick={() => setAgentType('llm')}
            className={`px-3 py-1 rounded font-medium ${
              agentType === 'llm' ? 'bg-accent-violet text-white shadow' : 'text-lab-400'
            }`}
          >
            LLM Agent
          </button>
        </div>
      </div>

      {notification && (
        <div className={`p-3 rounded-lg border text-xs flex items-center space-x-2 ${
          notification.type === 'success'
            ? 'bg-accent-emerald/10 border-accent-emerald/30 text-accent-emerald'
            : 'bg-accent-rose/10 border-accent-rose/30 text-accent-rose'
        }`}>
          {notification.type === 'success' ? <CheckCircle2 className="w-4 h-4" /> : <AlertCircle className="w-4 h-4" />}
          <span>{notification.message}</span>
        </div>
      )}

      {/* Main Grid: Form Left, Active Execution Right */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Configuration Form */}
        <form onSubmit={handleSubmit} className="lg:col-span-2 space-y-5">
          {/* Section 1: Experiment Title & Presets */}
          <div className="bg-lab-900 border border-lab-800 rounded-xl p-5 space-y-4">
            <h2 className="text-xs font-bold uppercase tracking-wider text-lab-200 flex items-center space-x-2">
              <Sliders className="w-4 h-4 text-accent-blue" />
              <span>1. Task & Graph Benchmark Configuration</span>
            </h2>

            <div>
              <label className="block text-[11px] text-lab-400 mb-1">Experiment Name</label>
              <input
                type="text"
                value={expName}
                onChange={(e) => setExpName(e.target.value)}
                required
                className="w-full bg-lab-850 border border-lab-750 text-white rounded-lg px-3 py-2 text-xs focus:ring-1 focus:ring-accent-blue"
              />
            </div>

            {/* Difficulty Presets */}
            <div>
              <label className="block text-[11px] text-lab-400 mb-1.5">Problem Difficulty Preset</label>
              <div className="grid grid-cols-3 gap-2">
                {(['easy', 'medium', 'hard'] as const).map((preset) => (
                  <button
                    key={preset}
                    type="button"
                    onClick={() => handleSelectDifficulty(preset)}
                    className={`py-2 px-3 rounded-lg text-xs font-medium border text-center transition ${
                      difficultyPreset === preset
                        ? 'bg-accent-blue/15 border-accent-blue text-white'
                        : 'bg-lab-850 border-lab-750 text-lab-400 hover:text-white'
                    }`}
                  >
                    <div className="capitalize font-bold">{preset}</div>
                    <div className="text-[10px] text-lab-400 mt-0.5">
                      {preset === 'easy' ? '3 Ag / 12 Nodes' : preset === 'medium' ? '4 Ag / 20 Nodes' : '5 Ag / 35 Nodes'}
                    </div>
                  </button>
                ))}
              </div>
            </div>

            {/* Custom Problem Inputs */}
            <div className="grid grid-cols-4 gap-3 pt-2">
              <div>
                <label className="block text-[10px] text-lab-400">Agents</label>
                <input
                  type="number"
                  min="3"
                  max="10"
                  value={numAgents}
                  onChange={(e) => setNumAgents(Number(e.target.value))}
                  className="w-full bg-lab-850 border border-lab-750 text-white rounded p-1.5 text-xs font-mono"
                />
              </div>
              <div>
                <label className="block text-[10px] text-lab-400">Nodes</label>
                <input
                  type="number"
                  min="3"
                  max="100"
                  value={numNodes}
                  onChange={(e) => setNumNodes(Number(e.target.value))}
                  className="w-full bg-lab-850 border border-lab-750 text-white rounded p-1.5 text-xs font-mono"
                />
              </div>
              <div>
                <label className="block text-[10px] text-lab-400">Colors</label>
                <input
                  type="number"
                  min="2"
                  max="8"
                  value={numColors}
                  onChange={(e) => setNumColors(Number(e.target.value))}
                  className="w-full bg-lab-850 border border-lab-750 text-white rounded p-1.5 text-xs font-mono"
                />
              </div>
              <div>
                <label className="block text-[10px] text-lab-400">Round Budget</label>
                <input
                  type="number"
                  min="5"
                  max="100"
                  value={roundBudget}
                  onChange={(e) => setRoundBudget(Number(e.target.value))}
                  className="w-full bg-lab-850 border border-lab-750 text-white rounded p-1.5 text-xs font-mono"
                />
              </div>
            </div>
          </div>

          {/* Section 2: Fault Injection Model */}
          <div className="bg-lab-900 border border-lab-800 rounded-xl p-5 space-y-4">
            <h2 className="text-xs font-bold uppercase tracking-wider text-lab-200 flex items-center space-x-2">
              <Sliders className="w-4 h-4 text-accent-blue" />
              <span>2. Network Fault Injection Model</span>
            </h2>

            {/* Fault Presets */}
            <div>
              <label className="block text-[11px] text-lab-400 mb-1.5">Network Condition Presets</label>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                {[
                  { key: 'reliable', label: 'Reliable (0% Loss)' },
                  { key: 'lossy_low', label: 'Lossy 10%' },
                  { key: 'lossy_medium', label: 'Lossy 25%' },
                  { key: 'lossy_severe', label: 'Lossy 50%' },
                  { key: 'partition_burst', label: 'Partition Burst' },
                ].map((item) => (
                  <button
                    key={item.key}
                    type="button"
                    onClick={() => handleSelectFault(item.key)}
                    className={`p-2 rounded-lg text-xs font-medium border text-center transition ${
                      faultPreset === item.key
                        ? 'bg-accent-blue/15 border-accent-blue text-white'
                        : 'bg-lab-850 border-lab-750 text-lab-400 hover:text-white'
                    }`}
                  >
                    {item.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Sliders */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-2">
              <div>
                <div className="flex justify-between text-[11px] mb-1">
                  <span className="text-lab-400">Packet Loss Rate</span>
                  <span className="font-mono text-white">{(lossRate * 100).toFixed(0)}%</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="0.8"
                  step="0.05"
                  value={lossRate}
                  onChange={(e) => setLossRate(Number(e.target.value))}
                  className="w-full accent-accent-blue"
                />
              </div>

              <div>
                <div className="flex justify-between text-[11px] mb-1">
                  <span className="text-lab-400">Latency / Jitter</span>
                  <span className="font-mono text-white">{minLatency} - {maxLatency} u</span>
                </div>
                <input
                  type="range"
                  min="0.5"
                  max="10.0"
                  step="0.5"
                  value={maxLatency}
                  onChange={(e) => setMaxLatency(Number(e.target.value))}
                  className="w-full accent-accent-blue"
                />
              </div>

              <div>
                <div className="flex justify-between text-[11px] mb-1">
                  <span className="text-lab-400">Duplicates & Reordering</span>
                  <span className="font-mono text-white">{(duplicateRate * 100).toFixed(0)}%</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="0.4"
                  step="0.05"
                  value={duplicateRate}
                  onChange={(e) => {
                    setDuplicateRate(Number(e.target.value));
                    setReorderRate(Number(e.target.value));
                  }}
                  className="w-full accent-accent-blue"
                />
              </div>
            </div>

            <div className="flex items-center space-x-2 pt-2">
              <input
                type="checkbox"
                id="partitionToggle"
                checked={enablePartition}
                onChange={(e) => setEnablePartition(e.target.checked)}
                className="rounded bg-lab-850 border-lab-750 text-accent-blue"
              />
              <label htmlFor="partitionToggle" className="text-xs text-lab-300">
                Inject temporary network partition window (t=10 to t=25)
              </label>
            </div>
          </div>

          {/* Section 3: Protocol Parameters & Ablations */}
          <div className="bg-lab-900 border border-lab-800 rounded-xl p-5 space-y-4">
            <h2 className="text-xs font-bold uppercase tracking-wider text-lab-200 flex items-center space-x-2">
              <Sliders className="w-4 h-4 text-accent-blue" />
              <span>3. Middleware & Ablation Controls</span>
            </h2>

            <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 text-xs">
              <div>
                <label className="block text-lab-400 text-[10px] mb-1">ACK Timeout (u)</label>
                <input
                  type="number"
                  step="0.5"
                  value={ackTimeout}
                  onChange={(e) => setAckTimeout(Number(e.target.value))}
                  className="w-full bg-lab-850 border border-lab-750 text-white rounded p-1.5 font-mono"
                />
              </div>
              <div>
                <label className="block text-lab-400 text-[10px] mb-1">Max Retries</label>
                <input
                  type="number"
                  min="1"
                  max="8"
                  value={maxRetries}
                  onChange={(e) => setMaxRetries(Number(e.target.value))}
                  className="w-full bg-lab-850 border border-lab-750 text-white rounded p-1.5 font-mono"
                />
              </div>
              <div>
                <label className="block text-lab-400 text-[10px] mb-1">Round Barrier Timeout</label>
                <input
                  type="number"
                  step="1.0"
                  value={roundBarrierTimeout}
                  onChange={(e) => setRoundBarrierTimeout(Number(e.target.value))}
                  className="w-full bg-lab-850 border border-lab-750 text-white rounded p-1.5 font-mono"
                />
              </div>
            </div>

            {/* Ablation Toggles */}
            <div className="pt-2 border-t border-lab-850 space-y-2">
              <div className="text-[11px] font-bold text-lab-300">Ablation Studies (Feature Toggles)</div>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                <label className="flex items-center space-x-2 text-xs text-lab-400">
                  <input
                    type="checkbox"
                    checked={enableRetransmission}
                    onChange={(e) => setEnableRetransmission(e.target.checked)}
                    className="rounded bg-lab-850 border-lab-750 text-accent-blue"
                  />
                  <span>Retransmissions</span>
                </label>
                <label className="flex items-center space-x-2 text-xs text-lab-400">
                  <input
                    type="checkbox"
                    checked={enableVersionFilter}
                    onChange={(e) => setEnableVersionFilter(e.target.checked)}
                    className="rounded bg-lab-850 border-lab-750 text-accent-blue"
                  />
                  <span>Version Filter</span>
                </label>
                <label className="flex items-center space-x-2 text-xs text-lab-400">
                  <input
                    type="checkbox"
                    checked={enableSync}
                    onChange={(e) => setEnableSync(e.target.checked)}
                    className="rounded bg-lab-850 border-lab-750 text-accent-blue"
                  />
                  <span>Snapshot Sync</span>
                </label>
              </div>
            </div>
          </div>

          {/* Section 4: Modes, Seeds & Launch */}
          <div className="bg-lab-900 border border-lab-800 rounded-xl p-5 space-y-4">
            <h2 className="text-xs font-bold uppercase tracking-wider text-lab-200">
              4. Execution Modes & Pseudo-Random Seeds
            </h2>

            {/* Mode Checkboxes */}
            <div className="flex flex-wrap gap-4 text-xs">
              {[
                { id: 'baseline', label: 'Mode A: Synchronous Baseline' },
                { id: 'timeout_baseline', label: 'Mode B: Timeout Baseline' },
                { id: 'protected', label: 'Mode C: Protected Middleware' },
              ].map((m) => (
                <label key={m.id} className="flex items-center space-x-2 text-lab-300 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={selectedModes.includes(m.id)}
                    onChange={() => toggleMode(m.id)}
                    className="rounded bg-lab-850 border-lab-750 text-accent-blue"
                  />
                  <span className="font-medium">{m.label}</span>
                </label>
              ))}
            </div>

            {/* Seed List & Reference run */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
              <div>
                <label className="block text-[11px] text-lab-400 mb-1">Random Seeds (Comma-separated)</label>
                <input
                  type="text"
                  value={seedListStr}
                  onChange={(e) => setSeedListStr(e.target.value)}
                  className="w-full bg-lab-850 border border-lab-750 text-white rounded p-2 text-xs font-mono"
                />
              </div>
              <div className="flex items-center pt-5">
                <label className="flex items-center space-x-2 text-xs text-lab-300 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={includeFaultFreeRef}
                    onChange={(e) => setIncludeFaultFreeRef(e.target.checked)}
                    className="rounded bg-lab-850 border-lab-750 text-accent-blue"
                  />
                  <span>Include Fault-Free Reference per Seed (for paired solver calibration)</span>
                </label>
              </div>
            </div>

            <div className="pt-3">
              <button
                type="submit"
                disabled={isSubmitting}
                className="w-full py-3 bg-accent-blue hover:bg-blue-600 disabled:opacity-50 text-white rounded-lg text-sm font-bold flex items-center justify-center space-x-2 shadow-lg transition"
              >
                <Play className="w-4 h-4" />
                <span>{isSubmitting ? 'Submitting Experiment...' : 'Start Experiment Batch'}</span>
              </button>
            </div>
          </div>
        </form>

        {/* Right Column: Live Experiment Monitor */}
        <div className="space-y-5">
          <div className="bg-lab-900 border border-lab-800 rounded-xl p-5 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-bold uppercase tracking-wider text-white">Active Batch Monitor</h3>
              {activeExp && activeExp.status === 'running' && (
                <button
                  type="button"
                  onClick={() => setCancelModal(true)}
                  className="px-2.5 py-1 rounded bg-accent-rose/15 text-accent-rose border border-accent-rose/30 text-xs font-medium hover:bg-accent-rose/25"
                >
                  Cancel Batch
                </button>
              )}
            </div>

            {activeExp ? (
              <div className="space-y-3">
                <div className="p-3 rounded-lg bg-lab-850 border border-lab-750">
                  <div className="text-sm font-bold text-white truncate">{activeExp.name}</div>
                  <div className="text-[11px] font-mono text-lab-400 mt-1 flex justify-between">
                    <span>Status: {activeExp.status.toUpperCase()}</span>
                    <span>{activeExp.completed_runs} / {activeExp.total_runs} Runs</span>
                  </div>

                  {/* Progress Bar */}
                  <div className="w-full bg-lab-950 rounded-full h-2 mt-2 overflow-hidden border border-lab-800">
                    <div
                      className="bg-accent-blue h-full transition-all duration-300"
                      style={{ width: `${progressPercent}%` }}
                    />
                  </div>
                </div>

                {/* Per-Run Progress Table */}
                <div className="max-h-[380px] overflow-y-auto space-y-1.5 font-mono text-xs pr-1">
                  {activeRuns.map((r) => (
                    <div
                      key={r.id}
                      className="p-2 rounded bg-lab-850/60 border border-lab-800 flex items-center justify-between"
                    >
                      <div>
                        <div className="font-semibold text-white text-[11px]">{r.mode}</div>
                        <div className="text-[10px] text-lab-400">Seed {r.seed}</div>
                      </div>
                      <div className="text-right">
                        <span className={`text-[10px] px-1.5 py-0.5 rounded font-bold ${
                          r.status === 'completed'
                            ? r.validation_valid
                              ? 'bg-accent-emerald/20 text-accent-emerald'
                              : 'bg-accent-amber/20 text-accent-amber'
                            : r.status === 'running'
                            ? 'bg-accent-blue/20 text-accent-blue'
                            : 'bg-accent-rose/20 text-accent-rose'
                        }`}>
                          {r.status === 'completed' ? (r.validation_valid ? 'Valid' : r.termination_reason) : r.status}
                        </span>
                        {r.simulated_time > 0 && (
                          <div className="text-[10px] text-lab-400 mt-0.5">{r.simulated_time} u</div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="text-center py-16 text-lab-500 text-xs">
                No experiment running. Configure parameters and click Start.
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Cancellation Confirmation Modal */}
      {cancelModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-lab-900 border border-lab-750 rounded-xl p-6 max-w-sm w-full space-y-4">
            <h3 className="text-sm font-bold text-white flex items-center space-x-2">
              <AlertCircle className="w-5 h-5 text-accent-rose" />
              <span>Confirm Experiment Cancellation</span>
            </h3>
            <p className="text-xs text-lab-300">
              Are you sure you want to cooperatively cancel the active experiment? Partial run results will be preserved
              in the database with status 'cancelled'.
            </p>
            <div className="flex justify-end space-x-2 pt-2">
              <button
                type="button"
                onClick={() => setCancelModal(false)}
                className="px-3 py-1.5 rounded bg-lab-800 text-lab-300 hover:text-white text-xs"
              >
                Back
              </button>
              <button
                type="button"
                onClick={handleCancel}
                className="px-3 py-1.5 rounded bg-accent-rose text-white text-xs font-bold"
              >
                Yes, Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
