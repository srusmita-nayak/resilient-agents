import csv
import io
import uuid
import json
import hashlib
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Query, Response
from app.api.schemas import CreateExperimentRequest, ConnectionTestRequest
from app.db.repository import Repository
from app.experiments.orchestrator import ExperimentOrchestrator
from app.problems.graph_coloring import DIFFICULTY_PRESETS
from app.metrics.statistics import wilson_score_interval, mcnemar_exact_test, bootstrap_confidence_interval, calculate_median_and_iqr
from app.config import settings

def sanitize_csv_cell(val: Any) -> Any:
    """Escapes leading spreadsheet formula injection characters (=, +, -, @)."""
    if isinstance(val, str):
        if val.startswith(("=", "+", "-", "@")):
            return f"'{val}"
    return val

def create_api_router(repository: Repository, orchestrator: ExperimentOrchestrator) -> APIRouter:
    router = APIRouter(prefix="/api")

    # --- Health & Status ---
    @router.get("/health")
    def get_health() -> Dict[str, Any]:
        has_key = bool(settings.GEMINI_API_KEY and settings.GEMINI_API_KEY.strip())
        return {
            "status": "healthy",
            "version": settings.VERSION,
            "database": "sqlite_wal_active",
            "llm_configured": has_key,
        }

    @router.get("/ready")
    def get_ready() -> Dict[str, Any]:
        return {"ready": True}

    @router.get("/system/status")
    def get_system_status() -> Dict[str, Any]:
        db_stats = repository.get_database_stats()
        return {
            "version": settings.VERSION,
            "active_experiment_id": orchestrator.active_experiment_id,
            "is_busy": orchestrator.active_experiment_id is not None,
            "database_stats": db_stats,
            "limits": {
                "max_sim_time_default": settings.MAX_SIMULATED_TIME_DEFAULT,
                "max_events_default": settings.MAX_EVENTS_DEFAULT,
                "max_wall_seconds_default": settings.MAX_WALL_SECONDS_DEFAULT,
            },
        }

    @router.get("/presets")
    def get_presets() -> Dict[str, Any]:
        fault_presets = {
            "reliable": {
                "loss_rate": 0.0,
                "min_latency": 1.0,
                "max_latency": 1.0,
                "jitter": 0.0,
                "duplicate_rate": 0.0,
                "reorder_rate": 0.0,
                "partitions": [],
            },
            "lossy_low": {
                "loss_rate": 0.10,
                "min_latency": 1.0,
                "max_latency": 2.0,
                "jitter": 0.5,
                "duplicate_rate": 0.0,
                "reorder_rate": 0.0,
                "partitions": [],
            },
            "lossy_medium": {
                "loss_rate": 0.25,
                "min_latency": 1.0,
                "max_latency": 3.0,
                "jitter": 1.0,
                "duplicate_rate": 0.05,
                "reorder_rate": 0.05,
                "partitions": [],
            },
            "lossy_severe": {
                "loss_rate": 0.50,
                "min_latency": 1.0,
                "max_latency": 4.0,
                "jitter": 1.5,
                "duplicate_rate": 0.10,
                "reorder_rate": 0.10,
                "partitions": [],
            },
            "partition_burst": {
                "loss_rate": 0.05,
                "min_latency": 1.0,
                "max_latency": 2.0,
                "jitter": 0.5,
                "duplicate_rate": 0.0,
                "reorder_rate": 0.0,
                "partitions": [{"start_time": 10.0, "duration": 15.0, "isolated_agents": None}],
            },
        }
        return {
            "difficulty_presets": DIFFICULTY_PRESETS,
            "fault_presets": fault_presets,
        }

    # --- Experiments ---
    @router.post("/experiments")
    def create_experiment(req: CreateExperimentRequest) -> Dict[str, Any]:
        exp_id = f"exp_{uuid.uuid4().hex[:10]}"
        cfg = req.model_dump()
        orchestrator.submit_experiment(
            experiment_id=exp_id,
            name=req.name,
            config=cfg,
            seeds=req.seeds,
            agent_type=req.agent_type,
            provider_model=req.provider_model,
            gemini_api_key=req.gemini_api_key or settings.GEMINI_API_KEY,
        )
        return {"experiment_id": exp_id, "status": "queued"}

    @router.get("/experiments")
    def list_experiments(
        limit: int = Query(50, ge=1, le=200),
        offset: int = Query(0, ge=0),
        status: Optional[str] = None,
        agent_type: Optional[str] = None,
        search: Optional[str] = None,
    ) -> Dict[str, Any]:
        items = repository.list_experiments(
            limit=limit, offset=offset, status=status, agent_type=agent_type, search=search
        )
        return {"experiments": items, "count": len(items), "limit": limit, "offset": offset}

    @router.get("/experiments/{exp_id}")
    def get_experiment(exp_id: str) -> Dict[str, Any]:
        exp = repository.get_experiment(exp_id)
        if not exp:
            raise HTTPException(status_code=404, detail=f"Experiment '{exp_id}' not found")
        runs = repository.list_runs_for_experiment(exp_id)
        exp["runs"] = runs
        return exp

    @router.post("/experiments/{exp_id}/cancel")
    def cancel_experiment(exp_id: str) -> Dict[str, Any]:
        exp = repository.get_experiment(exp_id)
        if not exp:
            raise HTTPException(status_code=404, detail="Experiment not found")
        cancelled = orchestrator.cancel_experiment(exp_id)
        return {"experiment_id": exp_id, "cancelled": cancelled}

    @router.delete("/experiments/{exp_id}")
    def delete_experiment(exp_id: str) -> Dict[str, Any]:
        exp = repository.get_experiment(exp_id)
        if not exp:
            raise HTTPException(status_code=404, detail="Experiment not found")
        if orchestrator.active_experiment_id == exp_id:
            raise HTTPException(status_code=409, detail="Cannot delete an actively running experiment")
        deleted = repository.delete_experiment(exp_id)
        return {"experiment_id": exp_id, "deleted": deleted}

    @router.post("/experiments/{exp_id}/rerun-failed")
    def rerun_failed_runs(exp_id: str) -> Dict[str, Any]:
        exp = repository.get_experiment(exp_id)
        if not exp:
            raise HTTPException(status_code=404, detail="Experiment not found")
        runs = repository.list_runs_for_experiment(exp_id)
        failed_seeds = sorted(list(set(r["seed"] for r in runs if r["status"] in ("failed", "interrupted"))))
        if not failed_seeds:
            raise HTTPException(status_code=400, detail="No failed or interrupted runs to re-run")

        new_exp_id = f"exp_rerun_{uuid.uuid4().hex[:8]}"
        cfg = dict(exp["config"])
        orchestrator.submit_experiment(
            experiment_id=new_exp_id,
            name=f"Rerun of {exp['name']}",
            config=cfg,
            seeds=failed_seeds,
            agent_type=exp["agent_type"],
            provider_model=exp.get("provider_model"),
            gemini_api_key=settings.GEMINI_API_KEY,
        )
        return {"new_experiment_id": new_exp_id, "seeds": failed_seeds, "status": "queued"}

    # --- Runs & Events ---
    @router.get("/experiments/{exp_id}/runs")
    def list_runs(exp_id: str) -> Dict[str, Any]:
        runs = repository.list_runs_for_experiment(exp_id)
        return {"runs": runs, "count": len(runs)}

    @router.get("/runs/{run_id}")
    def get_run(run_id: str) -> Dict[str, Any]:
        run = repository.get_run(run_id)
        if not run:
            raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
        return run

    @router.get("/runs/{run_id}/events")
    def get_run_events(
        run_id: str,
        min_seq: int = Query(0, ge=0),
        limit: int = Query(500, ge=1, le=2000),
        type: Optional[str] = None,
    ) -> Dict[str, Any]:
        events = repository.get_events_for_run(run_id=run_id, min_seq=min_seq, limit=limit, event_type=type)
        return {"events": events, "count": len(events)}

    @router.get("/runs/{run_id}/messages/{msg_id}/lifecycle")
    def get_message_lifecycle(run_id: str, msg_id: str) -> Dict[str, Any]:
        events = repository.get_message_lifecycle(run_id=run_id, msg_id=msg_id)
        return {"msg_id": msg_id, "lifecycle": events}

    # --- Analytics & Statistics ---
    @router.get("/analytics/summary")
    def get_analytics_summary(
        experiment_id: Optional[str] = None,
        paired_fault_free_only: bool = False,
    ) -> Dict[str, Any]:
        """Calculates aggregated metrics across modes with Wilson CIs, McNemar tests, and bootstrap CIs."""
        if experiment_id:
            all_runs = repository.list_runs_for_experiment(experiment_id)
        else:
            # Query recent runs
            experiments = repository.list_experiments(limit=5)
            all_runs = []
            for e in experiments:
                all_runs.extend(repository.list_runs_for_experiment(e["id"]))

        if not all_runs:
            return {"modes": {}, "comparison": {}, "paired_fault_free_only": paired_fault_free_only}

        # Filter for paired fault-free seeds if requested
        valid_seeds_filter = None
        if paired_fault_free_only:
            ff_runs = [r for r in all_runs if r["mode"] == "fault_free_reference"]
            solvable_seeds = set(r["seed"] for r in ff_runs if r["validation_valid"])
            valid_seeds_filter = solvable_seeds

        runs_by_mode: Dict[str, List[Dict[str, Any]]] = {}
        for r in all_runs:
            m = r["mode"]
            if m == "fault_free_reference":
                continue
            if valid_seeds_filter is not None and r["seed"] not in valid_seeds_filter:
                continue
            runs_by_mode.setdefault(m, []).append(r)

        modes_summary = {}
        for m, m_runs in runs_by_mode.items():
            n = len(m_runs)
            valid_count = sum(1 for r in m_runs if r["validation_valid"])
            p_val, ci_low, ci_high = wilson_score_interval(valid_count, n)
            
            sim_times = [r["simulated_time"] for r in m_runs if r["status"] == "completed"]
            mean_sim, boot_low, boot_high = bootstrap_confidence_interval(sim_times)
            med_sim, q25_sim, q75_sim = calculate_median_and_iqr(sim_times)

            # Communication metrics
            total_msgs = [r["metrics_summary"].get("messages_sent", 0) for r in m_runs]
            mean_msgs, _, _ = bootstrap_confidence_interval([float(x) for x in total_msgs])

            recovery_rates = [r["metrics_summary"].get("recovery_success_rate", 1.0) for r in m_runs]
            mean_rec = (sum(recovery_rates) / len(recovery_rates)) if recovery_rates else 1.0

            deadlocks = sum(1 for r in m_runs if r["termination_reason"] in ("deadlock", "stall"))
            deadlock_rate, _, _ = wilson_score_interval(deadlocks, n)

            modes_summary[m] = {
                "n": n,
                "valid_count": valid_count,
                "valid_rate": round(p_val, 4),
                "valid_rate_ci_lower": round(ci_low, 4),
                "valid_rate_ci_upper": round(ci_high, 4),
                "deadlock_count": deadlocks,
                "deadlock_rate": round(deadlock_rate, 4),
                "mean_simulated_time": round(mean_sim, 2),
                "simulated_time_ci_lower": round(boot_low, 2),
                "simulated_time_ci_upper": round(boot_high, 2),
                "median_simulated_time": round(med_sim, 2),
                "iqr_simulated_time": round(q75_sim - q25_sim, 2),
                "mean_messages_sent": round(mean_msgs, 2),
                "recovery_success_rate": round(mean_rec, 4),
            }

        # Paired McNemar Test (Baseline vs Protected, and Timeout vs Protected)
        pairs_mcnemar = {}
        seeds_set = sorted(list(set(r["seed"] for r in all_runs)))
        for base_mode in ("baseline", "timeout_baseline"):
            if base_mode in runs_by_mode and "protected" in runs_by_mode:
                mode_a_by_seed = {r["seed"]: r["validation_valid"] for r in runs_by_mode[base_mode]}
                mode_c_by_seed = {r["seed"]: r["validation_valid"] for r in runs_by_mode["protected"]}
                
                common_seeds = [s for s in seeds_set if s in mode_a_by_seed and s in mode_c_by_seed]
                paired_tuples = [(mode_a_by_seed[s], mode_c_by_seed[s]) for s in common_seeds]
                test_res = mcnemar_exact_test(paired_tuples)
                pairs_mcnemar[f"{base_mode}_vs_protected"] = test_res

        return {
            "modes": modes_summary,
            "paired_tests": pairs_mcnemar,
            "paired_fault_free_only": paired_fault_free_only,
        }

    # --- CSV Exports ---
    @router.get("/experiments/{exp_id}/export.csv")
    def export_experiment_csv(exp_id: str) -> Response:
        exp = repository.get_experiment(exp_id)
        if not exp:
            raise HTTPException(status_code=404, detail="Experiment not found")
        runs = repository.list_runs_for_experiment(exp_id)

        output = io.StringIO()
        writer = csv.writer(output)

        headers = [
            "run_id", "experiment_id", "mode", "seed", "agent_type", "provider_model",
            "status", "outcome", "termination_reason", "validation_valid", "violations_count",
            "simulated_time_virtual_units", "wall_ms", "messages_sent_count",
            "messages_delivered_count", "messages_dropped_count", "acks_sent_count",
            "acks_received_count", "retransmissions_count", "timeouts_count",
            "recovery_success_rate", "schema_version", "code_version"
        ]
        writer.writerow([sanitize_csv_cell(h) for h in headers])

        for r in runs:
            m = r["metrics_summary"]
            row = [
                r["id"],
                r["experiment_id"],
                r["mode"],
                r["seed"],
                exp["agent_type"],
                exp.get("provider_model") or "none",
                r["status"],
                r["outcome"],
                r["termination_reason"],
                1 if r["validation_valid"] else 0,
                r["violations_count"],
                r["simulated_time"],
                r["wall_ms"],
                m.get("messages_sent", 0),
                m.get("messages_delivered", 0),
                m.get("messages_dropped", 0),
                m.get("acks_sent", 0),
                m.get("acks_received", 0),
                m.get("retransmissions", 0),
                m.get("timeouts", 0),
                m.get("recovery_success_rate", 1.0),
                exp["schema_version"],
                exp["code_version"],
            ]
            writer.writerow([sanitize_csv_cell(val) for val in row])

        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=experiment_{exp_id}_runs.csv"},
        )

    @router.get("/runs/{run_id}/events.csv")
    def export_events_csv(run_id: str) -> Response:
        run = repository.get_run(run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")
        events = repository.get_events_for_run(run_id=run_id, min_seq=0, limit=5000)

        output = io.StringIO()
        writer = csv.writer(output)
        headers = ["seq", "sim_time_virtual_units", "type", "agent_id", "target_agent_id", "msg_id", "payload_json"]
        writer.writerow([sanitize_csv_cell(h) for h in headers])

        for e in events:
            row = [
                e["seq"],
                e["sim_time"],
                e["type"],
                e.get("agent_id") or "",
                e.get("target_agent_id") or "",
                e.get("msg_id") or "",
                json.dumps(e.get("payload", {})),
            ]
            writer.writerow([sanitize_csv_cell(val) for val in row])

        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=run_{run_id}_events.csv"},
        )

    # --- LLM Connection Test ---
    @router.post("/llm/test-connection")
    def test_llm_connection(req: ConnectionTestRequest) -> Dict[str, Any]:
        api_key = req.gemini_api_key or settings.GEMINI_API_KEY
        if not api_key or api_key.strip() == "":
            return {
                "success": False,
                "configured": False,
                "message": "No API key configured. Provide a key or set GEMINI_API_KEY in .env.",
            }

        try:
            import httpx
            model = req.provider_model or settings.GEMINI_MODEL
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
            req_body = {
                "contents": [{"parts": [{"text": "Say hello in one word."}]}],
            }
            resp = httpx.post(url, json=req_body, timeout=5.0)
            if resp.status_code == 200:
                return {
                    "success": True,
                    "configured": True,
                    "model": model,
                    "message": "Connection verified successfully.",
                }
            else:
                return {
                    "success": False,
                    "configured": True,
                    "status_code": resp.status_code,
                    "message": f"API returned status {resp.status_code}",
                }
        except Exception as ex:
            return {
                "success": False,
                "configured": True,
                "error_class": type(ex).__name__,
                "message": f"Connection test failed: {str(ex)[:100]}",
            }

    return router
