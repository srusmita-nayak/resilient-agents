# Architectural & Design Decisions

This document records key technical decisions made during the design and implementation of the Resilient Agents research platform, including trade-offs and defensible rationales.

---

### Decision 1: SQLite with Repository Layer and WAL Mode over Heavy ORMs
**Decision:** Implement data persistence using SQLite with a dedicated, type-safe repository layer using explicit connection factories and PRAGMA settings (`journal_mode=WAL`, `foreign_keys=ON`, `busy_timeout=10000`) rather than a complex async ORM with heavy reflection.
**Justification:** The research harness demands high write throughput for event batches and deterministic transactions without asynchronous locking conflicts or subtle event loop deadlocks. A direct repository layer provides complete visibility over query plans, atomic batch commits, and crash-safe startup reconciliation, ensuring zero data loss during high-frequency simulation events.

---

### Decision 2: Discrete-Event Virtual Clock Simulation Model
**Decision:** Model all multi-agent interactions and network fault injections inside a discrete-event simulation queue driven by a virtual clock, rather than using wall-clock sleeps or asynchronous network delays.
**Justification:** Virtual time decouples simulation speed from wall-clock duration, enabling extensive seed sweeps to complete in seconds rather than hours. Crucially, virtual clocks make fault schedules (e.g. partition start and end times, jitter, packet reordering) 100% deterministic and reproducible across identical seeds, satisfying rigorous scientific standards.

---

### Decision 3: Background Worker Thread with Cooperative Cancellation for Experiment Orchestration
**Decision:** Run experiment batches in a dedicated background worker thread communicating with the FastAPI application via thread-safe queues and atomic flags, rather than spawning arbitrary OS processes or blocking the asyncio event loop.
**Justification:** Multi-agent simulations perform CPU-intensive discrete event processing that can block asyncio event loops if run inline. An isolated worker thread keeps the REST API and WebSocket broadcast loops responsive, allows clean cooperative cancellation between simulation steps, and avoids complex inter-process memory sharing and Windows spawn/fork discrepancies.

---

### Decision 4: Three Disjoint Execution Modes for Fair Comparative Baselines
**Decision:** Maintain three rigorously identical task setups across Mode A (Synchronous baseline), Mode B (Timeout baseline), and Mode C (Protected middleware), guaranteeing identical graph instances, initial color states, and pseudo-random seeds.
**Justification:** Meaningful distributed systems research requires that baselines are never weakened or tuned arbitrarily. Running all three modes against the identical planted graph instance and identical pseudo-random fault timeline guarantees that observed differences in convergence, deadlocks, and message overhead stem strictly from protocol mechanisms.

---

### Decision 5: Monotonic Version-Based Conflict Resolution and Authoritative Boundary Ownership
**Decision:** Enforce single-writer node ownership where only the assigned agent may authoritatively update a node's color and version counter, using `(version, node_id)` pairs to reject stale messages.
**Justification:** In distributed constraint satisfaction over lossy channels, out-of-order and delayed messages can lead to race conditions where old states overwrite newer decisions. Strict single-writer monotonic versioning guarantees causal consistency at boundary edges without requiring heavyweight distributed consensus protocols like Paxos or Raft.
