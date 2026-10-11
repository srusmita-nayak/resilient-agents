# Platform Architecture Specification

## 1. System Overview

The Resilient Agents Research Platform investigates multi-agent distributed coordination over unreliable, lossy, and partitioned communication networks. It implements a discrete-event simulation kernel with a virtual clock, enabling deterministic and reproducible evaluation of communication protocols across identical problem seeds.

```
+---------------------------------------------------------------------------------+
|                                React Frontend                                   |
|   - Overview Dashboard    - Multi-Agent Workspace (SVG)  - Experiment Lab      |
|   - Middleware Inspector  - Research Analytics (Recharts) - Protocol Docs      |
+---------------------------------------------------------------------------------+
                                      | ^
                    REST API (HTTP)   | |  WebSocket Event Stream (/ws/events)
                                      v |
+---------------------------------------------------------------------------------+
|                             FastAPI Backend Service                             |
|  +---------------------------+  +--------------------------------------------+  |
|  |     REST / WS Routers     |  |       Experiment Orchestrator (Worker)     |  |
|  +---------------------------+  +--------------------------------------------+  |
|               |                                       |                         |
|               v                                       v                         |
|  +---------------------------------------------------------------------------+  |
|  |                    Discrete-Event Simulation Kernel                       |  |
|  |   - Virtual Clock Scheduler (heapq priority queue)                        |  |
|  |   - Seeded Fault Injector (Packet Loss, Jitter, Duplicates, Partitions)   |  |
|  |   - Virtual Software Channel (Message Interception & Event Logging)       |  |
|  +---------------------------------------------------------------------------+  |
|                                       |                                         |
|                                       v                                         |
|  +---------------------------------------------------------------------------+  |
|  |                           Protocol Middleware Layer                       |  |
|  |   - Mode A: Strict Synchronous Round Barrier (Baseline)                   |  |
|  |   - Mode B: Barrier Timeout Skipping Silent Peers (Timeout Baseline)      |  |
|  |   - Mode C: Protected Middleware (ACKs, Retries, Monotonic Versions, Sync)|  |
|  +---------------------------------------------------------------------------+  |
|                                       |                                         |
|                                       v                                         |
|  +---------------------------------------------------------------------------+  |
|  |                      Distributed Agents & Problem Domain                  |  |
|  |   - Distributed Graph Coloring (Planted Solvable Benchmark)               |  |
|  |   - Decision Policies: Min-Conflict DSA / Gemini LLM Adapter              |  |
|  |   - Independent Mathematical Solution Validator                           |  |
|  +---------------------------------------------------------------------------+  |
+---------------------------------------------------------------------------------+
                                       |
                                       v
+---------------------------------------------------------------------------------+
|                             SQLite WAL Database                              |
|   - experiments (config, seeds, status, audit info)                             |
|   - runs (seed, mode, outcome, simulated time, wall ms, metrics summary)        |
|   - events (seq, type, sim_time, agent, payload)                                |
|   - llm_calls (prompt hash, tokens, latency, fallback flag, error class)        |
+---------------------------------------------------------------------------------+
```

## 2. Core Modules

### 2.1 Virtual Clock & Discrete-Event Scheduler (`app/core/clock.py`)
All simulation events (message dispatches, network delays, ACK timeouts, barrier checks) are scheduled in a priority queue sorted by virtual timestamp. The simulation clock advances instantaneously to the next scheduled event timestamp, allowing thousand-packet executions to complete in milliseconds of physical wall-clock time while preserving precise temporal ordering.

### 2.2 Fault Injection Engine (`app/core/faults.py`)
Applies deterministic network faults driven by a seeded pseudo-random number generator (PRNG):
- **Packet Loss:** Drops messages based on a configured probability $p_{loss} \in [0, 1]$.
- **Latency & Jitter:** Simulates propagation delay ($t_{lat} \pm t_{jitter}$).
- **Reordering:** Injects extra delay on selected packets, allowing subsequent messages to arrive earlier.
- **Packet Duplication:** Dispatches duplicate copies of packets at slight temporal offsets.
- **Network Partitions:** Enforces time windows $[t_{start}, t_{start} + \Delta t]$ during which all traffic between partitioned agents is blocked.

### 2.3 Distributed Graph Coloring Benchmark (`app/problems/graph_coloring.py`)
A distributed constraint reasoning (DCR) benchmark where:
1. A graph $G = (V, E)$ is generated from a seed with a known planted coloring, guaranteeing mathematical solvability with $K$ colors.
2. Nodes are partitioned across $N$ agents. Agent $i$ is the authoritative single writer for its subset of nodes.
3. Edges spanning distinct agents represent boundary constraints requiring communication.
4. An **Independent Validator** (`app/problems/validator.py`), completely decoupled from agent code, evaluates the final global assignment.

### 2.4 Agent Decision Engine (`app/agents/`)
- **Deterministic Min-Conflict DSA:** Evaluates candidate colors for owned nodes to minimize constraint violations with boundary neighbors, switching with move probability $p_{move}$.
- **LLM Adapter (Gemini):** Formats boundary constraint context into structured JSON prompts. Implements strict call budgets and automatically falls back to deterministic min-conflict on rate limits, timeouts, or invalid JSON.

### 2.5 Data Persistence & Startup Reconciliation (`app/db/`)
Utilizes SQLite configured in Write-Ahead Logging (WAL) mode with foreign keys enabled.
- **Server Restart Reconciliation:** Upon startup, any run or experiment remaining in `running` or `queued` state is transitioned to `interrupted`, guaranteeing that incomplete runs are never counted as successful.
