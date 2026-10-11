# Resilient Agents: Fault-Tolerant Multi-Agent Coordination Research Platform

A complete, runnable, tested research prototype designed to investigate distributed multi-agent coordination resilience under lossy, delayed, and partitioned communication networks.

---

## 1. What the Project Does and Why

Modern multi-agent systems—whether running algorithmic coordination heuristics or Large Language Model (LLM) agents—typically assume reliable underlying communication. In decentralized or edge deployments, however, real network channels suffer from packet drops, high jitter, out-of-order delivery, and temporary network partitions.

This platform provides an environment to study how distributed communication protocols protect multi-agent coordination against communication faults. Using **Distributed Graph Coloring (DCR)** as an NP-complete constraint benchmark with guaranteed planted solutions, the platform compares three distinct communication modes across identical seeds:
1. **Mode A (Baseline):** Strict synchronous rounds where agents wait indefinitely for peer updates.
2. **Mode B (Timeout Baseline):** Synchronous rounds with barrier timeouts that skip silent peers.
3. **Mode C (Protected Middleware):** A state machine implementing unique message IDs, explicit ACK tracking, bounded exponential backoff retransmissions, duplicate suppression, monotonic version-based conflict resolution, authoritative boundary snapshots, and post-partition state reconciliation.

---

## 2. Research Problem, Question & Objectives

