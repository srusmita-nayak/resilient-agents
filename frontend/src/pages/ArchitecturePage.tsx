import React from 'react';
import { BookOpen, Shield, Layers, Cpu, Database, CheckCircle2, AlertTriangle, ArrowRight } from 'lucide-react';

export const ArchitecturePage: React.FC = () => {
  return (
    <div className="space-y-8 max-w-5xl mx-auto">
      {/* Title */}
      <div>
        <div className="flex items-center space-x-2 text-accent-blue font-mono text-xs font-bold uppercase">
          <BookOpen className="w-4 h-4" />
          <span>FORMAL SYSTEM ARCHITECTURE & PROTOCOL SPECIFICATION</span>
        </div>
        <h1 className="text-2xl font-bold text-white mt-1">
          Resilient Agents Architecture & Protocol State Machine
        </h1>
        <p className="text-sm text-lab-300 mt-1">
          A discrete-event simulation platform for investigating fault-tolerant distributed constraint coordination under adversarial communication.
        </p>
      </div>

      {/* SVG System Architecture Diagram */}
      <div className="bg-lab-900 border border-lab-800 rounded-xl p-6">
        <h2 className="text-sm font-bold uppercase tracking-wider text-white mb-4 flex items-center space-x-2">
          <Layers className="w-4 h-4 text-accent-blue" />
          <span>System Component Architecture</span>
        </h2>

        <div className="w-full bg-lab-950 border border-lab-850 rounded-lg p-4 flex items-center justify-center overflow-x-auto">
          <svg viewBox="0 0 740 320" className="w-full max-w-[740px]">
            {/* Frontend Layer Box */}
            <rect x="20" y="20" width="180" height="280" rx="8" fill="#0d1322" stroke="#233254" strokeWidth="1.5" />
            <text x="110" y="45" textAnchor="middle" fill="#6d88c2" fontSize="12" fontWeight="bold">REACT FRONTEND</text>
            <rect x="35" y="65" width="150" height="35" rx="4" fill="#17223b" />
            <text x="110" y="87" textAnchor="middle" fill="#ffffff" fontSize="11">Overview & Analytics</text>
            <rect x="35" y="110" width="150" height="35" rx="4" fill="#17223b" />
            <text x="110" y="132" textAnchor="middle" fill="#ffffff" fontSize="11">Workspace SVG Replay</text>
            <rect x="35" y="155" width="150" height="35" rx="4" fill="#17223b" />
            <text x="110" y="177" textAnchor="middle" fill="#ffffff" fontSize="11">Experiment Lab (Form)</text>
            <rect x="35" y="200" width="150" height="35" rx="4" fill="#17223b" />
            <text x="110" y="222" textAnchor="middle" fill="#ffffff" fontSize="11">Middleware Inspector</text>
            <rect x="35" y="245" width="150" height="35" rx="4" fill="#17223b" />
            <text x="110" y="267" textAnchor="middle" fill="#ffffff" fontSize="11">WebSocket Hook (Resume)</text>

            {/* Arrows Between FE and Backend */}
            <line x1="200" y1="110" x2="260" y2="110" stroke="#3b82f6" strokeWidth="2" markerEnd="url(#arrow)" />
            <text x="230" y="100" textAnchor="middle" fill="#6d88c2" fontSize="9" fontFamily="monospace">REST API</text>
            <line x1="260" y1="230" x2="200" y2="230" stroke="#10b981" strokeWidth="2" markerEnd="url(#arrow)" />
            <text x="230" y="222" textAnchor="middle" fill="#10b981" fontSize="9" fontFamily="monospace">WS Events</text>

            {/* Backend Layer Box */}
            <rect x="260" y="20" width="260" height="280" rx="8" fill="#0d1322" stroke="#3b82f6" strokeWidth="1.5" />
            <text x="390" y="45" textAnchor="middle" fill="#3b82f6" fontSize="12" fontWeight="bold">FASTAPI BACKEND</text>
            
            <rect x="275" y="65" width="230" height="40" rx="4" fill="#17223b" />
            <text x="390" y="85" textAnchor="middle" fill="#ffffff" fontSize="11" fontWeight="bold">Discrete-Event Scheduler</text>
            <text x="390" y="98" textAnchor="middle" fill="#6d88c2" fontSize="9" fontFamily="monospace">Virtual Clock • Priority Queue</text>

            <rect x="275" y="115" width="230" height="45" rx="4" fill="#17223b" />
            <text x="390" y="135" textAnchor="middle" fill="#ffffff" fontSize="11" fontWeight="bold">Fault Injector & Channel</text>
            <text x="390" y="148" textAnchor="middle" fill="#f43f5e" fontSize="9" fontFamily="monospace">Loss • Latency • Dups • Partitions</text>

            <rect x="275" y="170" width="230" height="45" rx="4" fill="#17223b" />
            <text x="390" y="190" textAnchor="middle" fill="#ffffff" fontSize="11" fontWeight="bold">Modes A / B / C Middleware</text>
            <text x="390" y="203" textAnchor="middle" fill="#10b981" fontSize="9" fontFamily="monospace">Retries • ACKs • Versions • Sync</text>

            <rect x="275" y="225" width="230" height="45" rx="4" fill="#17223b" />
            <text x="390" y="245" textAnchor="middle" fill="#ffffff" fontSize="11" fontWeight="bold">Agents & Decision Policy</text>
            <text x="390" y="258" textAnchor="middle" fill="#8b5cf6" fontSize="9" fontFamily="monospace">Min-Conflict DSA / LLM Adapter</text>

            {/* Persistence Layer Box */}
            <rect x="560" y="20" width="160" height="280" rx="8" fill="#0d1322" stroke="#233254" strokeWidth="1.5" />
            <text x="640" y="45" textAnchor="middle" fill="#6d88c2" fontSize="12" fontWeight="bold">SQLITE DATABASE</text>
            <rect x="575" y="70" width="130" height="35" rx="4" fill="#17223b" />
            <text x="640" y="92" textAnchor="middle" fill="#ffffff" fontSize="11">WAL Mode Journal</text>
            <rect x="575" y="120" width="130" height="35" rx="4" fill="#17223b" />
            <text x="640" y="142" textAnchor="middle" fill="#ffffff" fontSize="11">Experiments Table</text>
            <rect x="575" y="170" width="130" height="35" rx="4" fill="#17223b" />
            <text x="640" y="192" textAnchor="middle" fill="#ffffff" fontSize="11">Runs Table</text>
            <rect x="575" y="220" width="130" height="35" rx="4" fill="#17223b" />
            <text x="640" y="242" textAnchor="middle" fill="#ffffff" fontSize="11">Events Table (WAL)</text>

            {/* Arrows Between Backend and DB */}
            <line x1="505" y1="160" x2="560" y2="160" stroke="#8b5cf6" strokeWidth="2" markerEnd="url(#arrow)" />
          </svg>
        </div>
      </div>

      {/* Protocol Modes Comparison Table */}
      <div className="bg-lab-900 border border-lab-800 rounded-xl p-6">
        <h2 className="text-sm font-bold uppercase tracking-wider text-white mb-4">
          Comparative Evaluation Matrix: Protocol Modes
        </h2>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead>
              <tr className="border-b border-lab-800 text-lab-400 text-[11px]">
                <th className="pb-3">Mechanism</th>
                <th className="pb-3">Mode A: Baseline</th>
                <th className="pb-3">Mode B: Timeout Baseline</th>
                <th className="pb-3">Mode C: Protected Middleware</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-lab-850 text-lab-200">
              <tr>
                <td className="py-2.5 font-bold text-white font-sans">Round Synchronization</td>
                <td>Strict synchronous barrier</td>
                <td>Round barrier with timeout</td>
                <td>Round barrier with timeout & re-coordination</td>
              </tr>
              <tr>
                <td className="py-2.5 font-bold text-white font-sans">Behavior on Dropped Packet</td>
                <td className="text-accent-rose">Hangs in deadlock indefinitely</td>
                <td className="text-accent-amber">Skips silent peer; stale state</td>
                <td className="text-accent-emerald">Exponential backoff retry & recovery</td>
              </tr>
              <tr>
                <td className="py-2.5 font-bold text-white font-sans">Message Delivery Semantics</td>
                <td>Best-effort (0 retries)</td>
                <td>Best-effort (0 retries)</td>
                <td className="text-accent-emerald">Bounded at-least-once attempts</td>
              </tr>
              <tr>
                <td className="py-2.5 font-bold text-white font-sans">Duplicate Suppression</td>
                <td className="text-accent-rose">None (re-applied blindly)</td>
                <td className="text-accent-rose">None (re-applied blindly)</td>
                <td className="text-accent-emerald">At-most-once application by msg_id</td>
              </tr>
              <tr>
                <td className="py-2.5 font-bold text-white font-sans">State Ordering & Conflicts</td>
                <td>Last arrival overwrites</td>
                <td>Last arrival overwrites</td>
                <td className="text-accent-emerald">Monotonic versions (single-writer per node)</td>
              </tr>
              <tr>
                <td className="py-2.5 font-bold text-white font-sans">Post-Partition Healing</td>
                <td className="text-accent-rose">Deadlocked (no recovery)</td>
                <td className="text-accent-amber">Divergent states</td>
                <td className="text-accent-emerald">Authoritative snapshot reconciliation</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* Protocol State Machine & Assumptions */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-lab-900 border border-lab-800 rounded-xl p-5 space-y-3">
          <h3 className="text-xs font-bold uppercase tracking-wider text-white flex items-center space-x-2">
            <Shield className="w-4 h-4 text-accent-blue" />
            <span>Guarantees & Assumptions</span>
          </h3>
          <ul className="text-xs text-lab-300 space-y-2 list-disc pl-4 leading-relaxed font-sans">
            <li>
              <strong className="text-white">Crash-Free Agents:</strong> Agents do not crash silently. Software faults (loss, delay, jitter, partition) occur strictly within the communication transport layer.
            </li>
            <li>
              <strong className="text-white">Single-Writer Monotonic Ownership:</strong> Each graph node is authored exclusively by its designated agent. Node versions are strictly monotonic (v_(t+1) &gt; v_t).
            </li>
            <li>
              <strong className="text-white">Bounded Recovery:</strong> At-least-once delivery attempts are bounded by <code className="font-mono text-accent-blue">max_retries</code>. When exhausted, degraded status is logged and execution proceeds safely without hanging.
            </li>
            <li>
              <strong className="text-white">No Exactly-Once Claim:</strong> Network transport provides bounded at-least-once dispatch combined with idempotent deduplication to achieve at-most-once application.
            </li>
          </ul>
        </div>

        <div className="bg-lab-900 border border-lab-800 rounded-xl p-5 space-y-3">
          <h3 className="text-xs font-bold uppercase tracking-wider text-white flex items-center space-x-2">
            <AlertTriangle className="w-4 h-4 text-accent-amber" />
            <span>Known Threats to Validity & Limitations</span>
          </h3>
          <ul className="text-xs text-lab-300 space-y-2 list-disc pl-4 leading-relaxed font-sans">
            <li>
              <strong className="text-white">Software Emulation:</strong> Faults are simulated via pseudo-random scheduling in discrete virtual time rather than over physical Ethernet hardware.
            </li>
            <li>
              <strong className="text-white">Discrete Problem Domain:</strong> Current benchmark focuses on Distributed Graph Coloring (DCR). Generalization to continuous optimization requires further problem adapters.
            </li>
            <li>
              <strong className="text-white">LLM Determinism:</strong> LLM agents exhibit non-deterministic response times and non-zero token consumption; deterministic baselines are evaluated separately.
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
};
