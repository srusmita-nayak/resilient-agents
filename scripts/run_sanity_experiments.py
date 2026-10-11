import os
import sys
from pathlib import Path
import csv

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.db.database import init_db
from app.db.repository import Repository
from app.experiments.runner import execute_single_run
from app.problems.graph_coloring import DIFFICULTY_PRESETS
from app.metrics.statistics import wilson_score_interval, mcnemar_exact_test, bootstrap_confidence_interval

def main():
    print("=== Running Sanity Experiment Suite (Deterministic Agents) ===")
    db_path = Path(__file__).resolve().parent.parent / "backend" / "resilient_agents.db"
    init_db(db_path)
    repo = Repository(db_path)
    results_dir = Path(__file__).resolve().parent.parent / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    seeds = list(range(42, 72)) # 30 seeds
    print(f"Executing with 30 seeds: {seeds[0]} .. {seeds[-1]}")

    suites = [
        {
            "id": "exp_reliable_30",
            "name": "Reliable Network Baseline Sweep",
            "preset": "easy",
            "faults": {"loss_rate": 0.0, "min_latency": 1.0, "max_latency": 1.0, "jitter": 0.0},
            "mw": {"barrier_timeout": 8.0, "ack_timeout": 3.0, "max_retries": 3},
            "filename": "results_reliable_sweep.csv",
        },
        {
            "id": "exp_loss_25_30",
            "name": "Loss Severity Sweep (25% Packet Loss)",
            "preset": "easy",
            "faults": {"loss_rate": 0.25, "min_latency": 1.0, "max_latency": 2.5, "jitter": 0.5},
            "mw": {"barrier_timeout": 8.0, "ack_timeout": 2.5, "max_retries": 4, "round_barrier_timeout": 12.0},
            "filename": "results_loss_25_sweep.csv",
        },
        {
            "id": "exp_loss_50_30",
            "name": "Severe Loss Sweep (50% Packet Loss)",
            "preset": "easy",
            "faults": {"loss_rate": 0.50, "min_latency": 1.0, "max_latency": 3.0, "jitter": 0.8},
            "mw": {"barrier_timeout": 8.0, "ack_timeout": 2.5, "max_retries": 4, "round_barrier_timeout": 14.0},
            "filename": "results_loss_50_sweep.csv",
        },
        {
            "id": "exp_partition_burst_30",
            "name": "Temporary Partition Burst Sweep",
            "preset": "easy",
            "faults": {
                "loss_rate": 0.05,
                "min_latency": 1.0,
                "max_latency": 2.0,
                "jitter": 0.3,
                "partitions": [{"start_time": 10.0, "duration": 15.0, "isolated_agents": None}],
            },
            "mw": {"barrier_timeout": 8.0, "ack_timeout": 2.5, "max_retries": 4, "round_barrier_timeout": 16.0},
            "filename": "results_partition_sweep.csv",
        },
        {
            "id": "exp_hard_difficulty_30",
            "name": "Hard Problem Preset Calibration Sweep",
            "preset": "hard",
            "faults": {"loss_rate": 0.20, "min_latency": 1.0, "max_latency": 2.0, "jitter": 0.4},
            "mw": {"barrier_timeout": 10.0, "ack_timeout": 2.5, "max_retries": 4, "round_barrier_timeout": 16.0},
            "filename": "results_hard_sweep.csv",
        },
    ]

    all_csv_rows = []

    for suite in suites:
        exp_id = suite["id"]
        exp_name = suite["name"]
        prob_cfg = dict(DIFFICULTY_PRESETS[suite["preset"]])
        fault_cfg = suite["faults"]
        mw_cfg = suite["mw"]
        modes = ["baseline", "timeout_baseline", "protected"]

        print(f"\n--> Running Suite: {exp_name} (ID: {exp_id})")
        repo.create_experiment(
            exp_id=exp_id,
            name=exp_name,
            config={"problem": prob_cfg, "faults": fault_cfg, "middleware": mw_cfg},
            seeds=seeds,
            agent_type="deterministic",
            provider_model=None,
            total_runs=len(seeds) * (len(modes) + 1),
        )
        repo.update_experiment_status(exp_id, "running")

        suite_rows = []
        completed_count = 0

        for seed in seeds:
            # 1. Fault-free reference
            ff_id = f"run_{exp_id}_{seed}_fault_free"
            repo.create_run(ff_id, exp_id, "fault_free_reference", seed)
            repo.update_run_started(ff_id)
            ff_res = execute_single_run(
                task_id=f"task_{seed}",
                run_id=ff_id,
                mode="baseline",
                seed=seed,
                problem_config=prob_cfg,
                fault_config={"loss_rate": 0.0, "min_latency": 1.0, "max_latency": 1.0, "jitter": 0.0},
                middleware_config=mw_cfg,
                agent_type="deterministic",
                max_sim_time=400.0,
            )
            repo.insert_events_batch(ff_res.events)
            repo.complete_run(
                ff_id, ff_res.status, ff_res.outcome, ff_res.termination_reason,
                ff_res.simulated_time, ff_res.wall_ms, ff_res.validation.is_valid,
                ff_res.validation.violation_count, ff_res.metrics_summary,
            )
            completed_count += 1

            # 2. Modes A, B, C
            for m in modes:
                run_id = f"run_{exp_id}_{seed}_{m}"
                repo.create_run(run_id, exp_id, m, seed)
                repo.update_run_started(run_id)
                res = execute_single_run(
                    task_id=f"task_{seed}",
                    run_id=run_id,
                    mode=m,
                    seed=seed,
                    problem_config=prob_cfg,
                    fault_config=fault_cfg,
                    middleware_config=mw_cfg,
                    agent_type="deterministic",
                    max_sim_time=400.0,
                )
                repo.insert_events_batch(res.events)
                repo.complete_run(
                    run_id, res.status, res.outcome, res.termination_reason,
                    res.simulated_time, res.wall_ms, res.validation.is_valid,
                    res.validation.violation_count, res.metrics_summary,
                )
                completed_count += 1

                suite_rows.append({
                    "experiment_id": exp_id,
                    "suite_name": exp_name,
                    "mode": m,
                    "seed": seed,
                    "status": res.status,
                    "outcome": res.outcome,
                    "termination_reason": res.termination_reason,
                    "validation_valid": 1 if res.validation.is_valid else 0,
                    "violations_count": res.validation.violation_count,
                    "simulated_time": res.simulated_time,
                    "wall_ms": res.wall_ms,
                    "messages_sent": res.metrics_summary.get("messages_sent", 0),
                    "messages_dropped": res.metrics_summary.get("messages_dropped", 0),
                    "retransmissions": res.metrics_summary.get("retransmissions", 0),
                    "acks_received": res.metrics_summary.get("acks_received", 0),
                    "recovery_success_rate": res.metrics_summary.get("recovery_success_rate", 1.0),
                    "agent_type": "deterministic",
                    "code_version": "1.0.0",
                })

        repo.update_experiment_status(exp_id, "completed", completed_runs=completed_count)
        print(f"--> Completed {completed_count} runs for {exp_id}.")

        # Write Suite CSV
        csv_path = results_dir / suite["filename"]
        if suite_rows:
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=list(suite_rows[0].keys()))
                writer.writeheader()
                writer.writerows(suite_rows)
            print(f"Saved: {csv_path}")

        all_csv_rows.extend(suite_rows)

    # Master Combined CSV
    master_path = results_dir / "master_experiment_results.csv"
    if all_csv_rows:
        with open(master_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(all_csv_rows[0].keys()))
            writer.writeheader()
            writer.writerows(all_csv_rows)
        print(f"\nSaved Master Export: {master_path}")

    # Generate Statistical Summary Report
    print("\n=== SUMMARY STATISTICS ===")
    modes = ["baseline", "timeout_baseline", "protected"]
    for suite in suites:
        s_rows = [r for r in all_csv_rows if r["experiment_id"] == suite["id"]]
        print(f"\n--- {suite['name']} ---")
        for m in modes:
            m_rows = [r for r in s_rows if r["mode"] == m]
            n = len(m_rows)
            valid = sum(1 for r in m_rows if r["validation_valid"] == 1)
            deadlocks = sum(1 for r in m_rows if r["termination_reason"] in ("deadlock", "stall"))
            p, low, high = wilson_score_interval(valid, n)
            mean_msgs, _, _ = bootstrap_confidence_interval([float(r["messages_sent"]) for r in m_rows])
            mean_time, _, _ = bootstrap_confidence_interval([float(r["simulated_time"]) for r in m_rows if r["status"] == "completed"])
            print(f"  [{m:<16}] Valid: {valid}/{n} ({p*100:.1f}%, 95% CI: [{low*100:.1f}%, {high*100:.1f}%]) | Deadlocks: {deadlocks} | Mean Msgs: {mean_msgs:.1f} | Mean SimTime: {mean_time:.1f}u")

    print("\nSanity runs completed successfully!")

if __name__ == "__main__":
    main()
