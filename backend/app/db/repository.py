import json
import sqlite3
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from app.db.database import get_db_connection

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

class Repository:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path

    # --- System & Restart Reconciliation ---
    def reconcile_startup_interrupted_runs(self) -> int:
        """Marks any running or queued experiments/runs as interrupted upon server restart."""
        with get_db_connection(self.db_path) as conn:
            now = utc_now_iso()
            cursor = conn.cursor()
            # Update runs
            cursor.execute(
                """
                UPDATE runs
                SET status = 'interrupted',
                    outcome = 'interrupted',
                    termination_reason = 'Server restarted while run was in progress',
                    ended_at = ?
                WHERE status IN ('queued', 'running');
                """,
                (now,),
            )
            affected_runs = cursor.rowcount
            # Update experiments
            cursor.execute(
                """
                UPDATE experiments
                SET status = 'interrupted',
                    error_message = 'Backend restarted while experiment was active'
                WHERE status IN ('queued', 'running');
                """
            )
            return affected_runs

    def get_database_stats(self) -> Dict[str, Any]:
        """Returns database file size and row counts."""
        from app.config import settings
        path = self.db_path or settings.DATABASE_PATH
        size_bytes = os.path.getsize(path) if os.path.exists(path) else 0
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            exp_count = cursor.execute("SELECT COUNT(*) FROM experiments").fetchone()[0]
            run_count = cursor.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
            event_count = cursor.execute("SELECT COUNT(*) FROM events").fetchone()[0]
            llm_count = cursor.execute("SELECT COUNT(*) FROM llm_calls").fetchone()[0]
        return {
            "size_bytes": size_bytes,
            "size_mb": round(size_bytes / (1024 * 1024), 2),
            "experiments_count": exp_count,
            "runs_count": run_count,
            "events_count": event_count,
            "llm_calls_count": llm_count,
        }

    # --- Experiments ---
    def create_experiment(
        self,
        exp_id: str,
        name: str,
        config: Dict[str, Any],
        seeds: List[int],
        agent_type: str,
        provider_model: Optional[str],
        total_runs: int,
        code_version: str = "1.0.0",
        schema_version: str = "1.0",
    ) -> None:
        with get_db_connection(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO experiments (
                    id, name, created_at, status, config_json, seeds_json,
                    agent_type, provider_model, code_version, schema_version,
                    total_runs, completed_runs
                ) VALUES (?, ?, ?, 'queued', ?, ?, ?, ?, ?, ?, ?, 0);
                """,
                (
                    exp_id,
                    name,
                    utc_now_iso(),
                    json.dumps(config),
                    json.dumps(seeds),
                    agent_type,
                    provider_model,
                    code_version,
                    schema_version,
                    total_runs,
                ),
            )

    def get_experiment(self, exp_id: str) -> Optional[Dict[str, Any]]:
        with get_db_connection(self.db_path) as conn:
            row = conn.execute("SELECT * FROM experiments WHERE id = ?", (exp_id,)).fetchone()
            if not row:
                return None
            res = dict(row)
            res["config"] = json.loads(res["config_json"])
            res["seeds"] = json.loads(res["seeds_json"])
            return res

    def list_experiments(
        self,
        limit: int = 50,
        offset: int = 0,
        status: Optional[str] = None,
        agent_type: Optional[str] = None,
        search: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        query = "SELECT * FROM experiments WHERE 1=1"
        params: List[Any] = []
        if status:
            query += " AND status = ?"
            params.append(status)
        if agent_type:
            query += " AND agent_type = ?"
            params.append(agent_type)
        if search:
            query += " AND (name LIKE ? OR id LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%"])
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        with get_db_connection(self.db_path) as conn:
            rows = conn.execute(query, params).fetchall()
            out = []
            for r in rows:
                item = dict(r)
                item["config"] = json.loads(item["config_json"])
                item["seeds"] = json.loads(item["seeds_json"])
                out.append(item)
            return out

    def update_experiment_status(
        self,
        exp_id: str,
        status: str,
        completed_runs: Optional[int] = None,
        error_message: Optional[str] = None,
    ) -> None:
        with get_db_connection(self.db_path) as conn:
            if completed_runs is not None:
                conn.execute(
                    """
                    UPDATE experiments
                    SET status = ?, completed_runs = ?, error_message = COALESCE(?, error_message)
                    WHERE id = ?;
                    """,
                    (status, completed_runs, error_message, exp_id),
                )
            else:
                conn.execute(
                    """
                    UPDATE experiments
                    SET status = ?, error_message = COALESCE(?, error_message)
                    WHERE id = ?;
                    """,
                    (status, error_message, exp_id),
                )

    def delete_experiment(self, exp_id: str) -> bool:
        with get_db_connection(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM experiments WHERE id = ?", (exp_id,))
            return cursor.rowcount > 0

    # --- Runs ---
    def create_run(
        self,
        run_id: str,
        experiment_id: str,
        mode: str,
        seed: int,
    ) -> None:
        with get_db_connection(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO runs (
                    id, experiment_id, mode, seed, status, outcome,
                    termination_reason, started_at
                ) VALUES (?, ?, ?, ?, 'queued', 'pending', 'pending', ?);
                """,
                (run_id, experiment_id, mode, seed, utc_now_iso()),
            )

    def update_run_started(self, run_id: str) -> None:
        with get_db_connection(self.db_path) as conn:
            conn.execute(
                "UPDATE runs SET status = 'running', started_at = ? WHERE id = ?",
                (utc_now_iso(), run_id),
            )

    def complete_run(
        self,
        run_id: str,
        status: str,
        outcome: str,
        termination_reason: str,
        simulated_time: float,
        wall_ms: float,
        validation_valid: bool,
        violations_count: int,
        metrics_summary: Dict[str, Any],
        error_message: Optional[str] = None,
    ) -> None:
        with get_db_connection(self.db_path) as conn:
            conn.execute(
                """
                UPDATE runs
                SET status = ?,
                    outcome = ?,
                    termination_reason = ?,
                    ended_at = ?,
                    simulated_time = ?,
                    wall_ms = ?,
                    validation_valid = ?,
                    violations_count = ?,
                    metrics_summary_json = ?,
                    error_message = ?
                WHERE id = ?;
                """,
                (
                    status,
                    outcome,
                    termination_reason,
                    utc_now_iso(),
                    simulated_time,
                    wall_ms,
                    1 if validation_valid else 0,
                    violations_count,
                    json.dumps(metrics_summary),
                    error_message,
                    run_id,
                ),
            )

    def get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        with get_db_connection(self.db_path) as conn:
            row = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
            if not row:
                return None
            res = dict(row)
            res["validation_valid"] = bool(res["validation_valid"])
            res["metrics_summary"] = json.loads(res["metrics_summary_json"])
            return res

    def list_runs_for_experiment(self, experiment_id: str) -> List[Dict[str, Any]]:
        with get_db_connection(self.db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM runs WHERE experiment_id = ? ORDER BY seed ASC, mode ASC",
                (experiment_id,),
            ).fetchall()
            out = []
            for r in rows:
                item = dict(r)
                item["validation_valid"] = bool(item["validation_valid"])
                item["metrics_summary"] = json.loads(item["metrics_summary_json"])
                out.append(item)
            return out

    # --- Events ---
    def insert_events_batch(self, events: List[Dict[str, Any]]) -> None:
        if not events:
            return
        records = [
            (
                e["run_id"],
                e["seq"],
                e["sim_time"],
                e["type"],
                e.get("agent_id"),
                e.get("target_agent_id"),
                e.get("msg_id"),
                json.dumps(e.get("payload", {})),
            )
            for e in events
        ]
        with get_db_connection(self.db_path) as conn:
            conn.executemany(
                """
                INSERT INTO events (
                    run_id, seq, sim_time, type, agent_id, target_agent_id, msg_id, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                records,
            )

    def get_events_for_run(
        self,
        run_id: str,
        min_seq: int = 0,
        limit: int = 500,
        event_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        query = "SELECT * FROM events WHERE run_id = ? AND seq >= ?"
        params: List[Any] = [run_id, min_seq]
        if event_type:
            query += " AND type = ?"
            params.append(event_type)
        query += " ORDER BY seq ASC LIMIT ?"
        params.append(limit)

        with get_db_connection(self.db_path) as conn:
            rows = conn.execute(query, params).fetchall()
            out = []
            for r in rows:
                item = dict(r)
                item["payload"] = json.loads(item["payload_json"])
                out.append(item)
            return out

    def get_message_lifecycle(self, run_id: str, msg_id: str) -> List[Dict[str, Any]]:
        with get_db_connection(self.db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM events WHERE run_id = ? AND msg_id = ? ORDER BY seq ASC",
                (run_id, msg_id),
            ).fetchall()
            out = []
            for r in rows:
                item = dict(r)
                item["payload"] = json.loads(item["payload_json"])
                out.append(item)
            return out

    # --- LLM Calls ---
    def record_llm_call(
        self,
        run_id: str,
        agent_id: str,
        prompt_hash: str,
        latency_ms: float,
        tokens_used: int,
        is_fallback: bool,
        error_class: Optional[str] = None,
        is_cached: bool = False,
    ) -> None:
        with get_db_connection(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO llm_calls (
                    run_id, agent_id, prompt_hash, latency_ms, tokens_used,
                    is_fallback, error_class, is_cached, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    run_id,
                    agent_id,
                    prompt_hash,
                    latency_ms,
                    tokens_used,
                    1 if is_fallback else 0,
                    error_class,
                    1 if is_cached else 0,
                    utc_now_iso(),
                ),
            )

    def get_llm_calls_for_run(self, run_id: str) -> List[Dict[str, Any]]:
        with get_db_connection(self.db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM llm_calls WHERE run_id = ? ORDER BY id ASC",
                (run_id,),
            ).fetchall()
            return [dict(r) for r in rows]
