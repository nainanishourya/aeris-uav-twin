"""FastAPI REST API Server for AERIS Ground Control Station & External Integrations."""

import io
from typing import Dict, List, Any, Optional
import pandas as pd
from fastapi import FastAPI, HTTPException, Query, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from aeris.config.settings import settings
from aeris.telemetry.schemas import TelemetryInput, DiagnosticsSummary, FullEngineSnapshot
from aeris.telemetry.database import AerisDatabase
from aeris.telemetry.simulator import simulator
from aeris.mission.simulator import MissionSimulator, MissionProfile, MISSION_PRESETS
from aeris.ml.data_generator import FAULT_CLASSES

app = FastAPI(
    title="AERIS API - AI Engine Reliability & Intelligence System",
    description="Physics-Anchored Digital Twin & AI Health Platform for MALE UAV Aero-Piston Engines (SIH26054 DRDO)",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Enable CORS for external frontend or ground control integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

db = AerisDatabase()
mission_sim = MissionSimulator()


@app.get("/", include_in_schema=False)
def get_api_home():
    """Provides a compact landing response for the deployed API."""
    return {
        "name": "AERIS API",
        "status": "ONLINE",
        "docs": "/docs",
        "health": "/api/health",
    }

# ----------------- REQUEST SCHEMAS -----------------

class OperatingPointRequest(BaseModel):
    throttle: Optional[float] = Field(None, ge=0.0, le=1.0, description="Throttle position 0.0 to 1.0")
    altitude_m: Optional[float] = Field(None, ge=0.0, le=10000.0, description="Altitude in meters")
    ambient_temp_c: Optional[float] = Field(None, ge=-50.0, le=60.0, description="Ambient temp in C")
    fault: Optional[str] = Field(None, description="Fault to inject: Healthy, Misfire, Injector Abnormality, etc.")
    severity: Optional[float] = Field(None, ge=0.0, le=2.0, description="Fault severity multiplier")

class MissionRunRequest(BaseModel):
    preset_name: Optional[str] = Field("Normal ISR", description="Preset name or 'Custom'")
    duration_hours: float = Field(8.0, ge=0.5, le=36.0)
    cruise_altitude_m: float = Field(3000.0, ge=100.0, le=9000.0)
    ambient_temp_c: float = Field(15.0, ge=-50.0, le=55.0)
    cruise_throttle: float = Field(0.72, ge=0.3, le=1.0)
    throttle_transients: bool = Field(False)
    initial_health: float = Field(95.0, ge=10.0, le=100.0)

# ----------------- API ENDPOINTS -----------------

@app.get("/api/health", summary="System and Engine Health Status")
def get_system_health():
    """Returns the current composite health index, sub-indices, and operational status."""
    latest = db.get_latest_telemetry()
    if not latest:
        # Run one simulator step if empty
        step_data = simulator.step()
        latest = db.get_latest_telemetry()

    return {
        "status": "ONLINE",
        "uav_id": settings.mqtt_uav_id,
        "engine_health_index": latest.get("health_index", 100.0),
        "health_status": latest.get("health_status", "Healthy"),
        "active_fault": latest.get("predicted_fault", "Healthy"),
        "fault_confidence": latest.get("confidence", 1.0),
        "anomaly_score": latest.get("anomaly_score", 0.0),
        "estimated_rul_hours": latest.get("estimated_rul_hours", 1000.0),
        "maintenance_action": latest.get("maintenance_action", "Nominal operations"),
        "telemetry_stream_active": simulator.is_running
    }

@app.get("/api/telemetry/latest", summary="Latest Real-Time Telemetry Frame")
def get_latest_telemetry():
    """Returns the most recent physical sensor values, digital twin predictions, and residuals."""
    latest = db.get_latest_telemetry()
    if not latest:
        simulator.step()
        latest = db.get_latest_telemetry()
    return latest

@app.get("/api/telemetry/history", summary="Telemetry Time-Series History")
def get_telemetry_history(limit: int = Query(60, ge=5, le=1000)):
    """Fetches chronological telemetry sequence for charting."""
    history = db.get_telemetry_history(limit=limit)
    return {
        "count": len(history),
        "records": history
    }

@app.get("/api/diagnostics", summary="Latest Explainable AI Diagnostics")
def get_diagnostics():
    """Provides detailed diagnostic breakdown, cross-sensor checks, and XAI feature contributions."""
    latest = db.get_latest_telemetry()
    if not latest:
        simulator.step()
        latest = db.get_latest_telemetry()

    return {
        "predicted_fault": latest.get("predicted_fault", "Healthy"),
        "confidence": latest.get("confidence", 1.0),
        "anomaly_score": latest.get("anomaly_score", 0.0),
        "health_index": latest.get("health_index", 100.0),
        "health_status": latest.get("health_status", "Healthy"),
        "estimated_rul_hours": latest.get("estimated_rul_hours", 1000.0),
        "maintenance_action": latest.get("maintenance_action", ""),
        "residuals": {
            "egt": latest.get("res_egt", 0.0),
            "cht": latest.get("res_cht", 0.0),
            "oil_pressure": latest.get("res_oil_p", 0.0),
            "oil_temp": latest.get("res_oil_t", 0.0),
            "fuel_flow": latest.get("res_fuel_flow", 0.0),
            "vibration": latest.get("res_vibration", 0.0)
        }
    }

@app.get("/api/anomalies", summary="Active & Historical Anomaly Events")
def get_anomalies(limit: int = Query(20, ge=1, le=100)):
    """Returns logged maintenance alerts and anomaly events."""
    return db.get_advisories(limit=limit)

@app.get("/api/rul", summary="Remaining Useful Life Estimate")
def get_rul():
    """Returns estimated remaining flight hours, 90% confidence intervals, and degradation rate."""
    latest = db.get_latest_telemetry()
    health = latest.get("health_index", 95.0) if latest else 95.0
    anom = latest.get("anomaly_score", 0.0) if latest else 0.0
    
    rul_eval = simulator.rul_est.estimate(
        current_health_index=health,
        current_flight_hours=simulator.flight_hours,
        anomaly_score=anom
    )
    return rul_eval.to_dict()

@app.post("/api/simulation/run", summary="Run Mission Profile Simulation")
def run_mission_simulation(req: MissionRunRequest):
    """Simulates forward mission trajectory, degradation progression, and mission risk tier."""
    if req.preset_name in MISSION_PRESETS and req.preset_name != "Custom":
        profile = MISSION_PRESETS[req.preset_name]
        profile.initial_health_index = req.initial_health
    else:
        profile = MissionProfile(
            name="Custom Mission",
            description="User configured flight profile",
            duration_hours=req.duration_hours,
            cruise_altitude_m=req.cruise_altitude_m,
            ambient_temp_c=req.ambient_temp_c,
            cruise_throttle=req.cruise_throttle,
            throttle_transients=req.throttle_transients,
            initial_health_index=req.initial_health
        )

    res = mission_sim.run_simulation(profile)
    # Save to db
    db.record_mission_simulation(res.to_dict())
    return res.to_dict()

@app.post("/api/demo/start", summary="Start 1-Click Injector Degradation Demo")
def start_demo():
    """Initiates reproducible demonstration starting at Health=96 and progressively injecting injector fault."""
    simulator.start_demo_scenario()
    return {
        "status": "STARTED",
        "scenario": "Injector Degradation Divergence",
        "description": "Engine starts at Health=96. Twin diverges, residual rises, anomaly flagged, health drops, and predictive maintenance triggered."
    }

@app.post("/api/control/operating-point", summary="Set Simulator Operating Point or Fault")
def set_operating_point(req: OperatingPointRequest):
    """Adjusts simulator throttle, altitude, temperature, or injects a specific fault mode."""
    if req.fault and req.fault not in FAULT_CLASSES:
        raise HTTPException(status_code=400, detail=f"Invalid fault class. Supported: {FAULT_CLASSES}")
        
    simulator.set_operating_point(
        throttle=req.throttle,
        altitude_m=req.altitude_m,
        ambient_temp_c=req.ambient_temp_c,
        fault=req.fault,
        severity=req.severity
    )
    return {
        "status": "UPDATED",
        "current_fault": simulator.current_fault,
        "fault_severity": simulator.fault_severity,
        "throttle": simulator.throttle,
        "altitude_m": simulator.altitude_m
    }

@app.post("/api/replay/upload", summary="Upload Historical Telemetry CSV for Replay")
async def upload_replay_csv(file: UploadFile = File(...)):
    """Uploads historical telemetry CSV for synchronized playback."""
    contents = await file.read()
    try:
        df = pd.read_csv(io.BytesIO(contents))
        required = ["rpm", "cht_c", "egt_c", "oil_pressure_bar", "oil_temp_c", "fuel_flow_lph", "vibration_mms"]
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise HTTPException(status_code=400, detail=f"Missing required sensor columns: {missing}")
        
        # Save uploaded file
        save_path = settings.data_dir / f"replay_{file.filename}"
        df.to_csv(save_path, index=False)
        return {
            "status": "SUCCESS",
            "filename": file.filename,
            "rows": len(df),
            "columns": list(df.columns)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error parsing CSV: {e}")

@app.get("/api/models/info", summary="Machine Learning Model Metadata & Evaluation")
def get_models_info():
    """Returns training parameters, precision, recall, and confusion matrix from evaluation."""
    metrics_path = settings.models_dir / "evaluation_metrics.json"
    if metrics_path.exists():
        import json
        with open(metrics_path, "r") as f:
            return json.load(f)
    return {"message": "Models not yet trained or metrics not saved."}
