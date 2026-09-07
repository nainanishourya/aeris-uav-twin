"""Integration tests for AERIS FastAPI endpoints."""

import pytest
from fastapi.testclient import TestClient
from aeris.api.main import app

client = TestClient(app)

def test_api_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ONLINE"
    assert "engine_health_index" in data

def test_api_telemetry_latest():
    response = client.get("/api/telemetry/latest")
    assert response.status_code == 200
    data = response.json()
    assert "rpm" in data
    assert "cht_c" in data
    assert "egt_c" in data
    assert "twin_egt_c" in data
    assert "res_egt" in data

def test_api_rul():
    response = client.get("/api/rul")
    assert response.status_code == 200
    data = response.json()
    assert "estimated_rul_hours" in data
    assert "confidence_interval_hours" in data

def test_api_simulation_run():
    payload = {
        "preset_name": "Normal ISR",
        "duration_hours": 6.0,
        "cruise_altitude_m": 2500.0,
        "ambient_temp_c": 18.0,
        "cruise_throttle": 0.70,
        "throttle_transients": False,
        "initial_health": 95.0
    }
    response = client.post("/api/simulation/run", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["mission_risk_score"] in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    assert "trajectory" in data

def test_api_demo_start():
    response = client.post("/api/demo/start")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "STARTED"
