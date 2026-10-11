import pytest
import tempfile
from pathlib import Path
from app.db.database import init_db
from app.db.repository import Repository

@pytest.fixture
def temp_repo():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(db_path)
        repo = Repository(db_path)
        yield repo

def test_experiment_crud_and_runs(temp_repo):
    repo = temp_repo
    exp_id = "exp_test_001"
    repo.create_experiment(
        exp_id=exp_id,
        name="Test Experiment",
        config={"problem": {"num_agents": 3}},
        seeds=[42, 43],
        agent_type="deterministic",
        provider_model=None,
        total_runs=2,
    )

    exp = repo.get_experiment(exp_id)
    assert exp is not None
    assert exp["name"] == "Test Experiment"
    assert exp["seeds"] == [42, 43]

    # Create run
    run_id = "run_test_001"
    repo.create_run(run_id, exp_id, "baseline", 42)
    repo.update_run_started(run_id)

    # Insert events batch
    events = [
        {"run_id": run_id, "seq": 1, "sim_time": 0.0, "type": "SEND", "agent_id": "agent_0", "msg_id": "m1", "payload": {}},
        {"run_id": run_id, "seq": 2, "sim_time": 1.0, "type": "DELIVER", "agent_id": "agent_1", "msg_id": "m1", "payload": {}},
    ]
    repo.insert_events_batch(events)

    ev_fetch = repo.get_events_for_run(run_id)
    assert len(ev_fetch) == 2
    assert ev_fetch[0]["type"] == "SEND"

    lifecycle = repo.get_message_lifecycle(run_id, "m1")
    assert len(lifecycle) == 2

def test_startup_reconciliation_marks_interrupted(temp_repo):
    repo = temp_repo
    exp_id = "exp_restart_test"
    repo.create_experiment(
        exp_id=exp_id,
        name="Restart Test",
        config={},
        seeds=[1],
        agent_type="deterministic",
        provider_model=None,
        total_runs=1,
    )
    run_id = "run_restart_test"
    repo.create_run(run_id, exp_id, "baseline", 1)
    repo.update_run_started(run_id)

    # Verify currently running
    run_before = repo.get_run(run_id)
    assert run_before["status"] == "running"

    # Simulate server restart reconciliation
    affected = repo.reconcile_startup_interrupted_runs()
    assert affected == 1

    run_after = repo.get_run(run_id)
    assert run_after["status"] == "interrupted"
    assert run_after["outcome"] == "interrupted"
    assert "Server restarted" in run_after["termination_reason"]

    exp_after = repo.get_experiment(exp_id)
    assert exp_after["status"] == "interrupted"