- **Research Problem:** When multi-agent systems operate over unreliable channels, missing messages can cause deadlocks (hanging in synchronous round barriers) or cascading state divergence (making decisions based on stale or out-of-order constraints).
- **Primary Research Question:** *How do acknowledgment-based retransmission, monotonic versioning, and snapshot reconciliation mitigate coordination failure and deadlock in multi-agent constraint reasoning over unreliable communication channels, and what is the exact bandwidth overhead incurred?*
- **Research Objectives:**
  1. Measure task completion rates (independently validated solutions with zero edge conflicts).
  2. Measure deadlock and stall rates under software-emulated network faults.
  3. Quantify message overhead and recovery latency.
  4. Perform paired statistical hypothesis testing (McNemar's exact test and Wilson score confidence intervals).
- **Expected Contribution (Cautiously Stated):** Retries, timeouts, ACKs, and versioning are established distributed systems techniques; the contribution evaluated here is their rigorous combination applied to multi-agent coordination, tested against fair, equivalent baselines.

---

## 3. Plain-Language Explanation of Every Part

- **The Problem Benchmark:** Distributed Graph Coloring. Each agent owns a portion of graph nodes and must pick an integer color (e.g., 0, 1, or 2) such that no two connected nodes share the same color. Boundary edges between agents require message exchanges.
- **The Agents:** Software entities that execute local decisions (min-conflict algorithm or LLM adapter) to recolor conflicting nodes in successive rounds.
- **The Virtual Channel:** The simulated communication layer that intercepts messages, rolls a seeded random die to decide whether to drop, delay, or duplicate packets, and delivers them.
- **The Discrete-Event Scheduler:** A virtual clock that keeps time in simulation units rather than real seconds. This allows experiments to finish in milliseconds while ensuring that fault sequences are 100% reproducible by seed.
- **The Independent Validator:** An isolated verification module that inspects the final global assignment to guarantee zero edge conflicts.
- **The Database:** A local SQLite database in Write-Ahead-Logging (WAL) mode that permanently records all experiments, runs, and event logs.
- **The Web Dashboard:** A research laboratory UI with interactive agent topologies, playback scrubber, configuration forms, and charts with confidence intervals.

---

## 4. Architecture and Module Roles

```
resilient-agents/
  backend/
    app/
      core/          # Virtual clock (DiscreteEventScheduler), messages, faults, channel
      middleware/    # Mode A (baseline), Mode B (timeout), Mode C (protected state machine)
      agents/        # Base agent, deterministic policy, Gemini LLM adapter, mock provider
      problems/      # Planted graph coloring generator, independent validator, registry
      experiments/   # Single run runner, orchestrator background worker thread
      metrics/       # Event derivations, Wilson CI, McNemar exact test, bootstrap
      db/            # SQLite connection pool, repository, startup reconciliation
      api/           # FastAPI REST routers, WebSocket streaming manager, CSV exports
  frontend/          # React 18 + TypeScript + Vite + Tailwind CSS + Recharts
  results/           # Real CSV exports from 30-seed empirical experiment sweeps
  scripts/           # PowerShell developer automation scripts
  docs/              # Full scientific specifications and alignment matrices
```

---

## 5. How Agents Communicate

1. In each round, an agent inspects its owned nodes and constructs a payload containing its current boundary states: `node_id -> (color, version)`.
2. The agent hands the message to its assigned middleware.
3. The middleware passes the message to the `VirtualChannel`.
4. The channel evaluates configured packet loss and latency parameters, scheduling a delivery callback in the `DiscreteEventScheduler`.
5. Upon delivery, the recipient's middleware processes the payload and delivers it to the receiving agent.

---

## 6. How the Fault Injector Works

The `FaultInjector` uses a seeded pseudo-random number generator (`random.Random(seed)`):
- **Packet Loss:** If `random() < loss_rate`, the packet is dropped immediately and logged as a `DROP` event.
- **Network Latency & Jitter:** Calculates delivery delay: $t_{delay} = \text{uniform}(min\_latency, max\_latency) \pm jitter$.
- **Reordering:** Injects an extra delay into selected packets so subsequent messages arrive earlier.
- **Duplicates:** Dispatches duplicate copies at a slight temporal offset.
- **Partitions:** Checks if virtual time falls inside a configured partition window $[t_{start}, t_{start} + duration]$. If active, all traffic between partitioned agents is dropped.

---

## 7. How the Middleware Handles Unreliable Communication

- In **Mode A**, any dropped message causes the waiting agent to hang forever waiting for the round barrier to complete. The simulation scheduler detects an empty queue and records a `DEADLOCK`.
- In **Mode B**, a timer disarms the barrier after a deadline. Silent peers are skipped, allowing execution to continue, but state divergence can occur because lost messages are never recovered.
- In **Mode C**, every `DATA` packet requires an `ACK`. If an ACK does not arrive within `ack_timeout`, the sender retransmits with exponential backoff. Recipients reject duplicate packets via bounded history checks while re-sending ACKs. Monotonic versions (`v_new > v_current`) reject stale updates. If a partition heals, authoritative snapshot synchronization reconciles state.

---

## 8. Differences Between the Three Modes

| Feature | Mode A: Synchronous Baseline | Mode B: Timeout Baseline | Mode C: Protected Middleware |
|---|---|---|---|
| Round Barrier | Waits indefinitely | Skips after timeout | Times out & triggers re-coordination |
| Retransmissions | None (0 retries) | None (0 retries) | Bounded exponential backoff |
| ACKs | None | None | Explicit with correlation ID matching |
| Duplicate Suppression | None | None | At-most-once application by `msg_id` |
| Conflict Ordering | Last arrival overwrites | Last arrival overwrites | Single-writer monotonic versions |
| Post-Partition Recovery | Fails / Deadlocks | Diverges | Reconciles via authoritative snapshots |

---

## 9. Prerequisites (Windows 10/11)

1. **Python 3.12 or 3.13:** [Download Python for Windows](https://www.python.org/downloads/) (Ensure *"Add python.exe to PATH"* is checked during installation).
2. **Node.js 20 or 22 LTS:** [Download Node.js](https://nodejs.org/en/download/) (Includes npm).
3. **Git for Windows:** [Download Git](https://git-scm.com/download/win).
4. **PowerShell 5.1+ / PowerShell 7.**

---

## 10. Quick Start: Exact PowerShell Commands

Open PowerShell in the `resilient-agents` folder:

### Step 1: Handling PowerShell Execution Policy
If PowerShell blocks running scripts, bypass it for the current session:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

### Step 2: Automated Setup (One Command)
Run the setup script to create the Python virtual environment and install dependencies:
```powershell
.\scripts\setup.ps1
```

*Manual Setup Alternative:*
```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements-dev.txt
cd frontend
npm install
cd ..
Copy-Item .env.example .env
```

### Step 3: Start the Backend Server
```powershell
.\scripts\run-backend.ps1
```
The backend starts at: **http://127.0.0.1:8000**  
Interactive API Swagger Docs: **http://127.0.0.1:8000/docs**

### Step 4: Start the Frontend UI (In a second PowerShell window)
```powershell
.\scripts\run-frontend.ps1
```
The web dashboard opens at: **http://localhost:5173**

---

## 11. Configuring Gemini API Key Safely

1. Open `.env` in a text editor (created from `.env.example`).
2. Add your key:
   ```env
   GEMINI_API_KEY=AIzaSy...your_key_here
   GEMINI_MODEL=gemini-2.5-flash
   LLM_CALL_BUDGET=50
   ```
3. Test the connection from the UI or via curl:
   ```powershell
   Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/llm/test-connection" -Method Post -ContentType "application/json" -Body '{}'
   ```
*Security Note: The key is loaded strictly into memory by the backend. It is never logged, never returned over the API, never written to exports, and never sent to the browser.*

---

## 12. Running Experiments & Reproducibility Verification

### Running Experiments from the UI:
1. Navigate to **http://localhost:5173/lab**.
2. Choose a problem difficulty preset (*Easy*, *Medium*, or *Hard*).
3. Choose a network condition preset (*Reliable*, *Lossy 25%*, *Severe 50%*, or *Partition Burst*).
4. Select desired execution modes (Mode A, Mode B, Mode C).
5. Enter integer seeds (e.g., `42, 43, 44`).
6. Click **Start Experiment Batch**. Watch real-time execution in the progress table.

### Verifying Scientific Reproducibility:
1. Navigate to **http://localhost:5173/history**.
2. Click the green checkmark icon (**Verify Reproducibility**) next to any completed experiment.
3. The platform verifies that re-running the recorded seed sequence reproduces identical event-derived metrics.

---

## 13. How to Interpret Metrics and Charts

- **Valid Solution Rate (%):** The proportion of runs that achieved zero edge conflicts according to the independent validator. Displayed with **Wilson 95% Confidence Intervals**.
- **Deadlock / Stall Rate (%):** The proportion of runs where agents became stuck in a synchronous barrier without making progress.
- **Mean Simulated Time:** The virtual clock units elapsed before completion.
- **Mean Messages Dispatched:** Total packet volume sent. Comparing Mode C to Mode A illustrates the **message overhead** of resilience.
- **McNemar Test p-value:** In the Research Analytics page, evaluates whether the improvement of Mode C over baseline is statistically significant ($p < 0.05$).

---

## 14. Exporting and Analyzing Data

1. On the **Research Analytics** or **History** page, click **Export CSV**.
2. CSV files include formula-injection sanitization (prepended single-quotes on leading `=`, `+`, `-`, `@`), explicit unit headers (`simulated_time_virtual_units`), sample size $n$, and code version tags.
3. Open files in Excel, Python/Pandas, or R for external statistical auditing.

---

## 15. Running Automated Tests

Run the full automated test suite (backend pytest + frontend vitest):
```powershell
.\scripts\run-tests.ps1
```

*Direct backend test command:*
```powershell
.\.venv\Scripts\python.exe -m pytest -v backend\tests
```

*Direct frontend test command:*
```powershell
cd frontend; npm test; cd ..
```

---

## 16. Troubleshooting Guide

- **Port 8000 or 5173 Already in Use:**
  Run `netstat -ano | findstr :8000` to find the conflicting PID, then terminate it with `Stop-Process -Id <PID> -Force`.
- **PowerShell Execution Policy Error:**
  Run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`.
- **SQLite Database Locked:**
  The backend configures `PRAGMA busy_timeout=10000` and WAL mode. If locked by an external SQLite browser, close the browser tool.
- **WebSocket Disconnects:**
  The frontend hook includes automatic exponential reconnection and sequence-based event replay. Disconnects do not interrupt background simulations.

---

## 17. Platform Limitations & Prerequisites for Formal Research Claims

Before making academic claims or submitting a research paper based on this platform:
1. **Increase Sample Sizes:** Expand from 30 seeds to 100+ seeds per cell for narrower confidence intervals.
2. **Benchmark Diversity:** Add a second problem family (e.g., distributed resource allocation) beyond graph coloring.
3. **Physical Network Validation:** Validate findings over physical network interfaces using UDP or distributed containers.
4. **LLM Cost & Rate Limit Management:** Conduct dedicated LLM agent runs with formal token and cost accounting.
