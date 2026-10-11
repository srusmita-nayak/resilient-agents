# Complete Research Project Guide: Fault-Tolerant Multi-Agent Coordination

**Platform Title:** Fault-Tolerant Multi-Agent Coordination: A Communication-Aware Protocol for Resilient LLM Workflows  
**Codebase Location:** `C:\Users\ADMIN\Desktop\rmipr\resilient-agents`  
**Target Audience:** Students, Researchers, Software Engineers, and Academic Evaluators (Viva/Defense Preparation)  
**Document Classification:** Ground-Truth System Reference & Architectural Manual  

---

## Table of Contents
1. [Introduction & Executive Summary](#1-introduction--executive-summary)
2. [Core Concepts Explained from Scratch](#2-core-concepts-explained-from-scratch)
3. [The Benchmark Task: Distributed Graph Colouring](#3-the-benchmark-task-distributed-graph-colouring)
4. [The Multi-Agent System Architecture](#4-the-multi-agent-system-architecture)
5. [The Simulated Channel & Fault Injection Engine](#5-the-simulated-channel--fault-injection-engine)
6. [The Three Protocol Modes (A, B, and C)](#6-the-three-protocol-modes-a-b-and-c)
7. [The Protected Middleware: Mechanism & State Machine](#7-the-protected-middleware-mechanism--state-machine)
8. [Complete Research Dashboard Tour (Every Page & Control)](#8-complete-research-dashboard-tour-every-page--control)
9. [Detailed Walkthrough: Multi-Agent Topology Canvas & Event 22](#9-detailed-walkthrough-multi-agent-topology-canvas--event-22)
10. [End-to-End System Execution Flow](#10-end-to-end-system-execution-flow)
11. [Taxonomy of All Simulation Outcomes & Termination States](#11-taxonomy-of-all-simulation-outcomes--termination-states)
12. [Empirical Research Evaluation & Scientific Defense](#12-empirical-research-evaluation--scientific-defense)
13. [5-Minute Professor Demonstration Script](#13-5-minute-professor-demonstration-script)
14. [Comprehensive Technical Glossary](#14-comprehensive-technical-glossary)
15. [Limitations, Disclosures & Threats to Validity](#15-limitations-disclosures--threats-to-validity)

---

## 1. Introduction & Executive Summary

### 1.1 What This Project Is in Plain Words
When software agents (whether running rule-based algorithms or Large Language Models) collaborate across multiple machines to solve a problem, they do so by exchanging messages across a network. Standard multi-agent frameworks—such as AutoGen, CrewAI, LangGraph, and ChatDev—operate under an implicit assumption: **they assume the network is reliable**. They assume that every message dispatched by Agent A will arrive at Agent B promptly, in the correct order, and without duplicate copies or dropouts.

In reality, real-world edge networks, wireless channels, satellite links, and congested cloud backbones suffer from **packet drops**, **erratic latency (jitter)**, **out-of-order deliveries**, and **temporary network partitions**. When an unassisted multi-agent workflow encounters these communication faults, two severe failure modes emerge:
1. **Deadlock / Hanging:** Agents wait forever at synchronous round barriers for messages that were lost in transit.
2. **State Divergence / Invalidation:** Agents make recoloring decisions based on outdated, missing, or scrambled constraint data, producing invalid final outcomes.

This project implements and evaluates a **communication-aware distributed coordination protocol (Protected Middleware, Mode C)** designed to give multi-agent workflows fault resilience. Using **Distributed Graph Colouring (DCR)** as an objectively verifiable mathematical benchmark, the platform systematically compares three coordination strategies under identical, seeded network faults:
- **Mode A (Strict Synchronous Baseline):** Traditional round barriers; agents wait indefinitely for peer arrivals.
- **Mode B (Timeout Baseline):** Synchronous barriers equipped with static timeouts that skip unresponsive peers.
- **Mode C (Protected Middleware):** A communication-aware state machine providing bounded exponential backoff retries, explicit Acknowledgments (ACKs), duplicate suppression, monotonic version tracking, authoritative state snapshots, and partition reconciliation.

### 1.2 The 5-Line "Project in One Minute" Summary
- **Problem:** Unreliable network channels cause distributed multi-agent reasoning to deadlock or produce invalid solutions.
- **Benchmark:** Distributed Graph Colouring with mathematically planted zero-conflict solutions verified by an isolated checker.
- **Solution:** A protected middleware layer (Mode C) managing acknowledgments, exponential retries, monotonic versions, and snapshot healing.
- **Experimental Rigor:** 600 total database runs across 5 pre-configured 30-seed empirical sweeps comparing Modes A, B, and C under identical seeds.
- **Finding:** Protected Mode C eliminates deadlocks (0 deadlocks across all loss rates) and achieves up to 93.3% valid solutions under 50% packet loss where Mode A collapses to 3.3%, while incurring an empirical 2.0x to 5.4x message overhead.

### 1.3 Everyday Analogy
> **Analogy: The Dinner Party Seating Committee**  
> Imagine three event planners—Alice, Bob, and Charlie—stationed in different offices trying to seat guests at wedding tables such that feuding relatives never sit next to each other. Every ten minutes (a "round"), each planner writes their updated seating assignments on a postcard and mails it to the other two via an unreliable postal courier.  
> - **In Mode A (Strict Baseline):** Alice refuses to pick up her pen for Round 2 until she holds postcards from both Bob and Charlie. If Charlie's postcard is lost in the rain, Alice sits frozen at her desk forever. The entire wedding planning freezes (**Deadlock**).  
> - **In Mode B (Timeout Baseline):** Alice sets a 15-minute kitchen timer. If Charlie's postcard hasn't arrived when the timer rings, Alice shrugs, assumes Charlie hasn't changed anything, and assigns seats anyway. She avoids freezing, but if Charlie actually made critical changes that were lost in transit, Alice might place two arch-rivals at the same table (**Constraint Conflict**).  
> - **In Mode C (Protected Protocol):** Each postcard has a stamped sequence number. When Bob receives Alice's card, he immediately sends back a quick receipt slip ("I received Card #4"). If Alice doesn't get Bob's receipt slip within 3 minutes, she mails another copy with exponential patience. When Bob receives a duplicate, he checks the stamp and discards the spare. If the courier road is blocked for an hour, Alice and Bob reconcile their master guestbooks using authoritative snapshot summaries the moment the road reopens.

---

## 2. Core Concepts Explained from Scratch

Every technical term utilized throughout this codebase is defined below in plain, concrete language:

### 2.1 Agent
An independent software process responsible for making local decisions over a subset of problem variables. In this codebase ([backend/app/agents/base.py](file:///c:/Users/ADMIN/Desktop/rmipr/resilient-agents/backend/app/agents/base.py)), each agent owns a assigned set of graph nodes, maintains internal beliefs about its neighbors' colors, and executes a decision policy each round.

### 2.2 Multi-Agent System (MAS)
A system where multiple autonomous agents interact to solve a global task that no single agent has the complete information or authority to solve alone. Knowledge is decentralized: Agent 0 does not know the internal connections of Agent 1.

### 2.3 Message
A structured JSON-serialized datagram ([backend/app/core/messages.py](file:///c:/Users/ADMIN/Desktop/rmipr/resilient-agents/backend/app/core/messages.py)) transmitted over the channel. Every message carries a unique `msg_id`, protocol `kind` (`DATA`, `ACK`, `SYNC_REQ`, `SYNC_RESP`), `sender`, `receiver`, simulation `round`, `attempt` counter, and a `payload`.

### 2.4 Network Fault
A software-emulated communication impairment introduced between agents by the `FaultInjector` ([backend/app/core/faults.py](file:///c:/Users/ADMIN/Desktop/rmipr/resilient-agents/backend/app/core/faults.py)):
- **Packet Loss (`loss_rate`):** A message is permanently destroyed in transit and never delivered.
- **Latency & Jitter (`min_latency`, `max_latency`, `jitter`):** Delivery delay in virtual simulation units, randomized around a base duration.
- **Reordering (`reorder_rate`):** Message 2 arrives before Message 1 due to varied channel delays.
- **Duplicates (`duplicate_rate`):** A single dispatched packet generates two delivery events.
- **Network Partition (`partitions`):** Complete communication blackout across specified agent subsets during an explicit time window $[t_{start}, t_{start} + \text{duration}]$.

### 2.5 Acknowledgment (ACK)
A lightweight confirmation message sent by a receiver back to the original sender upon message receipt. It contains `corr_id` matching the original message's `msg_id`, confirming delivery to the sender.

### 2.6 Timeout
A countdown timer after which an agent stops waiting for an event. In Mode B, reaching the `barrier_timeout` forces the agent to proceed to the next round. In Mode C, reaching the `ack_timeout` triggers a packet retransmission.

### 2.7 Retransmission and Exponential Backoff
When an expected ACK is not received before `ack_timeout`, the sender re-dispatches the packet. To prevent clogging a congested network, each retry multiplies the waiting period by a `backoff_factor` (default: 1.5):
$$\text{Timeout}_{\text{attempt } k} = \text{ack\_timeout} \times (\text{backoff\_factor})^{k-1}$$

### 2.8 Duplicate Suppression
When duplicate packets arrive (from network replication or late retries), the receiver inspects a history of recently seen `msg_id`s. If already processed, the duplicate packet is discarded to prevent repeating old state transitions.

### 2.9 Stale Information & Monotonic Versioning
If Agent 0 colors Node 3 red at Round 1, and changes it to blue at Round 2, but the Round 1 packet was delayed and arrives after Round 2, the receiver might mistakenly revert Node 3 to red. To prevent this, every node state update carries an incrementing integer version number $v$. Receivers reject any incoming update where $v_{\text{incoming}} \le v_{\text{current}}$.

### 2.10 Synchronization / State Snapshot
When a network partition ends, agents may have diverged significantly. Mode C executes a post-partition reconciliation handshake: the coordinator broadcasts a `SYNC_REQ`, each peer responds with a `SYNC_RESP` containing an authoritative snapshot of its owned boundary nodes, and all peers update to the highest version of each node.

### 2.11 Deadlock and Stall
- **Deadlock:** A state where all pending agents are blocked waiting for messages, and the event queue is completely empty. The simulation cannot make progress.
- **Stall:** An individual agent is stuck waiting at a synchronization barrier while other agents have terminated.

### 2.12 Round-Based Coordination & Barrier
Simulations proceed in discrete steps called **rounds**. In synchronous designs, a round barrier requires an agent to collect messages from all known peers before evaluating constraints and advancing to round $r+1$.

### 2.13 Discrete-Event Simulation & Virtual Time ($u$)
Rather than sleeping physical CPU seconds, time is represented as an advancing numeric scalar $t$ measured in **virtual simulation units ($u$)** managed by a heap-based priority queue ([backend/app/core/clock.py](file:///c:/Users/ADMIN/Desktop/rmipr/resilient-agents/backend/app/core/clock.py)). One unit ($1.0u$) corresponds to the nominal duration of a round. This allows thousands of simulated network seconds to execute in milliseconds of wall-clock time with 100% mathematical determinism.

### 2.14 PRNG Seed and Reproducibility
Every pseudo-random number generator (in graph generation, policy decisions, and fault injection) is initialized with an explicit integer `seed` (e.g., 42..71). Given the same seed and parameters, execution produces an identical sequence of events down to the microsecond.

### 2.15 Independent Validator
An isolated verification module ([backend/app/problems/validator.py](file:///c:/Users/ADMIN/Desktop/rmipr/resilient-agents/backend/app/problems/validator.py)) that inspects the final global assignment after simulation termination. It has zero dependencies on agents or middleware, counting edge conflicts directly:
$$\text{is\_valid} = (\text{violations\_count} == 0) \land (\text{all nodes assigned}) \land (\text{colors} \in [0, k-1])$$

### 2.16 Deterministic vs. LLM Agents
- **Deterministic Agents:** Use the Distributed Stochastic Algorithm (DSA-B / min-conflict heuristic) with seeded random numbers. Fast, mathematically predictable, and reproducible.
- **LLM Agents:** Decisions are queried from a Large Language Model (e.g., Google Gemini 2.5 Flash via REST API) or a scriptable mock provider.

---

## 3. The Benchmark Task: Distributed Graph Colouring

### 3.1 Why Distributed Graph Colouring (DCR)?
Distributed Constraint Reasoning over Graph Colouring was selected because:
1. **NP-Complete Problem:** Solving a graph coloring instance requires non-trivial constraint negotiation.
2. **Objective Ground-Truth Verification:** Unlike natural language chat where quality is subjective, graph coloring has an undeniable binary mathematical criterion: either an edge connects two nodes of the same color (conflict), or it does not.
3. **Decentralized Structure:** By partitioning the graph across agents, inter-agent communication is strictly required along **boundary edges**. Agents cannot verify boundary constraints without exchanging network packets.

```
       [AGENT 0]                    [AGENT 1]
    (Node 0)---(Node 1)          (Node 4)---(Node 5)
       \         /                  \         /
        (Node 2)=====================(Node 3)
                   BOUNDARY EDGE (2 - 3)
                   Requires Network Messages!
```

### 3.2 Planted Graph Generation
To guarantee that failure to solve a graph is caused by communication faults rather than mathematical insolvability, the generator ([backend/app/problems/graph_coloring.py](file:///c:/Users/ADMIN/Desktop/rmipr/resilient-agents/backend/app/problems/graph_coloring.py)) plants a valid $k$-coloring into the graph before adding random edges that respect the planted colors.

### 3.3 Difficulty Presets
| Preset | Agents ($N$) | Nodes ($V$) | Colors ($k$) | Edge Density | Round Budget | Description |
|---|---|---|---|---|---|---|
| **Easy** | 3 | 12 | 3 | 0.25 | 25 | Standard benchmark for loss and partition sweeps. |
| **Medium**| 4 | 20 | 3 | 0.35 | 30 | Increased boundary density across 4 agents. |
| **Hard** | 5 | 35 | 4 | 0.50 | 40 | Dense graph calibrated to test computational and timeout limits. |

---

## 4. The Multi-Agent System Architecture

### 4.1 Agent Roles and State
Implemented in [backend/app/agents/base.py](file:///c:/Users/ADMIN/Desktop/rmipr/resilient-agents/backend/app/agents/base.py):
- **Coordinator (`Agent 0`):** Special role responsible for orchestrating global barrier checks, round synchronization broadcasts, and initiating post-partition reconciliation handshakes (`SYNC_REQ`).
- **Solvers (`Agent 1`, `Agent 2`, etc.):** Worker agents that maintain local node colors, evaluate boundary constraints, propose new colors, and respond to sync requests (`SYNC_RESP`).

### 4.2 State Maintained by Each Agent
```python
agent_id: str                      # "agent_0", "agent_1", etc.
role: str                          # "coordinator" or "solver"
owned_nodes: List[int]             # Nodes this agent has authority to recolor
current_colors: Dict[int, int]     # node_id -> integer color
versions: Dict[int, int]           # node_id -> integer version (incremented on recolor)
neighbor_colors: Dict[int, int]    # neighbor_node_id -> last received color
neighbor_versions: Dict[int, int]  # neighbor_node_id -> last received version
peers: List[str]                   # List of connected agent IDs
round: int                         # Current local round counter
```

### 4.3 Decision Policy: DSA-B Min-Conflict Algorithm
Implemented in `DeterministicPolicy` ([backend/app/agents/policies.py](file:///c:/Users/ADMIN/Desktop/rmipr/resilient-agents/backend/app/agents/policies.py#L42)):
1. Inspects all owned nodes. For each node, counts edge conflicts against internal and neighbor colors.
2. If conflicts exist, evaluates all candidate colors in $[0, k-1]$ to find the color that minimizes conflicts.
3. If a strictly better color exists, the agent adopts the new color with probability $p = \text{move\_probability}$ (default: 0.8). Stochastically gating moves prevents oscillating color cycles between adjacent agents.

---

## 5. The Simulated Channel & Fault Injection Engine

### 5.1 Software-Emulated Virtual Channel
All message delivery is orchestrated by `VirtualChannel` ([backend/app/core/channel.py](file:///c:/Users/ADMIN/Desktop/rmipr/resilient-agents/backend/app/core/channel.py)) running on the `DiscreteEventScheduler` ([backend/app/core/clock.py](file:///c:/Users/ADMIN/Desktop/rmipr/resilient-agents/backend/app/core/clock.py)). Every message sent triggers the following deterministic sequence:

```
[Agent Middleware] ---> channel.send(Message)
                             |
                   1. Record SEND event (t = scheduler.now)
                             |
                   2. should_drop()? (loss_rate / partition check)
                        |              |
                      [YES]          [NO]
                        |              |
                   Record DROP    3. Calculate latency + jitter
                     Return            |
                                  4. should_reorder()? -> add extra delay
                                       |
                                  5. should_duplicate()? -> schedule duplicate arrival
                                       |
                                  6. scheduler.schedule(delay, _deliver, Message)
                                       |
                          (Virtual clock advances to t + delay)
                                       |
                                  7. Record DELIVER event
                                  8. target_middleware.handle_message(Message)
```

### 5.2 Real Localhost UDP Transport Status
In addition to the virtual discrete-event channel, this codebase includes a functional physical UDP socket transport implementation located at [backend/app/core/transport_udp.py](file:///c:/Users/ADMIN/Desktop/rmipr/resilient-agents/backend/app/core/transport_udp.py).
- **Implementation:** Provides `UDPTransportEndpoint` and `UDPChannelManager`, binding to localhost (`127.0.0.1`) UDP sockets with background receiver threads, datagram serialization, and physical socket dispatch latency tracking.
- **Verification:** Verified by 5 dedicated unit tests in [backend/tests/test_transport_udp.py](file:///c:/Users/ADMIN/Desktop/rmipr/resilient-agents/backend/tests/test_transport_udp.py).
- **Scope Disclosure:** All 600 multi-seed research sweeps were executed over the discrete-event `VirtualChannel` to ensure microsecond determinism across seeds. The UDP transport is a standalone single-host loopback implementation; multi-machine distributed container deployments over real physical networks remain future work.

---

## 6. The Three Execution Modes (A, B, and C)

The platform evaluates three communication paradigms across identical seeds:

### 6.1 Architectural Comparison Table
| Feature / Behavior | Mode A: Strict Baseline | Mode B: Timeout Baseline | Mode C: Protected Middleware |
|---|---|---|---|
| **Implementing File** | [baseline.py](file:///c:/Users/ADMIN/Desktop/rmipr/resilient-agents/backend/app/middleware/baseline.py) | [timeout_baseline.py](file:///c:/Users/ADMIN/Desktop/rmipr/resilient-agents/backend/app/middleware/timeout_baseline.py) | [protected.py](file:///c:/Users/ADMIN/Desktop/rmipr/resilient-agents/backend/app/middleware/protected.py) |
| **Round Barrier Handling** | Waits indefinitely for all peers | Drops barrier after `barrier_timeout` | Waits with retry state machine until `round_barrier_timeout` |
| **Lost Packet Behavior** | **Deadlocks / stalls** on round 0/1 | Ignores missing peer; advances round | **Retransmits with exponential backoff** |
| **Acknowledgment (ACK)** | None | None | **Explicit ACK** for every data message |
| **Retransmissions** | None | None | Up to `max_retries` (default: 3 or 4) |
| **Duplicate Handling** | Overwrites state with duplicate | Overwrites state with duplicate | **Suppressed** via `seen_msg_ids` cache |
| **Stale Update Handling** | Applies stale data unconditionally | Applies stale data unconditionally | **Rejected** if $v_{\text{incoming}} \le v_{\text{current}}$ |
| **Partition Healing** | Permanently deadlocks | Desynchronizes state permanently | **Reconciles** via `SYNC_REQ` / `SYNC_RESP` snapshots |
| **Message Overhead** | $1.0\times$ (minimal, baseline) | $1.0\times$ (minimal, baseline) | **$2.0\times$ to $5.4\times$** (explicit ACKs & retries) |

### 6.2 The Fault-Free Reference Run
Every experiment seed executes a **Fault-Free Reference Run** alongside Modes A, B, and C:
- **Definition:** Executes Mode A under 0% loss, 0 jitter, and fixed $1.0u$ latency.
- **Purpose:** Identifies whether an algorithmic failure is caused by an intrinsic solver limitation (e.g., local minima in min-conflict) or by communication damage. In the analytics dashboard, the **Paired Seeds (Filtered)** toggle uses the fault-free reference to filter out instances that were insolvable even under perfect communication.

---

## 7. The Protected Middleware: Mechanism & State Machine

### 7.1 Message Protocol Schema
Every message in Mode C conforms to the Pydantic schema in [backend/app/core/messages.py](file:///c:/Users/ADMIN/Desktop/rmipr/resilient-agents/backend/app/core/messages.py):
```json
{
  "msg_id": "msg_agent_0_1_agent_2_a4b9c1",
  "kind": "DATA",
  "sender": "agent_0",
  "receiver": "agent_2",
  "task_id": "task_42",
  "run_id": "run_exp_loss_25_30_42_protected",
  "round": 1,
  "payload": {
    "boundary_colors": {"2": 1},
    "boundary_versions": {"2": 3}
  },
  "corr_id": null,
  "attempt": 1,
  "sent_at": 14.5,
  "schema_version": "1.0"
}
```

### 7.2 Text/ASCII Protocol State Machine
```
   [INIT / NEW ROUND]
           |
     dispatch_round_data()
           |
           v
  +-----------------+        Packet Lost / Dropped
  |  WAITING_FOR_   | -------------------------------------+
  |      ACKS       |                                      |
  +-----------------+                                      |
     |           ^                                         |
     | ACK Recv  | Timer Expires                           v
     |           | (attempt <= max_retries)        +---------------+
     |           +-- retransmit_with_backoff() --- | ACK_TIMEOUT   |
     v                                             +---------------+
  [All ACKs Recv]                                          |
     |                                                     | attempt > max_retries
     v                                                     v
  +-----------------+                             +-----------------+
  | WAITING_FOR_    |                             | DEGRADED_MODE   |
  | ROUND_MESSAGES  | <-------------------------- | (Log Warning)   |
  +-----------------+                             +-----------------+
     |
     | All peer updates received OR round_barrier_timeout
     v
  [ADVANCE TO ROUND r+1]
```

### 7.3 Post-Partition State Reconciliation Handshake
When a partition ends or multiple retries fail, agents reconcile boundary variables:
1. Coordinator dispatches `SYNC_REQ` with its current boundary snapshot.
2. Receiver validates snapshot, responds with `SYNC_RESP` containing its authoritative `(color, version)` pairs.
3. Both peers execute monotonic merge: `color[n] = incoming_color` if and only if `incoming_version > local_version`.

### 7.4 Protocol Guarantees vs. Non-Guarantees
- **Guarantee:** **At-Most-Once Application**. A message payload is never applied twice to node states due to monotonic version checking and message ID deduplication.
- **Guarantee:** **Stale Invalidation Freedom**. An older recoloring decision can never overwrite a newer recoloring decision regardless of channel reordering.
- **NON-Guarantee:** **No Exactly-Once Delivery Claim**. If a network partition exceeds the complete retry budget, delivery is not guaranteed. Mode C degrades gracefully to prevent deadlock rather than asserting impossible distributed consensus over lossy channels.

---

## 8. Complete Research Dashboard Tour (Every Page & Control)

The frontend is a dark-mode scientific research interface built with React 18, Tailwind CSS, Lucide icons, and Recharts ([frontend/src/pages/](file:///c:/Users/ADMIN/Desktop/rmipr/resilient-agents/frontend/src/pages)).

```
+---------------------------------------------------------------------------------------------------+
|  [SHIELD] RESILIENT AGENTS LAB   [PULSE] Connected   [DB] WAL Active   [TIME] 11:26 AM            |
|  [Overview]  [Workspace]  [Experiment Lab]  [Inspector]  [Analytics]  [History]  [Architecture]   |
+---------------------------------------------------------------------------------------------------+
```

### 8.1 Header & System Status Indicator
- **System Indicator Badge:** Displays `System Healthy` (green dot) or `Degraded` (red dot), polling `/api/health` every 10 seconds.
- **Storage Stat Badge:** Displays database size in MB and active WAL mode.
- **Navigation Tabs:** Direct links to the 7 platform pages.

---

### 8.2 Page 1: Research Overview (`/`)
Implemented in [OverviewPage.tsx](file:///c:/Users/ADMIN/Desktop/rmipr/resilient-agents/frontend/src/pages/OverviewPage.tsx):
- **Hero Banner:** States the research objective and provides quick-start buttons to the Lab and Analytics.
- **Metric Cards (Row of 4):**
  1. *Valid Solution Rate:* Percentage of runs in the latest substantive experiment that passed independent verification with 0 conflicts.
  2. *Deadlock / Stall Rate:* Percentage of runs that terminated in `deadlock` or `stall`.
  3. *Latest Experiment:* Name, agent type (`DETERMINISTIC`), and status of the current sweep.
  4. *Database Storage:* Current SQLite file size on disk (e.g., `215.8 MB`), total completed runs, and total recorded events.
- **Latest Experiment Breakdown Table:** Lists the runs of the current experiment, showing Run ID, Mode, Seed, Status, Outcome, Violations, Sim Time ($u$), and Wall Time (ms).

---

### 8.3 Page 2: Multi-Agent Workspace (`/workspace`)
Implemented in [WorkspacePage.tsx](file:///c:/Users/ADMIN/Desktop/rmipr/resilient-agents/frontend/src/pages/WorkspacePage.tsx):
- **Mode Toggle:** Switch between `Replay Stored Run` (queries recorded events from SQLite) and `Live Monitor` (streams live runs via WebSocket).
- **Experiment & Run Selectors:** Dropdowns to pick any experiment and individual run to inspect.
- **Playback Controls:** `Reset` (rewind to event 1), `Play / Pause`, and `Speed Multiplier` ($1\times, 2\times, 5\times$).
- **SVG Multi-Agent Topology Canvas:** Interactive 2D visualization of agent nodes and communication packets. (Fully detailed in Section 9).
- **Scrubber Slider:** Drag slider to scrub backwards and forwards through simulation virtual time event-by-event.
- **Event Timeline Drawer:** Chronological event feed with event type filter tabs (`ALL`, `SEND`, `DELIVER`, `DROP`, `RETRY`, `ACK_RECEIVED`, `DEADLOCK`, `VALIDATION`).

---

### 8.4 Page 3: Experiment Lab (`/lab`)
Implemented in [ExperimentLabPage.tsx](file:///c:/Users/ADMIN/Desktop/rmipr/resilient-agents/frontend/src/pages/ExperimentLabPage.tsx):
Configure and launch experiments.
#### Form Fields & Allowed Ranges:
1. **Experiment Name:** Text string (default: `"Resilience Evaluation Sweep"`).
2. **Agent Engine (`agent_type`):** Toggle between `Deterministic` (DSA-B heuristic) and `LLM` (Google Gemini REST / Mock).
3. **Difficulty Preset:** Buttons for `Easy` (12 nodes, 3 agents, $k=3$), `Medium` (20 nodes, 4 agents, $k=3$), and `Hard` (35 nodes, 5 agents, $k=4$).
4. **Number of Agents:** Range: 2 to 10 (default: 3).
5. **Number of Nodes:** Range: 6 to 100 (default: 12).
6. **Colors ($k$):** Range: 2 to 6 (default: 3).
7. **Round Budget:** Range: 5 to 100 rounds (default: 25).
8. **Fault Preset:** Quick buttons: `Reliable` (0% loss), `Lossy Medium` (25% loss), `Severe Loss` (50% loss), `Partition Burst`.
9. **Loss Rate (`loss_rate`):** Slider from 0.0 to 0.90 (0% to 90% packet drop).
10. **Min / Max Latency:** Sliders from 0.1 to 10.0 virtual units.
11. **Jitter:** Slider from 0.0 to 5.0 virtual units.
12. **Duplicate Rate / Reorder Rate:** Sliders from 0.0 to 0.50.
13. **Enable Partition Toggle:** Enables temporary network partition burst.
14. **ACK Timeout:** Range: 0.5 to 10.0 virtual units (default: 3.0).
15. **Max Retries:** Range: 0 to 10 attempts (default: 3 or 4).
16. **Backoff Factor:** Range: 1.0 to 3.0 (default: 1.5).
17. **Barrier Timeout (Mode B):** Range: 1.0 to 30.0 virtual units (default: 8.0).
18. **Round Barrier Timeout (Mode C):** Range: 2.0 to 50.0 virtual units (default: 12.0).
19. **Protocol Modes Checkboxes:** Select any combination of `baseline`, `timeout_baseline`, `protected`.
20. **Seeds Input:** Comma-separated integer seeds (e.g., `"42, 43, 44"`).
21. **Include Fault-Free Reference Toggle:** Generates paired calibration runs.
22. **Action Buttons:** `Launch Experiment Batch` and `Cancel Experiment`.

---

### 8.5 Page 4: Middleware Inspector (`/inspector`)
Implemented in [InspectorPage.tsx](file:///c:/Users/ADMIN/Desktop/rmipr/resilient-agents/frontend/src/pages/InspectorPage.tsx):
Low-level protocol inspection tool:
- **Run Header:** Displays run outcome, termination reason, wall time, simulated time, and validation indicator.
- **Message Lifecycle Inspector:** Input any `msg_id` to view its complete lifecycle chain: `SEND -> DROP -> RETRY -> DELIVER -> ACK_RECEIVED`.
- **Event Audit Log Table:** Full tabular log displaying Sequence (#), Sim Time ($u$), Event Type, Source Agent, Target Agent, Message ID, and JSON payload summary.

---

### 8.6 Page 5: Research Analytics (`/analytics`)
Implemented in [AnalyticsPage.tsx](file:///c:/Users/ADMIN/Desktop/rmipr/resilient-agents/frontend/src/pages/AnalyticsPage.tsx):
Academic visualization and statistical evaluation:
- **Experiment Selector:** Dropdown listing all stored experiments with their total run count (`• 120 runs`).
- **Paired Seeds Toggle (`paired_fault_free_only`):**
  - *All Seeds (Intention-to-Treat):* Evaluates all runs regardless of whether the fault-free reference solved the instance.
  - *Filtered: Solvable Seeds Only:* Filters analysis to seeds where the fault-free reference achieved a valid solution, isolating communication damage from solver limitations.
- **Export CSV Button:** Directly downloads sanitized experimental data from `/api/experiments/{id}/export.csv`.
- **Chart 1: Valid Solution Rate by Protocol Mode (%):**
  - Grouped bar chart comparing Modes A, B, and C.
  - Blue bar: Valid solution percentage ($0\%$ to $100\%$).
  - Red bar: Deadlock / stall percentage ($0\%$ to $100\%$).
  - Tooltip: Displays exact sample size ($n$) and asymmetric **Wilson 95% Confidence Intervals** $[CI_{\text{lower}}, CI_{\text{upper}}]$.
- **Chart 2: Communication Overhead & Message Volume:**
  - Bar chart comparing total messages dispatched per mode, illustrating the cost of reliability.
- **Statistical Significance Matrix Table:**
  - Displays pairwise **McNemar Exact Binomial Tests** ($A \text{ vs } B$, $C \text{ vs } A$, $C \text{ vs } B$).
  - Shows 2x2 contingency table ($a, b, c, d$), paired difference ($\Delta$), exact two-sided $p$-value, and significance badge ($p < 0.05$).
- **Statistical Formulas Reference Card:** Educational tabs explaining Wilson Score intervals, McNemar's paired test, and Bootstrap resampling formulas.

---

### 8.7 Page 6: Experiment History (`/history`)
Implemented in [HistoryPage.tsx](file:///c:/Users/ADMIN/Desktop/rmipr/resilient-agents/frontend/src/pages/HistoryPage.tsx):
- Complete searchable table of all experiments stored in SQLite.
- Columns: ID, Name, Created At, Agent Type, Status, Runs Progress, Configuration Chips.
- Actions:
  - `Export CSV`: Downloads raw experiment data.
  - `Rerun Failed Runs`: Automatically creates a new experiment re-executing only seeds that failed or deadlocked.
  - `Delete`: Deletes the experiment and cascades event records.

---

### 8.8 Page 7: Architecture & Protocol Documentation (`/architecture`)
Implemented in [ArchitecturePage.tsx](file:///c:/Users/ADMIN/Desktop/rmipr/resilient-agents/frontend/src/pages/ArchitecturePage.tsx):
- Interactive system architectural diagram showing Layer 1 (Problems), Layer 2 (Agents), Layer 3 (Middleware), Layer 4 (Channel & Faults), Layer 5 (Storage & API), and Layer 6 (Frontend).
- Formal mathematical specification of Distributed Graph Colouring and the fault injection probability distributions.

---

## 9. Detailed Walkthrough: Multi-Agent Topology Canvas & Event 22

This section breaks down the **Multi-Agent Communication Topology** panel ([WorkspacePage.tsx](file:///c:/Users/ADMIN/Desktop/rmipr/resilient-agents/frontend/src/pages/WorkspacePage.tsx#L210-L315)) and explains the exact stored run featured in the prompt: **`run_exp_loss_25_30_42_baseline`** (Mode A under 25% packet loss on Seed 42).

```
+-----------------------------------------------------------------------------------+
| [LAYERS] MULTI-AGENT COMMUNICATION TOPOLOGY                    Event 22 of 22     |
|                                                                                   |
|                                ( Agent 0 )  (cx: 300, cy: 80, Blue stroke)        |
|                                COORDINATOR                                        |
|                                  /      \                                         |
|                           - - - /        \ - - - (Dashed channel lines)           |
|                                /          \                                       |
|               ( Agent 1 ) - - - - - - - - - - ( Agent 2 )                         |
|               cx: 150, cy: 230                 cx: 450, cy: 230                   |
|               SOLVER (Purple stroke)           SOLVER (Green stroke)              |
|                                                                                   |
| +-------------------------------------------------------------------------------+ |
| | [VALIDATION] agent_id: None -> broadcast                             t=4.3 u  | |
| +-------------------------------------------------------------------------------+ |
| [=== scrubber slider ========================================================O===] |
| Start (t=0.0)                 Scrubber Position: 22 / 22                      End |
+-----------------------------------------------------------------------------------+
```

### 9.1 Visual Element Dictionary
1. **Title and Counter:** `"MULTI-AGENT COMMUNICATION TOPOLOGY"` accompanied by `"Event 22 of 22"`. This indicates that 22 discrete events were recorded during the run, and the scrubber is positioned at the final event.
2. **Three Agent Circles:**
   - **Agent 0 (Top Center):** Positioned at SVG coordinates $(300, 80)$. Strokecolor: Blue (`#3b82f6`). Subtitle: `COORDINATOR`.
   - **Agent 1 (Bottom Left):** Positioned at SVG coordinates $(150, 230)$. Strokecolor: Purple (`#8b5cf6`). Subtitle: `SOLVER`.
   - **Agent 2 (Bottom Right):** Positioned at SVG coordinates $(450, 230)$. Strokecolor: Emerald Green (`#10b981`). Subtitle: `SOLVER`.
   - *Note on Coordinates:* Positions are fixed in the 2D layout to provide a consistent geometric reference frame during playback.
3. **Dashed Channel Edges:** The grey dashed lines (`strokeDasharray="4 4"`, color `#233254`) connect the three agents. They represent physical communication channels between boundary peers.
4. **Bottom Active Event Banner:** Displays:
   - Badge: `[VALIDATION]` (blue badge).
   - Route: `→ broadcast` (Because `agent_id` and `target_agent_id` are `null` for global events, the code renders `currentEvent.agent_id → currentEvent.target_agent_id || 'broadcast'`).
   - Virtual Time: `t=4.3 u` (Rounded from exact virtual clock time `4.294688u`).
5. **Scrubber Slider:** An interactive range slider spanning 0 to 21 (0-indexed). Moving the slider replays the exact state of the multi-agent system at any historical moment.

### 9.2 Event-Type-to-Visual-Effect Mapping
| Event Type | Badge Color | Visual Effect on Topology Canvas | Meaning |
|---|---|---|---|
| `SEND` | Blue (`#3b82f6`) | Blue ping circle near sender node | Message dispatched into channel |
| `DELIVER` | Emerald (`#10b981`) | Target node receives message | Message arrived at recipient |
| `DROP` | Red (`#f43f5e`) | **Red ping circle** near sender | Packet permanently dropped by fault injector |
| `RETRY` | Amber (`#f59e0b`) | Amber pulse on channel edge | Timeout expired; retransmission dispatched |
| `ACK_RECEIVED` | Emerald (`#10b981`) | Green flash on sender | Acknowledgment received; retry canceled |
| `DEADLOCK` | Rose / Red (`#f43f5e`) | Banner alert: Deadlock detected | Event queue empty while agents waiting |
| `VALIDATION` | Blue (`#3b82f6`) | Global validation summary | Mathematical checker evaluated final graph |

### 9.3 Chronological Walkthrough of All 22 Events (`run_exp_loss_25_30_42_baseline`)
Directly queried from the SQLite database:

| Seq | Virtual Time ($t$) | Type | Sender | Target | Details / Payload | What Actually Happened |
|---|---|---|---|---|---|---|
| **1** | $0.0u$ | `SEND` | Agent 0 | Agent 1 | `msg_id: ...d8210a`, Round 0 | Agent 0 dispatches boundary colors to Agent 1. |
| **2** | $0.0u$ | `SEND` | Agent 0 | Agent 2 | `msg_id: ...68a57f`, Round 0 | Agent 0 dispatches boundary colors to Agent 2. |
| **3** | $0.0u$ | `DROP` | Agent 0 | Agent 2 | `reason: loss` | **FAULT:** Packet from Agent 0 to Agent 2 is dropped! |
| **4** | $0.0u$ | `SEND` | Agent 1 | Agent 0 | `msg_id: ...db7545`, Round 0 | Agent 1 dispatches boundary colors to Agent 0. |
| **5** | $0.0u$ | `SEND` | Agent 1 | Agent 2 | `msg_id: ...a47157`, Round 0 | Agent 1 dispatches boundary colors to Agent 2. |
| **6** | $0.0u$ | `DROP` | Agent 1 | Agent 2 | `reason: loss` | **FAULT:** Packet from Agent 1 to Agent 2 is dropped! |
| **7** | $0.0u$ | `SEND` | Agent 2 | Agent 0 | `msg_id: ...6fb04d`, Round 0 | Agent 2 dispatches boundary colors to Agent 0. |
| **8** | $0.0u$ | `SEND` | Agent 2 | Agent 1 | `msg_id: ...108e84`, Round 0 | Agent 2 dispatches boundary colors to Agent 1. |
| **9** | $0.74u$ | `DELIVER` | Agent 2 | Agent 1 | Round 0 data | Agent 1 receives Agent 2's colors. |
| **10**| $0.76u$ | `DELIVER` | Agent 2 | Agent 0 | Round 0 data | Agent 0 receives Agent 2's colors. |
| **11**| $0.81u$ | `DELIVER` | Agent 0 | Agent 1 | Round 0 data | Agent 1 receives Agent 0's colors. |
| **12**| $0.81u$ | `SEND` | Agent 1 | Agent 0 | `msg_id: ...540522`, Round 1 | Agent 1 collected all peer updates; advances to Round 1! |
| **13**| $0.81u$ | `SEND` | Agent 1 | Agent 2 | `msg_id: ...1fd2b9`, Round 1 | Agent 1 dispatches Round 1 colors to Agent 2. |
| **14**| $2.35u$ | `DELIVER` | Agent 1 | Agent 0 | Round 1 data | Agent 0 receives Agent 1's Round 1 data. |
| **15**| $2.41u$ | `DELIVER` | Agent 1 | Agent 0 | Round 0 data | Agent 0 receives Agent 1's Round 0 data (delayed). |
| **16**| $2.41u$ | `SEND` | Agent 0 | Agent 1 | Round 1 data | Agent 0 collected all Round 0 updates; advances to Round 1! |
| **17**| $2.41u$ | `SEND` | Agent 0 | Agent 2 | Round 1 data | Agent 0 dispatches Round 1 colors to Agent 2. |
| **18**| $2.41u$ | `DROP` | Agent 0 | Agent 2 | `reason: loss` | **FAULT:** Packet from Agent 0 to Agent 2 is dropped again! |
| **19**| $2.53u$ | `DELIVER` | Agent 1 | Agent 2 | Round 1 data | Agent 2 receives Round 1 data, but is **still waiting for Round 0!** |
| **20**| $4.29u$ | `DELIVER` | Agent 0 | Agent 1 | Round 1 data | Agent 1 receives Agent 0's Round 1 data. |
| **21**| $4.29u$ | `DEADLOCK`| None | None | `reason: Queue empty while agents pending` | **DEADLOCK:** Agent 2 is frozen waiting for Round 0 data that will never arrive. The event queue is empty! |
| **22**| $4.29u$ | `VALIDATION`| None | None | `is_valid: false, violations: 5` | Independent checker inspects graph: **5 conflicts exist!** Simulation halts. |

### 9.4 How to Explain This Failure to an Examining Professor
> "Professor, this run demonstrates the fundamental vulnerability of unassisted synchronous multi-agent coordination. In Events 3 and 6, network packet loss dropped the Round 0 messages destined for Agent 2. Because Mode A implements a strict barrier with no timeouts or retransmissions, Agent 2 was permanently trapped waiting for Round 0 peer arrivals. Agents 0 and 1 advanced to Round 1, but by $t=4.3u$, all remaining in-flight packets had been delivered and the scheduler queue emptied completely. The system detected a deadlock (Event 21), and the independent mathematical validator recorded 5 edge conflicts (Event 22). Under Mode C, those missing packets would have triggered ACKs and retries, allowing Agent 2 to recover and converge."

---

## 10. End-to-End System Execution Flow

The platform executes a 12-step pipeline from the moment a user clicks **Launch Experiment Batch** until charts render:

```
[1. UI Form: ExperimentLabPage] ---> POST /api/experiments
                                             |
[2. Pydantic Validation: schemas.py] <-------+
                                             |
[3. DB Record: repository.create_experiment]
                                             |
[4. Orchestrator Thread: orchestrator.py] <--+ (Pulls from queue)
                                             |
[5. Planted Problem Generator: graph_coloring.py] (Seeded solvable instance)
                                             |
[6. Agent & Policy Initialization: runner.py] (Deterministic or Gemini LLM)
                                             |
[7. Middleware Wiring: baseline / timeout / protected]
                                             |
[8. Discrete Scheduler Execution Loop: clock.py + channel.py]
      (Simulates virtual time, fault injection, packet drops, retries)
                                             |
[9. Termination & Independent Validation: validator.py]
      (Asserts zero edge conflicts; produces is_valid boolean)
                                             |
[10. Atomic DB Batch Persistence: repository.insert_events_batch]
                                             |
[11. WebSocket Live Broadcast: websocket.py -> useWebSocket.ts]
                                             |
[12. Statistical Derivation & Chart Rendering: statistics.py -> AnalyticsPage.tsx]
      (Computes Wilson Score CIs, McNemar Exact Tests, Bootstrap distributions)
```

---

## 11. Taxonomy of All Simulation Outcomes & Termination States

The platform strictly decouples execution completion from mathematical validity:

| Status (`status`) | Outcome (`outcome`) | Termination Reason (`termination_reason`) | Valid? (`validation_valid`) | How It Happens | Stored Run Example in Database |
|---|---|---|---|---|---|
| `completed` | `valid` | `completed` | **1 (True)** | All agents finished round budget; independent validator confirmed 0 edge conflicts. | `run_exp_reliable_30_42_protected` |
| `completed` | `invalid` | `completed` | **0 (False)** | All rounds finished, but final coloring has $\ge 1$ edge conflicts. | `run_exp_loss_25_30_44_timeout_baseline` |
| `failed` | `incomplete` | `deadlock` | **0 (False)** | Scheduler queue became empty while agents were pending (Mode A loss). | `run_exp_loss_25_30_42_baseline` |
| `failed` | `incomplete` | `stall` | **0 (False)** | One agent hung indefinitely while others terminated. | Handled in `runner.py` stall detector |
| `failed` | `valid` | `time_limit` | **1 (True)** | Virtual time exceeded budget ($400.0u$), but **graph had 0 conflicts when halted**. | `run_exp_hard_difficulty_30_43_protected` |
| `failed` | `invalid` | `time_limit` | **0 (False)** | Virtual time exceeded budget ($400.0u$), and graph had conflicts. | `run_exp_hard_difficulty_30_42_protected` |
| `interrupted` | `interrupted` | `Server restarted` | **0 (False)** | Backend server was restarted while run was in progress; reconciled on startup. | Reconciled via `reconcile_startup_interrupted_runs()` |
| `cancelled` | `cancelled` | `cancelled` | **0 (False)** | User clicked "Cancel Experiment" via UI or API. | Handled in `orchestrator.cancel_experiment()` |

---

## 12. Empirical Research Evaluation & Scientific Defense

### 12.1 Real Database Metrics Summary (Direct Ground Truth)
Every statistic quoted below was queried directly from the SQLite database across the 30 common seeds ($42 \dots 71$):

```
+---------------------------------------------------------------------------------------------------------+
|                                    EMPIRICAL RESULTS COMPARISON TABLE                                   |
+-----------------------------------+----------+-----------+------------+------------+--------------------+
| Experimental Suite                | Metric   | Mode A    | Mode B     | Mode C     | Reference (Fault-  |
|                                   |          | Baseline  | Timeout    | Protected  | Free Baseline)     |
+-----------------------------------+----------+-----------+------------+------------+--------------------+
| 1. Reliable Network               | Valid %  | 90.0%     | 90.0%      | 90.0%      | 90.0% (27/30)      |
|    (0% Loss, 0 Jitter)            | 95% CI   | [74.4,96.5| [74.4,96.5]| [74.4,96.5]| [74.4, 96.5]       |
|                                   | Deadlocks| 0 / 30    | 0 / 30     | 0 / 30     | 0 / 30             |
|                                   | Mean Msgs| 150.0     | 150.0      | 300.0 (2x) | 150.0              |
+-----------------------------------+----------+-----------+------------+------------+--------------------+
| 2. Moderate Packet Loss           | Valid %  | 16.7%     | 93.3%      | 83.3%      | 90.0% (27/30)      |
|    (25% Loss, 0.5u Jitter)        | 95% CI   | [7.3,33.6]| [78.7,98.2]| [66.4,92.7]| [74.4, 96.5]       |
|                                   | Deadlocks| 30 / 30   | 0 / 30     | 0 / 30     | 0 / 30             |
|                                   | Mean Msgs| 9.8       | 150.0      | 712.7      | 150.0              |
+-----------------------------------+----------+-----------+------------+------------+--------------------+
| 3. Severe Packet Loss             | Valid %  | 3.3%      | 86.7%      | 93.3%      | 90.0% (27/30)      |
|    (50% Loss, 0.8u Jitter)        | 95% CI   | [0.6,16.7]| [70.3,94.7]| [78.7,98.2]| [74.4, 96.5]       |
|                                   | Deadlocks| 30 / 30   | 0 / 30     | 0 / 30     | 0 / 30             |
|                                   | Mean Msgs| 7.3       | 150.0      | 815.9      | 150.0              |
+-----------------------------------+----------+-----------+------------+------------+--------------------+
| 4. Network Partition Burst        | Valid %  | 50.0%     | 90.0%      | 90.0%      | 90.0% (27/30)      |
|    (Duration: 15.0u at t=10.0u)   | 95% CI   | [33.2,66.8| [74.4,96.5]| [74.4,96.5]| [74.4, 96.5]       |
|                                   | Deadlocks| 30 / 30   | 0 / 30     | 0 / 30     | 0 / 30             |
|                                   | Mean Msgs| 20.5      | 150.0      | 639.5      | 150.0              |
+-----------------------------------+----------+-----------+------------+------------+--------------------+
| 5. Hard Problem Preset            | Valid %  | 0.0%      | 83.3%      | 83.3%      | 83.3% (25/30)      |
|    (35 Nodes, 5 Agents, k=4)      | 95% CI   | [0.0,11.4]| [66.4,92.7]| [66.4,92.7]| [66.4, 92.7]       |
|                                   | Deadlocks| 30 / 30   | 0 / 30     | 0 / 30     | 0 / 30             |
|                                   | Mean Msgs| 28.5      | 800.0      | 2526.2     | 800.0              |
+-----------------------------------+----------+-----------+------------+------------+--------------------+
```

### 12.2 Pairwise Hypothesis Testing (McNemar's Exact Tests)
- **Severe Loss (50% Loss):**
  - **Mode C vs. Mode A:** $p = 0.000000$ ($p < 10^{-6}$), $\Delta = +90.0\%$, statistically significant. Mode C prevents total collapse.
  - **Mode C vs. Mode B:** $p = 0.500000$, $\Delta = +6.7\%$ (Mode C: 28/30 vs. Mode B: 26/30). Difference is not statistically significant at $\alpha = 0.05$.
- **Moderate Loss (25% Loss):**
  - **Mode C vs. Mode A:** $p = 0.000002$, $\Delta = +66.7\%$, statistically significant.
  - **Mode B vs. Mode A:** $p = 0.000000$, $\Delta = +76.7\%$, statistically significant. Mode B achieved 93.3% by skipping missing peer updates.

### 12.3 Investigation: Why Did Hard Sweep Protected Runs Hit `time_limit`?
In `exp_hard_difficulty_30`, all 30 Mode C runs terminated with `status: 'failed'` and `termination_reason: 'time_limit'`.
- **Root Cause:** In the Hard preset, the round budget is 40 rounds across 5 agents. With `round_barrier_timeout: 16.0u` and backoff retries, the cumulative virtual time required to execute 40 rounds under packet loss exceeded the runner's safety ceiling (`max_sim_time = 400.0u`).
- **Critical Finding:** Even though the simulation halted at $t=400.0u$ due to time limit, **25 out of the 30 runs had already reached a valid zero-conflict coloring** before halting. When compared against Mode B, Mode C solved 4 seeds that Mode B failed, while Mode B solved 4 seeds that Mode C failed ($p = 1.000$, discordant pairs: $b=4, c=4$).

### 12.4 What This Research Proves vs. What It Does NOT Prove
#### What It Proves:
1. **Mode A is completely unviable in lossy environments:** Even a modest 25% packet drop causes 100% deadlock in Mode A.
2. **Mode C completely prevents deadlocks:** Zero runs in Mode C deadlocked across all 600 evaluations.
3. **Reliability incurs quantifiable overhead:** Mode C requires exactly $2.0\times$ messages on reliable channels (due to ACKs) and $4.2\times$ to $5.4\times$ messages under severe loss and partitions.

#### What It Does NOT Prove (Honest Academic Disclosures):
1. **Does not prove LLM performance:** All 600 stored runs used deterministic DSA-B agents. Zero real Gemini API runs exist in the dataset. While the Gemini adapter is implemented and tested, findings cannot be extrapolated to LLM agent reasoning without empirical LLM sweeps.
2. **Does not prove superiority over Mode B in unconstrained DCR:** In simple graph coloring, skipping a missing peer update (Mode B) often allows agents to converge because coloring is an iterative stochastic search. Mode C provides state consistency and ordering guarantees, but in purely stochastic constraint satisfaction, Mode B's lightweight barrier skips were highly competitive.
3. **Does not prove novel distributed algorithms:** ACKs, timeouts, monotonic versions, and snapshots are classic distributed systems techniques established by Lynch (1996) and Yokoo (1998). The contribution is their domain-specific integration into multi-agent coordination protocols.

---

## 13. 5-Minute Professor Demonstration Script

Follow this script during an oral exam or project review:

| Time | Action | What to Show on Screen | What to Say to the Professor |
|---|---|---|---|
| **0:00 - 1:00** | Open `http://localhost:5173/` | Research Overview Dashboard | *"Professor, this research platform investigates how multi-agent coordination survives network packet loss and partitions. Rather than assuming reliable channels, we evaluate three modes against an independent zero-conflict validator."* |
| **1:00 - 2:00** | Click **Analytics** tab | Valid Solution Rate & McNemar Test Matrix | *"Here in Research Analytics across 30 identical seeds, Mode A collapses to 3.3% valid solutions under 50% loss due to deadlocks. Mode C recovers to 93.3% ($p < 10^{-6}$). However, we honestly report that reliability incurs a 5.4x message overhead due to ACKs and retries."* |
| **2:00 - 3:15** | Click **Multi-Agent Workspace** tab | Replay `run_exp_loss_25_30_42_baseline`, move scrubber to Event 22 | *"In this topology playback, you can observe why Mode A fails. At Events 3 and 6, packet loss dropped Round 0 messages to Agent 2. At t=4.3u, the discrete event scheduler emptied while Agent 2 was still waiting. The platform detected a deadlock and recorded 5 edge violations."* |
| **3:15 - 4:15** | Switch dropdown to `run_exp_loss_25_30_42_protected` | Replay Mode C on Seed 42 | *"Under the exact same seed in Mode C, when packets are dropped, you can see amber retry pulses and green ACK confirmations. Agents reconciled their state versions and converged to 0 violations."* |
| **4:15 - 5:00** | Click **Architecture** tab | Layer Diagram & Limitations | *"All 600 sanity runs use deterministic DSA-B agents to guarantee mathematical reproducibility. Real LLM adapters and physical localhost UDP transport are implemented and unit-tested, but full multi-agent LLM sweeps remain future work."* |

---

## 14. Comprehensive Technical Glossary

- **ACK:** Acknowledgment packet confirming message delivery.
- **Agent:** Software entity controlling a set of nodes in the graph.
- **Boundary Edge:** An edge connecting two nodes owned by different agents.
- **Bootstrap CI:** Non-parametric confidence interval generated by 1,000 resamples with replacement.
- **Coordinator:** Agent 0; manages barriers and initiates snapshot sync.
- **DCR:** Distributed Constraint Reasoning (specifically Distributed Graph Colouring).
- **Deadlock:** State where agents are waiting for messages but the simulation queue is empty.
- **Deterministic Policy:** DSA-B min-conflict decision engine using seeded random numbers.
- **Discrete-Event Scheduler:** Priority queue managing virtual time ($u$) events.
- **Duplicate Suppression:** Discarding repeated deliveries of already-processed message IDs.
- **Fault Injector:** Configurable engine simulating drops, jitter, reordering, and partitions.
- **Internal Edge:** An edge connecting two nodes owned by the same agent.
- **Jitter:** Random variation in message transmission latency.
- **McNemar's Test:** Exact paired statistical test comparing binary outcomes across identical seeds.
- **Monotonic Version:** Incrementing integer counter preventing older states from overwriting newer states.
- **Partition:** Total communication blackout across specified agents during a time window.
- **Planted Graph:** A graph generated with a known, mathematically guaranteed zero-conflict coloring.
- **Retransmission:** Re-sending an unacknowledged message after a timeout.
- **Scrubber:** Interactive timeline slider to replay simulation events step-by-step.
- **Simulated Time ($u$):** Virtual simulation clock units, normalized such that $1.0u \approx 1$ round.
- **Solver:** Worker agent (Agent 1, Agent 2) responsible for local constraint resolution.
- **Stall:** Individual agent waiting at a barrier after peers have finished.
- **SYNC_REQ / SYNC_RESP:** Snapshot synchronization protocol messages for post-partition healing.
- **Validation:** Independent verification guaranteeing 0 edge conflicts and complete node assignment.
- **Wilson Score Interval:** Asymmetric binomial confidence interval suitable for small sample sizes and extreme proportions.

---

## 15. Limitations, Disclosures & Threats to Validity

1. **Deterministic Agents vs. LLM Workflows:** All empirical sweep data in `results/*.csv` and `resilient_agents.db` was produced by deterministic DSA-B agents. Zero empirical sweeps have been run with live Gemini LLMs. While LLM policies are implemented in code, conclusions regarding LLM cost and prompt stability remain theoretical until empirical LLM runs are conducted.
2. **Localhost UDP Transport Scope:** Localhost loopback UDP transport is implemented in [transport_udp.py](file:///c:/Users/ADMIN/Desktop/rmipr/resilient-agents/backend/app/core/transport_udp.py) and verified by 5 unit tests. Multi-host physical network deployment across separate machines over wide-area networks remains outside current scope.
3. **Problem Domain Generality:** Findings are established on Distributed Graph Colouring. While graph coloring is an NP-complete constraint benchmark, generalizing these results to open-ended conversational multi-agent workflows (e.g., code generation or dialogue) requires cautious evaluation.
4. **Hard Preset Timeouts:** In the Hard problem preset, Protected Mode C runs reached the $400.0u$ simulation time limit due to cumulative backoff retries. While 83.3% achieved valid colorings, researchers must calibrate round budgets and barrier timeouts when scaling to dense graphs.
