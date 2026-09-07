"""SQLite Persistence Layer for AERIS Telemetry, Digital Twin, and Diagnostic Records."""

import sqlite3
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from contextlib import contextmanager

from aeris.config.settings import settings

class AerisDatabase:
    """Manages local SQLite database storage for telemetry and analysis."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or settings.db_path
        self._initializing = False
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def _get_connection(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path), timeout=15.0)
        conn.row_factory = sqlite3.Row
        if not self._initializing:
            schema_exists = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='engine_telemetry'"
            ).fetchone()
            if not schema_exists:
                conn.close()
                self._initializing = True
                try:
                    self._init_db()
                finally:
                    self._initializing = False
                conn = sqlite3.connect(str(self.db_path), timeout=15.0)
                conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self):
        """Initializes database schema."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Telemetry & Twin States table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS engine_telemetry (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    uav_id TEXT NOT NULL,
                    rpm REAL NOT NULL,
                    throttle REAL NOT NULL,
                    altitude_m REAL NOT NULL,
                    ambient_temp_c REAL NOT NULL,
                    engine_load REAL NOT NULL,
                    cht_c REAL NOT NULL,
                    egt_c REAL NOT NULL,
                    oil_pressure_bar REAL NOT NULL,
                    oil_temp_c REAL NOT NULL,
                    fuel_flow_lph REAL NOT NULL,
                    vibration_mms REAL NOT NULL,
                    battery_v REAL NOT NULL,
                    injection_timing_deg REAL NOT NULL,
                    twin_egt_c REAL,
                    twin_cht_c REAL,
                    twin_oil_pressure_bar REAL,
                    twin_oil_temp_c REAL,
                    twin_fuel_flow_lph REAL,
                    twin_vibration_mms REAL,
                    res_egt REAL,
                    res_cht REAL,
                    res_oil_p REAL,
                    res_oil_t REAL,
                    res_fuel_flow REAL,
                    res_vibration REAL,
                    z_egt REAL,
                    z_cht REAL,
                    z_oil_p REAL,
                    z_oil_t REAL,
                    z_fuel_flow REAL,
                    z_vibration REAL
                );
            """)

            # Diagnostics & Health table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS health_diagnostics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    uav_id TEXT NOT NULL,
                    health_index REAL NOT NULL,
                    health_status TEXT NOT NULL,
                    thermal_health REAL NOT NULL,
                    lubrication_health REAL NOT NULL,
                    vibration_health REAL NOT NULL,
                    efficiency_health REAL NOT NULL,
                    is_anomaly INTEGER NOT NULL,
                    anomaly_score REAL NOT NULL,
                    anomaly_severity TEXT NOT NULL,
                    predicted_fault TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    fault_severity TEXT NOT NULL,
                    estimated_rul_hours REAL NOT NULL,
                    rul_status TEXT NOT NULL,
                    sensor_drift_flag INTEGER NOT NULL,
                    suspect_sensors TEXT,
                    maintenance_action TEXT,
                    explanation_json TEXT
                );
            """)

            # Mission simulations log table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS mission_simulations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    profile_name TEXT NOT NULL,
                    duration_hours REAL NOT NULL,
                    cruise_altitude_m REAL NOT NULL,
                    ambient_temp_c REAL NOT NULL,
                    throttle_setting REAL NOT NULL,
                    initial_health REAL NOT NULL,
                    final_health REAL NOT NULL,
                    mission_risk_score TEXT NOT NULL,
                    risk_explanation TEXT,
                    rul_delta_hours REAL NOT NULL
                );
            """)

            # Maintenance advisory log table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS maintenance_advisories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    fault_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    evidence TEXT NOT NULL,
                    action_prescribed TEXT NOT NULL,
                    acknowledged INTEGER DEFAULT 0
                );
            """)

            conn.commit()

    def record_snapshot(
        self,
        telemetry: Dict[str, Any],
        twin: Dict[str, Any],
        residuals: Dict[str, Any],
        diagnostics: Dict[str, Any]
    ):
        """Atomically inserts telemetry and diagnostic state."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            ts = telemetry.get("timestamp", datetime.now(timezone.utc).timestamp())
            uav_id = telemetry.get("uav_id", "UAV-MALE-01")

            # 1. Insert Telemetry
            cursor.execute("""
                INSERT INTO engine_telemetry (
                    timestamp, uav_id, rpm, throttle, altitude_m, ambient_temp_c, engine_load,
                    cht_c, egt_c, oil_pressure_bar, oil_temp_c, fuel_flow_lph, vibration_mms,
                    battery_v, injection_timing_deg,
                    twin_egt_c, twin_cht_c, twin_oil_pressure_bar, twin_oil_temp_c,
                    twin_fuel_flow_lph, twin_vibration_mms,
                    res_egt, res_cht, res_oil_p, res_oil_t, res_fuel_flow, res_vibration,
                    z_egt, z_cht, z_oil_p, z_oil_t, z_fuel_flow, z_vibration
                ) VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?
                )
            """, (
                ts, uav_id,
                telemetry.get("rpm", 0.0), telemetry.get("throttle", 0.0),
                telemetry.get("altitude_m", 0.0), telemetry.get("ambient_temp_c", 0.0),
                telemetry.get("engine_load", 0.0), telemetry.get("cht_c", 0.0),
                telemetry.get("egt_c", 0.0), telemetry.get("oil_pressure_bar", 0.0),
                telemetry.get("oil_temp_c", 0.0), telemetry.get("fuel_flow_lph", 0.0),
                telemetry.get("vibration_mms", 0.0), telemetry.get("battery_v", 14.2),
                telemetry.get("injection_timing_deg", -22.0),
                twin.get("egt_c"), twin.get("cht_c"), twin.get("oil_pressure_bar"),
                twin.get("oil_temp_c"), twin.get("fuel_flow_lph"), twin.get("vibration_mms"),
                residuals.get("egt_residual"), residuals.get("cht_residual"),
                residuals.get("oil_pressure_residual"), residuals.get("oil_temp_residual"),
                residuals.get("fuel_flow_residual"), residuals.get("vibration_residual"),
                residuals.get("z_egt"), residuals.get("z_cht"),
                residuals.get("z_oil_pressure"), residuals.get("z_oil_temp"),
                residuals.get("z_fuel_flow"), residuals.get("z_vibration")
            ))

            # 2. Insert Diagnostics
            cursor.execute("""
                INSERT INTO health_diagnostics (
                    timestamp, uav_id, health_index, health_status,
                    thermal_health, lubrication_health, vibration_health, efficiency_health,
                    is_anomaly, anomaly_score, anomaly_severity,
                    predicted_fault, confidence, fault_severity,
                    estimated_rul_hours, rul_status,
                    sensor_drift_flag, suspect_sensors,
                    maintenance_action, explanation_json
                ) VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
            """, (
                ts, uav_id,
                diagnostics.get("health_index", 100.0),
                diagnostics.get("health_status", "Healthy"),
                diagnostics.get("thermal_health", 100.0),
                diagnostics.get("lubrication_health", 100.0),
                diagnostics.get("vibration_health", 100.0),
                diagnostics.get("efficiency_health", 100.0),
                1 if diagnostics.get("is_anomaly") else 0,
                diagnostics.get("anomaly_score", 0.0),
                diagnostics.get("anomaly_severity", "Nominal"),
                diagnostics.get("predicted_fault", "Healthy"),
                diagnostics.get("confidence", 1.0),
                diagnostics.get("fault_severity", "Nominal"),
                diagnostics.get("estimated_rul_hours", 1000.0),
                diagnostics.get("rul_status", "Nominal Life"),
                1 if not diagnostics.get("all_sensors_valid", True) else 0,
                ", ".join(diagnostics.get("suspect_sensors", [])),
                diagnostics.get("maintenance_action", ""),
                json.dumps(diagnostics.get("explanation", {}))
            ))

            # If critical or fault detected, log maintenance advisory
            pred_fault = diagnostics.get("predicted_fault", "Healthy")
            if pred_fault != "Healthy" and diagnostics.get("confidence", 0) > 0.65:
                cursor.execute("""
                    INSERT INTO maintenance_advisories (
                        timestamp, fault_type, severity, evidence, action_prescribed
                    ) VALUES (?, ?, ?, ?, ?)
                """, (
                    ts,
                    pred_fault,
                    diagnostics.get("fault_severity", "Caution"),
                    diagnostics.get("explanation_summary", "Anomaly detected"),
                    diagnostics.get("maintenance_action", "Inspect engine")
                ))

            conn.commit()

    def get_latest_telemetry(self) -> Optional[Dict[str, Any]]:
        """Returns the most recent telemetry record."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT t.*, d.health_index, d.health_status, d.predicted_fault, d.confidence,
                       d.anomaly_score, d.estimated_rul_hours, d.maintenance_action
                FROM engine_telemetry t
                LEFT JOIN health_diagnostics d ON t.timestamp = d.timestamp
                ORDER BY t.id DESC LIMIT 1
            """)
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_telemetry_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Returns historical telemetry sequence."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT t.*, d.health_index, d.health_status, d.predicted_fault, d.confidence,
                       d.anomaly_score, d.estimated_rul_hours, d.maintenance_action
                FROM engine_telemetry t
                LEFT JOIN health_diagnostics d ON t.timestamp = d.timestamp
                ORDER BY t.id DESC LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            return [dict(r) for r in reversed(rows)]

    def get_advisories(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Fetch active maintenance advisories."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM maintenance_advisories
                ORDER BY id DESC LIMIT ?
            """, (limit,))
            return [dict(r) for r in cursor.fetchall()]

    def record_mission_simulation(self, record: Dict[str, Any]):
        """Saves mission simulation results."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO mission_simulations (
                    created_at, profile_name, duration_hours, cruise_altitude_m,
                    ambient_temp_c, throttle_setting, initial_health, final_health,
                    mission_risk_score, risk_explanation, rul_delta_hours
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.now(timezone.utc).isoformat(),
                record.get("profile_name", "Custom"),
                record.get("duration_hours", 4.0),
                record.get("cruise_altitude_m", 2500.0),
                record.get("ambient_temp_c", 20.0),
                record.get("throttle_setting", 0.75),
                record.get("initial_health", 95.0),
                record.get("final_health", 90.0),
                record.get("mission_risk_score", "LOW"),
                record.get("risk_explanation", ""),
                record.get("rul_delta_hours", 4.0)
            ))
            conn.commit()
