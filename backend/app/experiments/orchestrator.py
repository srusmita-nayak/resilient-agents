import threading
import queue
import time
import uuid
from typing import Dict, Any, List, Optional, Callable
from app.db.repository import Repository
from app.experiments.runner import execute_single_run

class ExperimentOrchestrator:
    """Manages asynchronous batch experiments in a dedicated background worker thread."""
    def __init__(self, repository: Repository):
        self.repository = repository
        self.task_queue: queue.Queue = queue.Queue()
        self.active_experiment_id: Optional[str] = None
        self._cancel_flags: Dict[str, threading.Event] = {}
        self._lock = threading.Lock()
        self.event_subscribers: List[Callable[[Dict[str, Any]], None]] = []

        # Start background worker daemon thread
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()

    def subscribe_events(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        self.event_subscribers.append(callback)

    def _broadcast_event(self, ev: Dict[str, Any]) -> None:
        for sub in self.event_subscribers:
            try:
                sub(ev)
            except Exception:
                pass

    def cancel_experiment(self, experiment_id: str) -> bool:
        with self._lock:
            if experiment_id in self._cancel_flags:
                self._cancel_flags[experiment_id].set()
                return True
        return False

    def is_cancelled(self, experiment_id: str) -> bool:
        with self._lock:
            flag = self._cancel_flags.get(experiment_id)
            return flag.is_set() if flag else False

    def wait_idle(self, timeout: float = 5.0) -> bool:
        """Blocks until the background task queue is empty and the active experiment finishes."""
        t0 = time.time()
        while time.time() - t0 < timeout:
            with self._lock:
                if self.task_queue.empty() and self.active_experiment_id is None:
                    return True
            time.sleep(0.02)
        with self._lock:
            return self.task_queue.empty() and self.active_experiment_id is None


    def submit_experiment(
        self,
        experiment_id: str,
        name: str,
        config: Dict[str, Any],
        seeds: List[int],
        agent_type: str,
        provider_model: Optional[str] = None,
        gemini_api_key: Optional[str] = None,
    ) -> None:
        modes = config.get("modes", ["baseline", "timeout_baseline", "protected"])
        include_fault_free_ref = config.get("include_fault_free_reference", False)
        
        # Calculate total runs
        runs_per_seed = len(modes) + (1 if include_fault_free_ref else 0)
        total_runs = len(seeds) * runs_per_seed

        with self._lock:
            self._cancel_flags[experiment_id] = threading.Event()

        # Create experiment record in DB
        self.repository.create_experiment(
            exp_id=experiment_id,
            name=name,
            config=config,
            seeds=seeds,
            agent_type=agent_type,
            provider_model=provider_model,
            total_runs=total_runs,
        )

        # Enqueue experiment task
        self.task_queue.put({
            "experiment_id": experiment_id,
            "name": name,
            "config": config,
            "seeds": seeds,
            "agent_type": agent_type,
            "provider_model": provider_model,
            "gemini_api_key": gemini_api_key,
            "modes": modes,
            "include_fault_free_ref": include_fault_free_ref,
        })

    def _worker_loop(self) -> None:
        while True:
            item = self.task_queue.get()
            exp_id = item["experiment_id"]
            with self._lock:
                self.active_experiment_id = exp_id

            try:
                self._run_experiment_batch(item)
            except Exception as ex:
                self.repository.update_experiment_status(
                    exp_id=exp_id,
                    status="failed",
                    error_message=str(ex),
                )
            finally:
                with self._lock:
                    self.active_experiment_id = None
                    self._cancel_flags.pop(exp_id, None)
                self.task_queue.task_done()

    def _run_experiment_batch(self, task: Dict[str, Any]) -> None:
        exp_id = task["experiment_id"]
        config = task["config"]
        seeds = task["seeds"]
        modes = task["modes"]
        include_ref = task["include_fault_free_ref"]
        agent_type = task["agent_type"]
        provider_model = task.get("provider_model")
        api_key = task.get("gemini_api_key")

        self.repository.update_experiment_status(exp_id=exp_id, status="running")

        problem_cfg = config.get("problem", {})
        fault_cfg = config.get("faults", {})
        mw_cfg = config.get("middleware", {})
        limits = config.get("limits", {})
        mock_llm_mode = config.get("mock_llm_mode")

        completed_runs_count = 0

        for seed in seeds:
            # 1. Fault-free reference run if requested
            if include_ref:
                if self.is_cancelled(exp_id):
                    break
                run_id = f"run_{exp_id}_{seed}_fault_free"
                self.repository.create_run(run_id=run_id, experiment_id=exp_id, mode="fault_free_reference", seed=seed)
                self.repository.update_run_started(run_id)

                ff_fault_cfg = {"loss_rate": 0.0, "min_latency": 1.0, "max_latency": 1.0, "jitter": 0.0}
                res = execute_single_run(
                    task_id=f"task_{seed}",
                    run_id=run_id,
                    mode="baseline",
                    seed=seed,
                    problem_config=problem_cfg,
                    fault_config=ff_fault_cfg,
                    middleware_config=mw_cfg,
                    agent_type=agent_type,
                    llm_provider="gemini",
                    llm_model=provider_model,
                    gemini_api_key=api_key,
                    mock_llm_mode=mock_llm_mode,
                    event_listener=self._broadcast_event,
                    max_sim_time=limits.get("max_sim_time", 500.0),
                    max_events=limits.get("max_events", 5000),
                    max_wall_seconds=limits.get("max_wall_seconds", 30.0),
                    is_cancelled_func=lambda: self.is_cancelled(exp_id),
                )
                self._persist_run_result(run_id, res)
                completed_runs_count += 1
                self.repository.update_experiment_status(exp_id=exp_id, status="running", completed_runs=completed_runs_count)

            # 2. Sweep across configured modes
            for mode in modes:
                if self.is_cancelled(exp_id):
                    break

                run_id = f"run_{exp_id}_{seed}_{mode}"
                self.repository.create_run(run_id=run_id, experiment_id=exp_id, mode=mode, seed=seed)
                self.repository.update_run_started(run_id)

                res = execute_single_run(
                    task_id=f"task_{seed}",
                    run_id=run_id,
                    mode=mode,
                    seed=seed,
                    problem_config=problem_cfg,
                    fault_config=fault_cfg,
                    middleware_config=mw_cfg,
                    agent_type=agent_type,
                    llm_provider="gemini",
                    llm_model=provider_model,
                    gemini_api_key=api_key,
                    mock_llm_mode=mock_llm_mode,
                    event_listener=self._broadcast_event,
                    max_sim_time=limits.get("max_sim_time", 500.0),
                    max_events=limits.get("max_events", 5000),
                    max_wall_seconds=limits.get("max_wall_seconds", 30.0),
                    is_cancelled_func=lambda: self.is_cancelled(exp_id),
                )
                self._persist_run_result(run_id, res)
                completed_runs_count += 1
                self.repository.update_experiment_status(exp_id=exp_id, status="running", completed_runs=completed_runs_count)

            if self.is_cancelled(exp_id):
                break

        # Terminal status
        final_status = "cancelled" if self.is_cancelled(exp_id) else "completed"
        self.repository.update_experiment_status(
            exp_id=exp_id,
            status=final_status,
            completed_runs=completed_runs_count,
        )

    def _persist_run_result(self, run_id: str, result: Any) -> None:
        self.repository.insert_events_batch(result.events)
        self.repository.complete_run(
            run_id=run_id,
            status=result.status,
            outcome=result.outcome,
            termination_reason=result.termination_reason,
            simulated_time=result.simulated_time,
            wall_ms=result.wall_ms,
            validation_valid=result.validation.is_valid,
            violations_count=result.validation.violation_count,
            metrics_summary=result.metrics_summary,
        )
        for call in result.llm_calls:
            self.repository.record_llm_call(
                run_id=run_id,
                agent_id=call["agent_id"],
                prompt_hash=call["prompt_hash"],
                latency_ms=call["latency_ms"],
                tokens_used=call["tokens_used"],
                is_fallback=call["is_fallback"],
                error_class=call.get("error_class"),
            )
