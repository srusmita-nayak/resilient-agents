import time
import random
from typing import Dict, Any, List, Optional, Callable
from app.core.clock import DiscreteEventScheduler
from app.core.faults import FaultConfig, FaultInjector
from app.core.channel import VirtualChannel
from app.problems.graph_coloring import generate_graph_coloring_instance, GraphColoringInstance
from app.problems.validator import validate_coloring, ValidationReport
from app.agents.base import Agent
from app.agents.policies import DeterministicPolicy, MockLLMPolicy
from app.agents.llm_adapter import GeminiLLMPolicy
from app.middleware.baseline import BaselineMiddleware
from app.middleware.timeout_baseline import TimeoutBaselineMiddleware
from app.middleware.protected import ProtectedMiddleware
from app.metrics.collector import derive_run_metrics
from app.config import settings

class RunExecutionResult:
    def __init__(
        self,
        status: str,
        outcome: str,
        termination_reason: str,
        simulated_time: float,
        wall_ms: float,
        validation: ValidationReport,
        metrics_summary: Dict[str, Any],
        events: List[Dict[str, Any]],
        llm_calls: List[Dict[str, Any]],
        coloring: Dict[int, int],
    ):
        self.status = status
        self.outcome = outcome
        self.termination_reason = termination_reason
        self.simulated_time = simulated_time
        self.wall_ms = wall_ms
        self.validation = validation
        self.metrics_summary = metrics_summary
        self.events = events
        self.llm_calls = llm_calls
        self.coloring = coloring

