"""Pydantic schemas and data contracts for AERIS telemetry and diagnostics."""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

class TelemetryInput(BaseModel):
    uav_id: str = Field(default="UAV-MALE-01", description="UAV airframe identifier")
    timestamp: float = Field(..., description="Unix epoch or mission timestamp in seconds")
    rpm: float = Field(..., ge=0.0, le=7000.0, description="Crankshaft speed in RPM")
    cht_c: float = Field(..., description="Cylinder Head Temperature in Celsius")
    egt_c: float = Field(..., description="Exhaust Gas Temperature in Celsius")
    oil_pressure_bar: float = Field(..., description="Engine lubrication pressure in bar")
    oil_temp_c: float = Field(..., description="Oil sump temperature in Celsius")
    fuel_flow_lph: float = Field(..., ge=0.0, description="Fuel consumption rate in L/h")
    vibration_mms: float = Field(..., ge=0.0, description="Vibration velocity RMS in mm/s")
    battery_v: float = Field(default=14.2, description="Bus/Alternator voltage in Volts")
    injection_timing_deg: float = Field(default=-22.0, description="Injection timing in degrees BTDC")
    throttle: float = Field(..., ge=0.0, le=1.0, description="Throttle demand 0.0 to 1.0")
    altitude_m: float = Field(default=1500.0, description="Pressure altitude in meters")
    ambient_temp_c: float = Field(default=18.0, description="Ambient air temperature in Celsius")
    engine_load: float = Field(default=0.75, ge=0.0, le=1.0, description="Engine load factor 0.0 to 1.0")

class TwinPredictionOutput(BaseModel):
    egt_c: float
    cht_c: float
    oil_pressure_bar: float
    oil_temp_c: float
    fuel_flow_lph: float
    vibration_mms: float
    engine_efficiency: float
    manifold_pressure_inhg: float
    air_density_kgm3: float
    brake_power_kw: float

class ResidualsOutput(BaseModel):
    egt_residual: float
    cht_residual: float
    oil_pressure_residual: float
    oil_temp_residual: float
    fuel_flow_residual: float
    vibration_residual: float
    z_egt: float
    z_cht: float
    z_oil_pressure: float
    z_oil_temp: float
    z_fuel_flow: float
    z_vibration: float
    pct_egt: float
    pct_cht: float
    pct_oil_pressure: float
    pct_oil_temp: float
    pct_fuel_flow: float
    pct_vibration: float

class DiagnosticsSummary(BaseModel):
    is_anomaly: bool
    anomaly_score: float
    anomaly_severity: str
    affected_sensors: List[str]
    predicted_fault: str
    confidence: float
    fault_severity: str
    health_index: float
    health_status: str
    estimated_rul_hours: float
    rul_confidence_lower: float
    rul_confidence_upper: float
    all_sensors_valid: bool
    sensor_drift_warnings: List[str]
    maintenance_action: str
    explanation_summary: str

class FullEngineSnapshot(BaseModel):
    telemetry: TelemetryInput
    digital_twin: TwinPredictionOutput
    residuals: ResidualsOutput
    diagnostics: DiagnosticsSummary
