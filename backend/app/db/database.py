import sqlite3
import os
from pathlib import Path
from contextlib import contextmanager
from typing import Generator
from app.config import settings

def init_db(db_path: Path | None = None) -> None:
    """Initializes SQLite database with WAL mode and schema."""
    path = db_path or settings.DATABASE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(str(path), timeout=settings.SQLITE_TIMEOUT_SECONDS)
    try:
        cursor = conn.cursor()
        # Enable WAL mode and foreign keys
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA foreign_keys=ON;")
        cursor.execute("PRAGMA busy_timeout=10000;")
        
        # Experiments table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS experiments (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            created_at TEXT NOT NULL,
            status TEXT NOT NULL,
            config_json TEXT NOT NULL,
            seeds_json TEXT NOT NULL,
            agent_type TEXT NOT NULL,
            provider_model TEXT,
            code_version TEXT NOT NULL,
            schema_version TEXT NOT NULL,
            total_runs INTEGER NOT NULL DEFAULT 0,
            completed_runs INTEGER NOT NULL DEFAULT 0,
            error_message TEXT
        );
        """)

        # Runs table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS runs (
            id TEXT PRIMARY KEY,
            experiment_id TEXT NOT NULL,
            mode TEXT NOT NULL,
            seed INTEGER NOT NULL,
            status TEXT NOT NULL,
            outcome TEXT NOT NULL,
            termination_reason TEXT NOT NULL,
            started_at TEXT NOT NULL,
            ended_at TEXT,
            simulated_time REAL NOT NULL DEFAULT 0.0,
            wall_ms REAL NOT NULL DEFAULT 0.0,
            validation_valid INTEGER NOT NULL DEFAULT 0,
            violations_count INTEGER NOT NULL DEFAULT 0,
            metrics_summary_json TEXT NOT NULL DEFAULT '{}',
            error_message TEXT,
            FOREIGN KEY (experiment_id) REFERENCES experiments (id) ON DELETE CASCADE
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_runs_experiment ON runs(experiment_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_runs_mode_seed ON runs(mode, seed);")

        # Events table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            seq INTEGER NOT NULL,
            sim_time REAL NOT NULL,
            type TEXT NOT NULL,
            agent_id TEXT,
            target_agent_id TEXT,
            msg_id TEXT,
            payload_json TEXT NOT NULL DEFAULT '{}',
            FOREIGN KEY (run_id) REFERENCES runs (id) ON DELETE CASCADE
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_run_seq ON events(run_id, seq);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_type ON events(type);")

        # LLM Calls table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS llm_calls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            agent_id TEXT NOT NULL,
            prompt_hash TEXT NOT NULL,
            latency_ms REAL NOT NULL,
            tokens_used INTEGER NOT NULL DEFAULT 0,
            is_fallback INTEGER NOT NULL DEFAULT 0,
            error_class TEXT,
            is_cached INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            FOREIGN KEY (run_id) REFERENCES runs (id) ON DELETE CASCADE
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_llm_run ON llm_calls(run_id);")

        conn.commit()
    finally:
        conn.close()

@contextmanager
def get_db_connection(db_path: Path | None = None) -> Generator[sqlite3.Connection, None, None]:
    """Context manager for SQLite connection with configured pragmas."""
    path = db_path or settings.DATABASE_PATH
    conn = sqlite3.connect(str(path), timeout=settings.SQLITE_TIMEOUT_SECONDS)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA foreign_keys=ON;")
        conn.execute("PRAGMA busy_timeout=10000;")
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