def execute_single_run(
    task_id: str,
    run_id: str,
    mode: str,  # "baseline", "timeout_baseline", "protected"
    seed: int,
    problem_config: Dict[str, Any],
    fault_config: Dict[str, Any],
    middleware_config: Optional[Dict[str, Any]] = None,
    agent_type: str = "deterministic",  # "deterministic" or "llm"
    llm_provider: Optional[str] = None,
    llm_model: Optional[str] = None,
    llm_call_budget: int = 50,
    gemini_api_key: Optional[str] = None,
    mock_llm_mode: Optional[str] = None,
    event_listener: Optional[Callable[[Dict[str, Any]], None]] = None,
    max_sim_time: float = 500.0,
    max_events: int = 5000,
    max_wall_seconds: float = 30.0,
    is_cancelled_func: Optional[Callable[[], bool]] = None,
) -> RunExecutionResult:
    """Executes a single simulation run under Mode A, B, or C with independent validation."""
    t_wall_start = time.perf_counter()
    events: List[Dict[str, Any]] = []
    seq_counter = 0

    def _on_event(raw_ev: Dict[str, Any]) -> None:
        nonlocal seq_counter
        seq_counter += 1
        ev_record = {
            "run_id": run_id,
            "seq": seq_counter,
            "sim_time": raw_ev.get("sim_time", 0.0),
            "type": raw_ev.get("type", "UNKNOWN"),
            "agent_id": raw_ev.get("agent_id"),
            "target_agent_id": raw_ev.get("target_agent_id"),
            "msg_id": raw_ev.get("msg_id"),
            "payload": raw_ev.get("payload", {}),
        }
        events.append(ev_record)
        if event_listener:
            event_listener(ev_record)

    # 1. Initialize Discrete-Event Scheduler
    scheduler = DiscreteEventScheduler(
        max_sim_time=max_sim_time,
        max_events=max_events,
        max_wall_seconds=max_wall_seconds,
    )

    # 2. Initialize Fault Injector
    faults = FaultInjector(FaultConfig(**fault_config), seed=seed)

    # 3. Initialize Virtual Channel
    channel = VirtualChannel(scheduler=scheduler, fault_injector=faults, on_event=_on_event)

    # 4. Generate Problem Instance with planted solution
    instance: GraphColoringInstance = generate_graph_coloring_instance(
        task_id=task_id,
        num_agents=problem_config.get("num_agents", 3),
        num_nodes=problem_config.get("num_nodes", 15),
        num_colors=problem_config.get("num_colors", 3),
        edge_density=problem_config.get("edge_density", 0.3),
        round_budget=problem_config.get("round_budget", 30),
        seed=seed,
    )

    # Generate initial colors (seeded PRNG, common across all modes for fair comparison)
    init_rng = random.Random(seed + 1000)
    initial_colors = {
        n: init_rng.randint(0, instance.num_colors - 1) for n in range(instance.num_nodes)
    }

    # Internal and boundary edges mapping
    edges_set = set(instance.edges)
    agent_ids = list(instance.agent_nodes.keys())

    # 5. Build Agents and Policies
    agents: Dict[str, Agent] = {}
    for aid in agent_ids:
        owned = instance.agent_nodes[aid]
        # Categorize edges
        internal_edges = [
            (u, v) for u, v in instance.edges if u in owned and v in owned
        ]
        boundary_edges = [
            (u, v) for u, v in instance.edges if (u in owned and v not in owned) or (v in owned and u not in owned)
        ]
        peers = [p for p in agent_ids if p != aid]

        # Policy setup
        det_policy = DeterministicPolicy(seed=seed + int(aid.split("_")[-1]) * 101)
        if agent_type == "llm":
            if mock_llm_mode:
                policy = MockLLMPolicy(deterministic_fallback=det_policy, mode=mock_llm_mode)
            else:
                key = gemini_api_key or settings.GEMINI_API_KEY
                policy = GeminiLLMPolicy(
                    api_key=key,
                    model_name=llm_model or settings.GEMINI_MODEL,
                    call_budget=llm_call_budget,
                    deterministic_fallback=det_policy,
                )
        else:
            policy = det_policy

        role = "coordinator" if aid == "agent_0" else "solver"
        agent = Agent(
            agent_id=aid,
            role=role,
            owned_nodes=owned,
            initial_colors=initial_colors,
            internal_edges=internal_edges,
            boundary_edges=boundary_edges,
            num_colors=instance.num_colors,
            peers=peers,
            policy=policy,
        )
        agents[aid] = agent

    # 6. Build Middleware per mode
    middlewares: Dict[str, Any] = {}
    m_cfg = middleware_config or {}

    for aid, agent in agents.items():
        if mode == "baseline":
            mw = BaselineMiddleware(
                agent=agent,
                scheduler=scheduler,
                channel=channel,
                task_id=task_id,
                run_id=run_id,
                round_budget=instance.round_budget,
                on_event=_on_event,
            )
        elif mode == "timeout_baseline":
            mw = TimeoutBaselineMiddleware(
                agent=agent,
                scheduler=scheduler,
                channel=channel,
                task_id=task_id,
                run_id=run_id,
                round_budget=instance.round_budget,
                barrier_timeout=m_cfg.get("barrier_timeout", 8.0),
                on_event=_on_event,
            )
        elif mode == "protected":
            mw = ProtectedMiddleware(
                agent=agent,
                scheduler=scheduler,
                channel=channel,
                task_id=task_id,
                run_id=run_id,
                round_budget=instance.round_budget,
                ack_timeout=m_cfg.get("ack_timeout", 3.0),
                max_retries=m_cfg.get("max_retries", 3),
                backoff_factor=m_cfg.get("backoff_factor", 1.5),
                round_barrier_timeout=m_cfg.get("round_barrier_timeout", 10.0),
                max_recoordination_attempts=m_cfg.get("max_recoordination_attempts", 2),
                enable_retransmission=m_cfg.get("enable_retransmission", True),
                enable_version_filter=m_cfg.get("enable_version_filter", True),
                enable_sync_recoordination=m_cfg.get("enable_sync_recoordination", True),
                on_event=_on_event,
            )
        else:
            raise ValueError(f"Unknown mode: {mode}")

        middlewares[aid] = mw
        channel.register_receiver(aid, mw.handle_message)

    # 7. Start simulation
    for mw in middlewares.values():
        mw.start()

    # 8. Discrete-event execution loop
    status = "completed"
    termination_reason = "completed"
    t_deadline = t_wall_start + max_wall_seconds

    while True:
        # Cancellation check
        if is_cancelled_func and is_cancelled_func():
            status = "cancelled"
            termination_reason = "cancelled"
            break

        # Check if all agents finished
        if all(mw.is_finished for mw in middlewares.values()):
            status = "completed"
            termination_reason = "completed"
            break

        # Check wall-clock timeout
        if time.perf_counter() > t_deadline:
            status = "failed"
            termination_reason = "wall_limit"
            break

        # Check event limit
        if scheduler.events_processed >= max_events:
            status = "failed"
            termination_reason = "event_limit"
            break

        # Check virtual simulation time limit
        if scheduler.now >= max_sim_time:
            status = "failed"
            termination_reason = "time_limit"
            break

        # Check if events remain in queue
        if not scheduler.has_pending():
            # No pending events but not all agents finished => Deadlock / stall
            status = "failed"
            if mode == "baseline":
                termination_reason = "deadlock"
            else:
                termination_reason = "stall"
            _on_event({
                "sim_time": scheduler.now,
                "type": "DEADLOCK" if termination_reason == "deadlock" else "STALL",
                "payload": {"reason": f"Queue empty while agents pending ({termination_reason})"},
            })
            break

        # Advance one discrete event
        stepped = scheduler.step()
        if not stepped:
            break

    wall_ms = (time.perf_counter() - t_wall_start) * 1000.0

    # 9. Collect final coloring
    final_coloring: Dict[int, int] = {}
    for agent in agents.values():
        final_coloring.update(agent.get_owned_colors())

    # 10. Independent Validation
    validation_report = validate_coloring(
        coloring=final_coloring,
        edges=instance.edges,
        total_nodes=instance.num_nodes,
        num_colors=instance.num_colors,
    )

    # Record validation event
    _on_event({
        "sim_time": scheduler.now,
        "type": "VALIDATION",
        "payload": {
            "is_valid": validation_report.is_valid,
            "violations_count": validation_report.violation_count,
            "colored_nodes": validation_report.colored_nodes,
            "total_nodes": validation_report.total_nodes,
        },
    })

    # Determine final outcome
    if status == "cancelled":
        outcome = "cancelled"
    elif status == "completed":
        outcome = "valid" if validation_report.is_valid else "invalid"
    else:
        outcome = "incomplete"

    # 11. Metrics Derivation
    metrics_summary = derive_run_metrics(events)
    metrics_summary["simulated_time"] = round(scheduler.now, 2)
    metrics_summary["wall_ms"] = round(wall_ms, 2)
    metrics_summary["validation_valid"] = validation_report.is_valid
    metrics_summary["violations_count"] = validation_report.violation_count

    # 12. LLM Call extraction
    llm_calls_records = []
    for aid, agent in agents.items():
        for decision in agent.llm_decisions:
            if decision.tokens_used > 0 or decision.is_fallback:
                llm_calls_records.append({
                    "run_id": run_id,
                    "agent_id": aid,
                    "prompt_hash": decision.prompt_hash,
                    "latency_ms": decision.llm_latency_ms,
                    "tokens_used": decision.tokens_used,
                    "is_fallback": decision.is_fallback,
                    "error_class": decision.error_class,
                })

    return RunExecutionResult(
        status=status,
        outcome=outcome,
        termination_reason=termination_reason,
        simulated_time=scheduler.now,
        wall_ms=wall_ms,
        validation=validation_report,
        metrics_summary=metrics_summary,
        events=events,
        llm_calls=llm_calls_records,
        coloring=final_coloring,
    )
