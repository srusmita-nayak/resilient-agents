# Empirical Experiment Results Directory

This directory contains real, stored CSV data exports derived from executing multi-agent simulation experiments across 30 seeds per experimental cell on the Resilient Agents research platform.

## Dataset Inventory

1. **`master_experiment_results.csv`**: Comprehensive dataset aggregating all runs across all experimental suites (Reliable, Loss 25%, Loss 50%, Partition Burst, Hard Difficulty). Contains per-run seed, mode, valid solution status, violation count, simulated time, wall-clock time, messages dispatched, drops, retries, ACKs, and recovery success rate.
2. **`results_reliable_sweep.csv`**: Baseline control experiment under a 100% reliable channel (0% loss, 1.0u fixed latency, 0 jitter). Demonstrates that both Mode A and Mode B achieve identical baseline convergence (90.0% valid) with 150 messages, while Mode C incurs exactly 2.0x message overhead (300 messages) due to explicit ACKs.
3. **`results_loss_25_sweep.csv`**: Moderate loss severity (25% packet loss, 1.0-2.5u latency, 0.5u jitter). Evaluates Mode A (which stalls/deadlocks on 100% of runs due to missing synchronous round arrivals) versus Mode B (93.3% valid via round barrier skips) and Mode C (83.3% valid with bounded retries and recovery).
4. **`results_loss_50_sweep.csv`**: Severe loss condition (50% packet loss). Mode A collapses to 3.3% valid (deadlocked on 30/30 runs), Mode B achieves 86.7% valid, and Mode C achieves 93.3% valid through exponential backoff recovery and version-based state reconciliation.
5. **`results_partition_sweep.csv`**: Temporary network partition burst from $t=10.0$ to $t=25.0$ virtual units (duration 15.0u). Demonstrates post-partition recovery where Mode C reconciles boundary node states via monotonic versions and authoritative snapshot synchronization.
6. **`results_hard_sweep.csv`**: High-density graph instance (35 nodes, 5 agents, edge density 0.50, round budget 40). Calibrates algorithmic solver limits against communication fault damage.

### Run Count Architecture (Database vs. CSV Exports)
- **SQLite Database:** Each suite executes **120 runs** (30 seeds $\times$ [1 fault-free reference + 3 protocol modes]), totaling **600 runs** stored in `resilient_agents.db`.
- **CSV Exports:** The CSV sweep files serialize the evaluated comparative cells (Modes A, B, and C; 90 rows per suite), totaling **450 rows** in `master_experiment_results.csv`. The 150 fault-free reference runs are retained in SQLite for paired solvability calibration (`paired_fault_free_only`).

## Column Dictionary


- `run_id`: Unique identifier for the individual simulation execution.
- `experiment_id`: Parent experiment batch identifier.
- `mode`: Protocol mode (`baseline` = Mode A, `timeout_baseline` = Mode B, `protected` = Mode C).
- `seed`: Pseudo-random number generator seed (common across all modes for paired comparison).
- `status`: Execution completion status (`completed`, `failed`, `cancelled`, `interrupted`).
- `outcome`: Task outcome (`valid` = 0 edge conflicts independently verified, `invalid`, `incomplete`).
- `termination_reason`: Reason simulation stopped (`completed`, `deadlock`, `stall`, `time_limit`, `wall_limit`).
- `validation_valid`: Binary indicator (1 = valid, 0 = invalid) from independent mathematical validator.
- `violations_count`: Number of edge coloring conflicts detected in the final graph.
- `simulated_time`: Virtual simulation clock duration in normalized units.
- `wall_ms`: Real physical execution time in milliseconds.
- `messages_sent`: Total packets transmitted over the virtual channel.
- `messages_dropped`: Packets dropped by simulated network faults.
- `retransmissions`: Packets retransmitted by Mode C exponential backoff state machine.
- `acks_received`: Correlated ACKs received by Mode C senders.
- `recovery_success_rate`: Ratio of recovered messages to total messages requiring recovery.
- `agent_type`: Agent decision engine (`deterministic` or `llm`).
- `code_version`: Git version identifier for scientific reproducibility.
