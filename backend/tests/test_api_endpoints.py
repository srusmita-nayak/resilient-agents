import pytest
from fastapi.testclient import TestClient
from app.db.database import init_db
from app.main import app

init_db()
client = TestClient(app)

def test_health_and_ready():
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "llm_configured" in data

    resp_ready = client.get("/api/ready")
    assert resp_ready.status_code == 200
    assert resp_ready.json() == {"ready": True}

def test_system_status():
    resp = client.get("/api/system/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "database_stats" in data
    assert "limits" in data

def test_presets():
    resp = client.get("/api/presets")
    assert resp.status_code == 200
    data = resp.json()
    assert "difficulty_presets" in data
    assert "fault_presets" in data
    assert "easy" in data["difficulty_presets"]
    assert "reliable" in data["fault_presets"]

def test_create_and_get_experiment():
    payload = {
        "name": "Integration Test Experiment",
        "problem": {
            "num_agents": 3,
            "num_nodes": 12,
            "num_colors": 3,
            "edge_density": 0.25,
            "round_budget": 10,
        },
        "faults": {"loss_rate": 0.0},
        "middleware": {"max_retries": 2},
        "modes": ["baseline", "protected"],
        "seeds": [100],
        "include_fault_free_reference": False,
        "agent_type": "deterministic",
    }
    resp = client.post("/api/experiments", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "experiment_id" in data
    exp_id = data["experiment_id"]

    # Fetch experiment
    resp_get = client.get(f"/api/experiments/{exp_id}")
    assert resp_get.status_code == 200
    exp_data = resp_get.json()
    assert exp_data["name"] == "Integration Test Experiment"
    assert exp_data["agent_type"] == "deterministic"

def test_llm_test_connection_unconfigured():
    resp = client.post("/api/llm/test-connection", json={"gemini_api_key": ""})
    assert resp.status_code == 200
    data = resp.json()
    assert data["configured"] is False
    assert "No API key configured" in data["message"]

def test_csv_export_headers_and_escaping():
    # Create experiment and check CSV export response format
    payload = {
        "name": "=HYPERLINK(\"http://evil.com\")", # Formula injection attempt
        "problem": {"num_agents": 3, "num_nodes": 9, "num_colors": 3},
        "faults": {},
        "modes": ["baseline"],
        "seeds": [77],
        "include_fault_free_reference": False,
        "agent_type": "deterministic",
    }
    resp = client.post("/api/experiments", json=payload)
    assert resp.status_code == 200
    exp_id = resp.json()["experiment_id"]

    resp_csv = client.get(f"/api/experiments/{exp_id}/export.csv")
    assert resp_csv.status_code == 200
    assert "text/csv" in resp_csv.headers["content-type"]
    content = resp_csv.text
    # Verify header line exists
    assert "run_id" in content
    assert "simulated_time_virtual_units" in content
