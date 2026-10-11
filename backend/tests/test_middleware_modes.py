import pytest
from app.experiments.runner import execute_single_run
from app.problems.graph_coloring import DIFFICULTY_PRESETS

def test_mode_a_reliable_completes_successfully():
    problem_cfg = dict(DIFFICULTY_PRESETS["easy"])
    problem_cfg["round_budget"] = 15
    fault_cfg = {"loss_rate": 0.0, "min_latency": 1.0, "max_latency": 1.0, "jitter": 0.0}

    res = execute_single_run(
        task_id="t_rel",
        run_id="r_a_rel",
        mode="baseline",
        seed=42,
        problem_config=problem_cfg,
        fault_config=fault_cfg,
        max_sim_time=200.0,
    )
    assert res.status == "completed"
    assert res.termination_reason == "completed"
    assert res.validation.is_valid is True

def test_mode_a_lossy_deadlocks_without_hanging():
    problem_cfg = dict(DIFFICULTY_PRESETS["easy"])
    problem_cfg["round_budget"] = 15
    # High loss causes synchronous baseline barrier to stall
    fault_cfg = {"loss_rate": 0.5, "min_latency": 1.0, "max_latency": 2.0, "jitter": 0.0}

    res = execute_single_run(
        task_id="t_loss",
        run_id="r_a_loss",
        mode="baseline",
        seed=101,
        problem_config=problem_cfg,
        fault_config=fault_cfg,
        max_sim_time=100.0,
    )
    # Baseline cannot recover from lost messages; scheduler queue empties
    assert res.termination_reason in ("deadlock", "stall")
    assert res.status == "failed"

def test_mode_b_timeout_baseline_avoids_deadlock_under_loss():
    problem_cfg = dict(DIFFICULTY_PRESETS["easy"])
    problem_cfg["round_budget"] = 10
    fault_cfg = {"loss_rate": 0.4, "min_latency": 1.0, "max_latency": 2.0, "jitter": 0.0}
    mw_cfg = {"barrier_timeout": 5.0}

    res = execute_single_run(
        task_id="t_b",
        run_id="r_b_loss",
        mode="timeout_baseline",
        seed=101,
        problem_config=problem_cfg,
        fault_config=fault_cfg,
        middleware_config=mw_cfg,
        max_sim_time=200.0,
    )
    # Mode B times out and advances; does NOT deadlock
    assert res.termination_reason == "completed"
    assert res.metrics_summary["timeouts"] > 0

def test_mode_c_protected_recovers_under_packet_loss():
    problem_cfg = dict(DIFFICULTY_PRESETS["easy"])
    problem_cfg["round_budget"] = 15
    # 25% loss rate
    fault_cfg = {"loss_rate": 0.25, "min_latency": 1.0, "max_latency": 2.0, "jitter": 0.2}
    mw_cfg = {
        "ack_timeout": 2.5,
        "max_retries": 4,
        "backoff_factor": 1.4,
        "round_barrier_timeout": 8.0,
    }

    res = execute_single_run(
        task_id="t_c",
        run_id="r_c_loss",
        mode="protected",
        seed=42,
        problem_config=problem_cfg,
        fault_config=fault_cfg,
        middleware_config=mw_cfg,
        max_sim_time=300.0,
    )
    assert res.status == "completed"
    assert res.metrics_summary["retransmissions"] > 0
    assert res.metrics_summary["acks_received"] > 0
    assert res.metrics_summary["recovery_success_rate"] > 0.0
    assert res.validation.is_valid is True

def test_mode_c_short_partition_recovery():
    problem_cfg = dict(DIFFICULTY_PRESETS["easy"])
    problem_cfg["round_budget"] = 12
    # Short partition from t=5.0 to 9.0 (duration 4.0), within retry budget
    fault_cfg = {
        "loss_rate": 0.0,
        "min_latency": 1.0,
        "max_latency": 1.0,
        "jitter": 0.0,
        "partitions": [{"start_time": 5.0, "duration": 4.0, "isolated_agents": None}],
    }
    mw_cfg = {
        "ack_timeout": 2.0,
        "max_retries": 4,
        "backoff_factor": 1.5,
        "round_barrier_timeout": 12.0,
    }

    res = execute_single_run(
        task_id="t_part_short",
        run_id="r_c_part_short",
        mode="protected",
        seed=42,
        problem_config=problem_cfg,
        fault_config=fault_cfg,
        middleware_config=mw_cfg,
        max_sim_time=200.0,
    )
    assert res.status == "completed"
    assert res.metrics_summary["retransmissions"] > 0
    assert res.validation.is_valid is True

def test_mode_c_duplicate_suppression_and_stale_rejection():
    problem_cfg = dict(DIFFICULTY_PRESETS["easy"])
    problem_cfg["round_budget"] = 10
    # Faults with duplicates and reordering
    fault_cfg = {
        "loss_rate": 0.0,
        "min_latency": 1.0,
        "max_latency": 2.0,
        "jitter": 0.2,
        "duplicate_rate": 0.4,
        "reorder_rate": 0.3,
        "reorder_extra_delay": 3.0,
    }

    res = execute_single_run(
        task_id="t_dup_stale",
        run_id="r_c_dup_stale",
        mode="protected",
        seed=55,
        problem_config=problem_cfg,
        fault_config=fault_cfg,
        max_sim_time=250.0,
    )
    assert res.status == "completed"
    # Duplicates were generated and suppressed
    assert res.metrics_summary["duplicates_suppressed"] > 0
    assert res.validation.is_valid is True
