import React, { useState, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend, CartesianGrid } from 'recharts';
import { Download, Info, BarChart2, CheckCircle, AlertTriangle, Layers } from 'lucide-react';
import { api } from '../api/client';
import { AnalyticsSummaryResponse, ExperimentRecord } from '../api/types';

export const AnalyticsPage: React.FC = () => {
  const [experiments, setExperiments] = useState<ExperimentRecord[]>([]);
  const [selectedExpId, setSelectedExpId] = useState<string>('');
  const [summaryData, setSummaryData] = useState<AnalyticsSummaryResponse | null>(null);
  const [pairedFaultFreeOnly, setPairedFaultFreeOnly] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(true);
  const [activeFormulaTab, setActiveFormulaTab] = useState<string>('wilson');

  useEffect(() => {
    async function loadInitial() {
      try {
        const res = await api.listExperiments({ limit: 50 });
        setExperiments(res.experiments);
        if (res.experiments.length > 0) {
          // Prioritize substantive multi-run research sweeps over test artifacts
          const chosen =
            res.experiments.find(
              (e) => e.total_runs >= 10 && !e.name.startsWith('=') && !e.name.includes('Test')
            ) || res.experiments[0];
          setSelectedExpId(chosen.id);
        }
      } catch (err) {
        console.error(err);
      }
    }
    loadInitial();
  }, []);

  useEffect(() => {
    if (!selectedExpId) return;
    async function loadSummary() {
      setLoading(true);
      try {
        const res = await api.getAnalyticsSummary(selectedExpId, pairedFaultFreeOnly);
        setSummaryData(res);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    loadSummary();
  }, [selectedExpId, pairedFaultFreeOnly]);

  const modes = summaryData?.modes || {};
  const currentExp = experiments.find((e) => e.id === selectedExpId);

  // Prepare chart data for Success Rate & Deadlock Rate
  const chartData = Object.entries(modes).map(([mName, stats]) => ({
    mode: mName === 'timeout_baseline' ? 'Timeout Base' : mName.charAt(0).toUpperCase() + mName.slice(1),
    validRate: Math.round(stats.valid_rate * 100),
    deadlockRate: Math.round(stats.deadlock_rate * 100),
    meanMsgs: Math.round(stats.mean_messages_sent),
    simTime: Math.round(stats.mean_simulated_time),
    n: stats.n,
    ciLower: Math.round(stats.valid_rate_ci_lower * 100),
    ciUpper: Math.round(stats.valid_rate_ci_upper * 100),
  }));

  return (
    <div className="space-y-6">
      {/* Top Header & Filters */}
      <div className="bg-lab-900 border border-lab-800 rounded-xl p-5 flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2 text-accent-blue font-mono text-xs font-bold uppercase">
            <BarChart2 className="w-4 h-4" />
            <span>RESEARCH ANALYTICS & STATISTICAL COMPARISON</span>
          </div>
          <h1 className="text-xl font-bold text-white mt-1">
            Mode A vs Mode B vs Mode C Rigorous Evaluation
          </h1>
          <p className="text-xs text-lab-300 mt-0.5">
            Software-emulated network faults • Agent Type:{' '}
            <span className="font-bold text-white uppercase">{currentExp?.agent_type || 'DETERMINISTIC'}</span>
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {/* Select Experiment */}
          <select
            value={selectedExpId}
            onChange={(e) => setSelectedExpId(e.target.value)}
            className="bg-lab-850 border border-lab-750 text-white rounded-lg px-3 py-1.5 text-xs font-mono"
          >
            {experiments.map((e) => (
              <option key={e.id} value={e.id}>
                {e.name} ({e.agent_type}) • {e.total_runs} runs
              </option>
            ))}
          </select>


          {/* Toggle Paired Calibration */}
          <button
            type="button"
            onClick={() => setPairedFaultFreeOnly(!pairedFaultFreeOnly)}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold border transition ${
              pairedFaultFreeOnly
                ? 'bg-accent-violet/20 border-accent-violet text-white'
                : 'bg-lab-850 border-lab-750 text-lab-400 hover:text-white'
            }`}
          >
            {pairedFaultFreeOnly ? 'Filtered: Solvable Seeds Only' : 'All Seeds (Intention-to-Treat)'}
          </button>

          {/* CSV Export */}
          {selectedExpId && (
            <a
              href={api.getExportExperimentUrl(selectedExpId)}
              download
              className="inline-flex items-center space-x-1.5 px-3 py-1.5 bg-accent-blue hover:bg-blue-600 text-white rounded-lg text-xs font-bold shadow"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Export CSV</span>
            </a>
          )}
        </div>
      </div>

      {/* Main Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Valid Solution Rate Chart with Wilson CIs */}
        <div className="bg-lab-900 border border-lab-800 rounded-xl p-5">
          <div className="flex items-center justify-between mb-3">
            <div>
              <h2 className="text-sm font-bold text-white uppercase tracking-wider">
                Valid Solution Rate by Protocol Mode (%)
              </h2>
              <p className="text-[11px] text-lab-400">
                Independent validator check (0 constraint violations) with Wilson 95% Confidence Intervals
              </p>
            </div>
          </div>

          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} margin={{ top: 15, right: 20, left: 0, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#17223b" />
                <XAxis dataKey="mode" stroke="#6d88c2" fontSize={11} />
                <YAxis unit="%" domain={[0, 100]} stroke="#6d88c2" fontSize={11} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#0d1322', borderColor: '#233254', fontSize: '11px' }}
                  formatter={(val: any, name: any, item: any) => [
                    `${val}% (95% CI: [${item.payload.ciLower}%, ${item.payload.ciUpper}%], n=${item.payload.n})`,
                    name,
                  ]}
                />
                <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }} />
                <Bar dataKey="validRate" fill="#3b82f6" name="Valid Solution Rate (%)" radius={[4, 4, 0, 0]} />
                <Bar dataKey="deadlockRate" fill="#f43f5e" name="Deadlock / Stall Rate (%)" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Message Overhead & Communication Cost Chart */}
        <div className="bg-lab-900 border border-lab-800 rounded-xl p-5">
          <div className="flex items-center justify-between mb-3">
            <div>
              <h2 className="text-sm font-bold text-white uppercase tracking-wider">
                Communication Overhead (Mean Messages Sent)
              </h2>
              <p className="text-[11px] text-lab-400">
                Mean message exchange volume illustrating the trade-off of resilience ACKs and retries
              </p>
            </div>
          </div>

          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} margin={{ top: 15, right: 20, left: 0, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#17223b" />
                <XAxis dataKey="mode" stroke="#6d88c2" fontSize={11} />
                <YAxis stroke="#6d88c2" fontSize={11} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#0d1322', borderColor: '#233254', fontSize: '11px' }}
                  formatter={(val: any) => [`${val} messages`, 'Mean Sent']}
                />
                <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }} />
                <Bar dataKey="meanMsgs" fill="#8b5cf6" name="Mean Messages Dispatched" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Numerical Metrics & Confidence Interval Table */}
      <div className="bg-lab-900 border border-lab-800 rounded-xl p-5">
        <h2 className="text-sm font-bold text-white uppercase tracking-wider mb-3">
          Statistical Rigor Table: Metrics, Sample Sizes ($n$), and 95% Confidence Intervals
        </h2>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead>
              <tr className="border-b border-lab-800 text-lab-400 text-[11px]">
                <th className="pb-2">Protocol Mode</th>
                <th className="pb-2">Sample Size ($n$)</th>
                <th className="pb-2">Valid Rate (Point)</th>
                <th className="pb-2">Wilson 95% CI</th>
                <th className="pb-2">Deadlock Rate</th>
                <th className="pb-2">Mean Sim Time (Bootstrap CI)</th>
                <th className="pb-2">Median Sim Time (IQR)</th>
                <th className="pb-2">Mean Messages</th>
                <th className="pb-2">Recovery Success</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-lab-850">
              {Object.entries(modes).map(([mName, s]) => (
                <tr key={mName} className="hover:bg-lab-850/50">
                  <td className="py-2.5 font-bold text-white">{mName}</td>
                  <td className="py-2.5 text-lab-300">{s.n}</td>
                  <td className="py-2.5 font-bold text-accent-emerald">
                    {(s.valid_rate * 100).toFixed(1)}%
                  </td>
                  <td className="py-2.5 text-lab-300">
                    [{(s.valid_rate_ci_lower * 100).toFixed(1)}%, {(s.valid_rate_ci_upper * 100).toFixed(1)}%]
                  </td>
                  <td className="py-2.5 text-accent-rose">
                    {(s.deadlock_rate * 100).toFixed(1)}%
                  </td>
                  <td className="py-2.5 text-lab-300">
                    {s.mean_simulated_time} u [{s.simulated_time_ci_lower}, {s.simulated_time_ci_upper}]
                  </td>
                  <td className="py-2.5 text-lab-300">
                    {s.median_simulated_time} u (IQR: {s.iqr_simulated_time})
                  </td>
                  <td className="py-2.5 text-accent-violet">{s.mean_messages_sent}</td>
                  <td className="py-2.5 text-accent-cyan">
                    {(s.recovery_success_rate * 100).toFixed(1)}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Paired Statistical Hypothesis Tests: McNemar's Test */}
      {summaryData?.paired_tests && Object.keys(summaryData.paired_tests).length > 0 && (
        <div className="bg-lab-900 border border-lab-800 rounded-xl p-5">
          <h2 className="text-sm font-bold text-white uppercase tracking-wider mb-2">
            Paired Hypothesis Testing: McNemar's Exact Test on Discordant Pairs
          </h2>
          <p className="text-xs text-lab-300 mb-4">
            Evaluating whether the observed improvement of Mode C over baseline is statistically significant across identical seeds.
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {Object.entries(summaryData.paired_tests).map(([testKey, res]: any) => (
              <div key={testKey} className="p-4 rounded-lg bg-lab-850 border border-lab-750 text-xs">
                <div className="font-bold text-white text-sm mb-1 uppercase font-mono">{testKey}</div>
                <div className="grid grid-cols-2 gap-2 text-lab-300 font-mono text-[11px] my-2">
                  <div>Total Paired Seeds: {res.total_pairs}</div>
                  <div>Exact p-value: <span className="font-bold text-white">{res.p_value.toFixed(4)}</span></div>
                  <div>Mode A/B Valid Rate: {(res.rate_A * 100).toFixed(1)}%</div>
                  <div>Mode C Valid Rate: {(res.rate_B * 100).toFixed(1)}%</div>
                </div>
                <div className={`p-2 rounded mt-2 font-medium ${
                  res.is_significant_05
                    ? 'bg-accent-emerald/15 text-accent-emerald border border-accent-emerald/30'
                    : 'bg-lab-800 text-lab-400'
                }`}>
                  {res.is_significant_05
                    ? `Statistically Significant (p < 0.05). Null hypothesis of equal performance rejected.`
                    : `Difference not statistically significant at alpha=0.05 (p >= 0.05).`}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* "How Computed" Formula & Methodology Panel */}
      <div className="bg-lab-900 border border-lab-800 rounded-xl p-5">
        <h2 className="text-sm font-bold text-white uppercase tracking-wider mb-3 flex items-center space-x-2">
          <Info className="w-4 h-4 text-accent-blue" />
          <span>Research Methodology & Metric Formulation Guide</span>
        </h2>

        <div className="flex border-b border-lab-800 space-x-4 mb-3 text-xs">
          {[
            { id: 'wilson', label: 'Wilson Score Interval' },
            { id: 'mcnemar', label: "McNemar's Exact Test" },
            { id: 'bootstrap', label: 'Bootstrap Resampling' },
            { id: 'overhead', label: 'Message Overhead Formula' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveFormulaTab(tab.id)}
              className={`pb-2 font-medium transition ${
                activeFormulaTab === tab.id
                  ? 'border-b-2 border-accent-blue text-white'
                  : 'text-lab-400 hover:text-lab-200'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <div className="text-xs text-lab-300 leading-relaxed font-mono bg-lab-950 p-4 rounded-lg border border-lab-850">
          {activeFormulaTab === 'wilson' && (
            <div>
              <p className="font-bold text-white mb-1">Wilson 95% Score Confidence Interval:</p>
              <p>CI = (p + z^2/(2n) ± z * sqrt((p*(1-p)/n) + (z^2/(4n^2)))) / (1 + z^2/n)</p>
              <p className="mt-2 text-lab-400">
                Where z = 1.95996 for 95% confidence, p = valid / n. Superior to standard normal approximation for extreme proportions (near 0 or 1) and smaller sample sizes.
              </p>
            </div>
          )}
          {activeFormulaTab === 'mcnemar' && (
            <div>
              <p className="font-bold text-white mb-1">McNemar's Exact Test on Discordant Pairs:</p>
              <p>Two-sided exact binomial test on discordant pairs (b, c) with null hypothesis p = 0.5.</p>
              <p className="mt-2 text-lab-400">
                Evaluates seeds where one protocol succeeded and the other failed, properly accounting for the paired within-subject design across identical problem graphs.
              </p>
            </div>
          )}
          {activeFormulaTab === 'bootstrap' && (
            <div>
              <p className="font-bold text-white mb-1">Seeded Non-Parametric Bootstrap Interval (1000 resamples):</p>
              <p>Mean estimation sampled with replacement using fixed random seed (42). 2.5th and 97.5th percentiles define the empirical 95% confidence limits.</p>
            </div>
          )}
          {activeFormulaTab === 'overhead' && (
            <div>
              <p className="font-bold text-white mb-1">Message Overhead Ratio:</p>
              <p>Overhead Ratio = (Mean Messages Mode C) / (Mean Messages Baseline Mode A)</p>
              <p className="mt-2 text-lab-400">
                Measures the exact network bandwidth penalty incurred by acknowledgment traffic and retransmissions in exchange for fault recovery.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
