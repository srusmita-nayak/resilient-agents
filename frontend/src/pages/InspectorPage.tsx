import React, { useState, useEffect } from 'react';
import { Shield, Search, ArrowRight, CheckCircle2, AlertTriangle, Layers, Info } from 'lucide-react';
import { api } from '../api/client';
import { ExperimentRecord, RunRecord, SimEvent } from '../api/types';

export const InspectorPage: React.FC = () => {
  const [experiments, setExperiments] = useState<ExperimentRecord[]>([]);
  const [selectedExpId, setSelectedExpId] = useState<string>('');
  const [runs, setRuns] = useState<RunRecord[]>([]);
  const [selectedRunId, setSelectedRunId] = useState<string>('');
  const [allEvents, setAllEvents] = useState<SimEvent[]>([]);
  const [messagesList, setMessagesList] = useState<string[]>([]);
  const [selectedMsgId, setSelectedMsgId] = useState<string>('');
  const [lifecycleEvents, setLifecycleEvents] = useState<SimEvent[]>([]);
  const [runDetail, setRunDetail] = useState<RunRecord | null>(null);

  useEffect(() => {
    async function loadExps() {
      try {
        const res = await api.listExperiments({ limit: 15 });
        setExperiments(res.experiments);
        if (res.experiments.length > 0) setSelectedExpId(res.experiments[0].id);
      } catch (err) {
        console.error(err);
      }
    }
    loadExps();
  }, []);

  useEffect(() => {
    if (!selectedExpId) return;
    async function loadRuns() {
      try {
        const res = await api.listRuns(selectedExpId);
        setRuns(res.runs);
        if (res.runs.length > 0) setSelectedRunId(res.runs[0].id);
      } catch (err) {
        console.error(err);
      }
    }
    loadRuns();
  }, [selectedExpId]);

  useEffect(() => {
    if (!selectedRunId) return;
    async function loadRunEvents() {
      try {
        const [rRes, evRes] = await Promise.all([
          api.getRun(selectedRunId),
          api.getRunEvents(selectedRunId, 0, 1000),
        ]);
        setRunDetail(rRes);
        setAllEvents(evRes.events);

        // Extract unique msg_ids
        const msgIds = Array.from(new Set(evRes.events.map((e) => e.msg_id).filter(Boolean) as string[]));
        setMessagesList(msgIds);
        if (msgIds.length > 0) {
          setSelectedMsgId(msgIds[0]);
        } else {
          setSelectedMsgId('');
          setLifecycleEvents([]);
        }
      } catch (err) {
        console.error(err);
      }
    }
    loadRunEvents();
  }, [selectedRunId]);

  useEffect(() => {
    if (!selectedRunId || !selectedMsgId) return;
    async function loadLifecycle() {
      try {
        const res = await api.getMessageLifecycle(selectedRunId, selectedMsgId);
        setLifecycleEvents(res.lifecycle);
      } catch (err) {
        console.error(err);
      }
    }
    loadLifecycle();
  }, [selectedRunId, selectedMsgId]);

  const metrics = runDetail?.metrics_summary;

  const getReasonExplanation = (type: string, payload: any) => {
    switch (type) {
      case 'SEND':
        return `Message dispatched by ${payload?.kind || 'DATA'} protocol. Attempt #${payload?.attempt || 1}.`;
      case 'DROP':
        return `Packet dropped in virtual channel due to ${payload?.reason === 'partition' ? 'active network partition window' : 'simulated packet loss probability'}.`;
      case 'TIMEOUT':
        return 'Sender did not receive an ACK matching correlation ID before the scheduled ACK timer expired.';
      case 'RETRY':
        return `Bounded retransmission attempt #${payload?.attempt} dispatched with exponential backoff delay of ${payload?.backoff_delay?.toFixed(1) || '—'} units.`;
      case 'ACK_RECEIVED':
        return `Correlated ACK received matching message ID. Retry timer cancelled. Recovery latency: ${payload?.recovery_latency?.toFixed(1) || '0.0'} units.`;
      case 'ACK_UNMATCHED':
        return 'Received ACK does not match any active pending request or arrived from unexpected sender. Ignored without state mutation.';
      case 'DUP_SUPPRESSED':
        return 'Message ID already recorded in bounded FIFO deduplication history. Payload re-application skipped; fresh ACK dispatched to sender.';
      case 'STALE_REJECTED':
        return `Incoming version (${payload?.incoming_version}) is less than or equal to current monotonic node version (${payload?.current_version}). Update rejected.`;
      case 'RETRY_EXHAUSTED':
        return 'Max retries reached without receiving an ACK. Link marked degraded; execution continues in degraded mode without deadlock.';
      case 'SYNC_REQ':
        return 'Agent requested authoritative boundary node snapshots from silent peer following round barrier expiration.';
      case 'SYNC_APPLIED':
        return 'Merged authoritative node snapshots into local state using monotonic version comparisons.';
      default:
        return 'Protocol state machine transition.';
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Selector Bar */}
      <div className="bg-lab-900 border border-lab-800 rounded-xl p-4 flex flex-wrap items-center justify-between gap-4">
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center space-x-2 text-xs font-bold text-white">
            <Shield className="w-4 h-4 text-accent-blue" />
            <span>MIDDLEWARE INSPECTOR</span>
          </div>

          <select
            value={selectedExpId}
            onChange={(e) => setSelectedExpId(e.target.value)}
            className="bg-lab-850 border border-lab-750 text-white rounded-lg px-3 py-1 text-xs"
          >
            {experiments.map((e) => (
              <option key={e.id} value={e.id}>{e.name} ({e.agent_type})</option>
            ))}
          </select>

          <select
            value={selectedRunId}
            onChange={(e) => setSelectedRunId(e.target.value)}
            className="bg-lab-850 border border-lab-750 text-white rounded-lg px-3 py-1 text-xs"
          >
            {runs.map((r) => (
              <option key={r.id} value={r.id}>{r.mode} | Seed {r.seed} | {r.outcome}</option>
            ))}
          </select>
        </div>

        {runDetail && (
          <div className="text-xs font-mono text-lab-300">
            Mode: <span className="font-bold text-white">{runDetail.mode}</span> | Termination: {runDetail.termination_reason}
          </div>
        )}
      </div>

      {/* Mechanism Counts Summary Banner */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3">
        {[
          { label: 'Retransmissions', val: metrics?.retransmissions || 0, color: 'text-accent-blue' },
          { label: 'ACKs Matched', val: metrics?.acks_received || 0, color: 'text-accent-emerald' },
          { label: 'Duplicates Suppressed', val: metrics?.duplicates_suppressed || 0, color: 'text-accent-violet' },
          { label: 'Stale Rejected', val: metrics?.stale_updates_rejected || 0, color: 'text-accent-amber' },
          { label: 'Sync Requests', val: metrics?.sync_requests || 0, color: 'text-accent-cyan' },
          { label: 'Degraded Peers', val: metrics?.degraded_peers || 0, color: 'text-accent-rose' },
        ].map((item, idx) => (
          <div key={idx} className="bg-lab-900 border border-lab-800 rounded-lg p-3 text-center">
            <div className="text-[10px] text-lab-400 font-mono uppercase">{item.label}</div>
            <div className={`text-xl font-bold font-mono ${item.color} mt-1`}>{item.val}</div>
          </div>
        ))}
      </div>

      {/* Main Grid: Message Selector Left, Lifecycle Detailed Timeline Right */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Messages List in this run */}
        <div className="bg-lab-900 border border-lab-800 rounded-xl p-5 flex flex-col h-[520px]">
          <h2 className="text-xs font-bold uppercase tracking-wider text-white mb-3 flex items-center space-x-2">
            <Search className="w-3.5 h-3.5 text-accent-blue" />
            <span>Messages in Run ({messagesList.length})</span>
          </h2>

          <div className="flex-1 overflow-y-auto space-y-1.5 font-mono text-xs pr-1">
            {messagesList.length === 0 ? (
              <div className="text-center py-20 text-lab-500">No message identifiers recorded.</div>
            ) : (
              messagesList.map((mId) => {
                const count = allEvents.filter((e) => e.msg_id === mId).length;
                const hasDrop = allEvents.some((e) => e.msg_id === mId && e.type === 'DROP');
                const hasAck = allEvents.some((e) => e.msg_id === mId && e.type === 'ACK_RECEIVED');
                return (
                  <div
                    key={mId}
                    onClick={() => setSelectedMsgId(mId)}
                    className={`p-2.5 rounded border cursor-pointer transition ${
                      selectedMsgId === mId
                        ? 'bg-lab-800 border-accent-blue text-white'
                        : 'bg-lab-850/60 border-lab-800 text-lab-300 hover:bg-lab-800/50'
                    }`}
                  >
                    <div className="flex items-center justify-between text-[11px] font-bold">
                      <span className="truncate">{mId}</span>
                      <span className="text-[10px] text-lab-400">{count} ev</span>
                    </div>
                    <div className="flex items-center space-x-2 mt-1 text-[10px]">
                      {hasDrop && <span className="text-accent-rose">Dropped</span>}
                      {hasAck && <span className="text-accent-emerald">ACK Recovered</span>}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Selected Message Lifecycle Inspector */}
        <div className="lg:col-span-2 bg-lab-900 border border-lab-800 rounded-xl p-5 flex flex-col h-[520px]">
          <div className="flex items-center justify-between mb-4 pb-3 border-b border-lab-800">
            <div>
              <h2 className="text-sm font-bold text-white flex items-center space-x-2">
                <span>Message Lifecycle Inspection:</span>
                <span className="font-mono text-accent-blue">{selectedMsgId || 'None'}</span>
              </h2>
              <p className="text-[11px] text-lab-400 mt-0.5">
                Causal sequence of transmission, network faults, retransmissions, and acknowledgments.
              </p>
            </div>
            {lifecycleEvents.length > 0 && (
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-lab-800 border border-lab-700 text-lab-300">
                {lifecycleEvents.length} Lifecycle Events
              </span>
            )}
          </div>

          <div className="flex-1 overflow-y-auto space-y-4 pr-2">
            {lifecycleEvents.length === 0 ? (
              <div className="text-center py-24 text-lab-500 text-xs">
                Select a message on the left to inspect its end-to-end lifecycle.
              </div>
            ) : (
              lifecycleEvents.map((ev, idx) => (
                <div key={idx} className="relative pl-6 border-l-2 border-lab-800 pb-3 last:border-transparent">
                  {/* Timeline Node Dot */}
                  <div className={`absolute -left-[9px] top-0 w-4 h-4 rounded-full border-2 bg-lab-950 flex items-center justify-center ${
                    ev.type === 'DROP' ? 'border-accent-rose' :
                    ev.type === 'ACK_RECEIVED' ? 'border-accent-emerald' :
                    ev.type === 'RETRY' ? 'border-accent-amber' :
                    'border-accent-blue'
                  }`} />

                  {/* Event Header */}
                  <div className="bg-lab-850 border border-lab-800 rounded-lg p-3">
                    <div className="flex items-center justify-between text-xs font-mono mb-1">
                      <div className="flex items-center space-x-2">
                        <span className={`font-bold px-2 py-0.5 rounded text-[10px] ${
                          ev.type === 'DROP' ? 'bg-accent-rose/15 text-accent-rose' :
                          ev.type === 'ACK_RECEIVED' ? 'bg-accent-emerald/15 text-accent-emerald' :
                          ev.type === 'RETRY' ? 'bg-accent-amber/15 text-accent-amber' :
                          'bg-accent-blue/15 text-accent-blue'
                        }`}>
                          {ev.type}
                        </span>
                        <span className="text-white font-semibold">
                          {ev.agent_id} {ev.target_agent_id ? `→ ${ev.target_agent_id}` : ''}
                        </span>
                      </div>
                      <span className="text-lab-400 text-[11px]">t={ev.sim_time.toFixed(1)} virtual units</span>
                    </div>

                    {/* Plain Language Explanation of WHY this happened */}
                    <p className="text-xs text-lab-200 mt-1 leading-relaxed">
                      {getReasonExplanation(ev.type, ev.payload)}
                    </p>

                    {/* Raw payload toggle or viewer */}
                    {ev.payload && Object.keys(ev.payload).length > 0 && (
                      <div className="mt-2 text-[10px] font-mono bg-lab-950/80 p-2 rounded border border-lab-850 text-lab-400">
                        <pre className="overflow-x-auto">{JSON.stringify(ev.payload, null, 2)}</pre>
                      </div>
                    )}
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
