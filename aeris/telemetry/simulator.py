"""Real-Time Telemetry Generator and Dynamic Fault Injector for AERIS."""

import time
import math
import random
import threading
from typing import Dict, Any, Optional, Callable

from aeris.core.physics_twin import AeroPistonTwin
from aeris.core.residual_engine import ResidualCalculator
from aeris.core.health_index import HealthIndexCalculator
from aeris.ml.anomaly_detector import IsolationForestAnomalyDetector
from aeris.ml.fault_classifier import EngineFaultClassifier
from aeris.ml.sensor_validator import SensorValidator
from aeris.ml.rul_estimator import PhysicsInformedRULEstimator
from aeris.ml.explainability import XAIEngine
from aeris.telemetry.mqtt_client import mqtt_gateway
from aeris.telemetry.database import AerisDatabase
from aeris.config.settings import settings

class TelemetrySimulator:
    """Simulates real-time telemetry streaming from a MALE UAV aero-piston engine."""

    def __init__(self, db: Optional[AerisDatabase] = None):
        self.db = db or AerisDatabase()
        self.twin = AeroPistonTwin()
        self.calc = ResidualCalculator()
        self.health_calc = HealthIndexCalculator()
        self.validator = SensorValidator()
        self.rul_est = PhysicsInformedRULEstimator()
        
        # Load ML models if available
        self.anomaly_detector = IsolationForestAnomalyDetector().load(settings.anomaly_model_path)
        self.fault_classifier = EngineFaultClassifier().load(settings.fault_classifier_path)

        # Simulation states
        self.is_running: bool = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        # Operational mode
        self.current_fault: str = "Healthy"
        self.fault_severity: float = 0.0
        self.step_counter: int = 0
        self.flight_hours: float = 382.5
        
        # Current conditions
        self.rpm_target: float = 5050.0
        self.throttle: float = 0.74
        self.altitude_m: float = 2400.0
        self.ambient_temp_c: float = 16.0
        
        # Demo scenario state
        self.demo_active: bool = False
        self.demo_step: int = 0
        self.demo_total_steps: int = 60

    def set_operating_point(
        self,
        throttle: Optional[float] = None,
        altitude_m: Optional[float] = None,
        ambient_temp_c: Optional[float] = None,
        fault: Optional[str] = None,
        severity: Optional[float] = None
    ):
        """Dynamically adjusts engine inputs or injects faults."""
        if throttle is not None:
            self.throttle = max(0.0, min(1.0, float(throttle)))
            self.rpm_target = 1600.0 + self.throttle * 4000.0
        if altitude_m is not None:
            self.altitude_m = float(altitude_m)
        if ambient_temp_c is not None:
            self.ambient_temp_c = float(ambient_temp_c)
        if fault is not None:
            self.current_fault = fault
        if severity is not None:
            self.fault_severity = max(0.0, min(2.0, float(severity)))

    def start_demo_scenario(self):
        """Initiates the 1-click end-to-end injector degradation demonstration."""
        self.demo_active = True
        self.demo_step = 0
        self.current_fault = "Healthy"
        self.fault_severity = 0.0
        self.throttle = 0.75
        self.rpm_target = 5100.0
        if not self.is_running:
            self.start()

    def start(self):
        """Starts real-time streaming thread."""
        if self.is_running:
            return
        self.is_running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """Stops streaming thread."""
        self.is_running = False
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2.0)

    def step(self) -> Dict[str, Any]:
        """Generates a single synchronized time-slice of telemetry, twin, and diagnostics."""
        self.step_counter += 1
        t = time.time()
        dt = 1.0

        # Handle demo scenario progression
        if self.demo_active:
            self.demo_step += 1
            if self.demo_step > 10:
                # Begin gradual injector degradation divergence
                self.current_fault = "Injector Abnormality"
                progress = min(1.0, (self.demo_step - 10) / (self.demo_total_steps - 10))
                self.fault_severity = progress * 1.3
            if self.demo_step >= self.demo_total_steps:
                self.demo_active = False

        # Flight dynamics variation
        rpm = self.rpm_target + random.gauss(0, 15)
        amb_temp = self.ambient_temp_c - 0.0065 * self.altitude_m

        # 1. Physics Digital Twin Expected Values
        twin_pred = self.twin.predict(
            rpm=rpm,
            throttle=self.throttle,
            altitude_m=self.altitude_m,
            ambient_temp_c=amb_temp,
            dt_seconds=dt
        )

        # 2. Apply Fault Injection Deltas
        d_egt = 0.0
        d_cht = 0.0
        d_oil_p = 0.0
        d_oil_t = 0.0
        d_ff = 0.0
        d_vib = 0.0
        d_rpm = 0.0
        sev = self.fault_severity

        if self.current_fault == "Misfire":
            d_egt = -150.0 * sev
            d_vib = 2.2 * sev
            d_rpm = -70.0 * sev
            d_ff = 1.0 * sev
        elif self.current_fault == "Injector Abnormality":
            d_ff = 5.2 * sev
            d_egt = 62.0 * sev
            d_vib = 0.7 * sev
            d_cht = 7.0 * sev
        elif self.current_fault == "Lubrication Problem":
            d_oil_p = -1.6 * sev
            d_oil_t = 22.0 * sev
            d_vib = 0.5 * sev
        elif self.current_fault == "Sensor Drift/Failure":
            # CHT sensor drifts, other sensors completely normal
            d_cht = 45.0 * sev
        elif self.current_fault == "Combustion Instability":
            d_egt = 28.0 * sev * math.sin(self.step_counter / 3.0)
            d_vib = 1.6 * sev
            d_rpm = 50.0 * sev * math.sin(self.step_counter / 2.5)
        elif self.current_fault == "Overheating":
            d_cht = 30.0 * sev
            d_oil_t = 26.0 * sev
            d_egt = 22.0 * sev
        elif self.current_fault == "Abnormal Vibration":
            d_vib = 3.8 * sev
        elif self.current_fault == "General Degradation":
            d_ff = 2.2 * sev
            d_oil_p = -0.4 * sev
            d_vib = 0.5 * sev
            d_egt = 16.0 * sev

        # Simulated sensors with realistic noise
        actual_rpm = round(max(1000.0, rpm + d_rpm), 1)
        actual_egt = round(twin_pred.egt_c + d_egt + random.gauss(0, 2.5), 2)
        actual_cht = round(twin_pred.cht_c + d_cht + random.gauss(0, 0.6), 2)
        actual_oil_p = round(max(0.2, twin_pred.oil_pressure_bar + d_oil_p + random.gauss(0, 0.03)), 3)
        actual_oil_t = round(twin_pred.oil_temp_c + d_oil_t + random.gauss(0, 0.4), 2)
        actual_ff = round(max(2.0, twin_pred.fuel_flow_lph + d_ff + random.gauss(0, 0.12)), 2)
        actual_vib = round(max(0.2, twin_pred.vibration_mms + d_vib + random.gauss(0, 0.06)), 2)
        batt_v = round(14.2 + random.gauss(0, 0.04), 2)
        timing = round(-21.0 - (actual_rpm / 1000.0) * 0.4, 2)
        eng_load = round(self.throttle * (actual_rpm / 5800.0), 3)

        telemetry = {
            "timestamp": round(t, 2),
            "uav_id": settings.mqtt_uav_id,
            "rpm": actual_rpm,
            "throttle": round(self.throttle, 3),
            "altitude_m": round(self.altitude_m, 1),
            "ambient_temp_c": round(amb_temp, 1),
            "engine_load": eng_load,
            "cht_c": actual_cht,
            "egt_c": actual_egt,
            "oil_pressure_bar": actual_oil_p,
            "oil_temp_c": actual_oil_t,
            "fuel_flow_lph": actual_ff,
            "vibration_mms": actual_vib,
            "battery_v": batt_v,
            "injection_timing_deg": timing
        }

        # 3. Residual Vector Calculation
        res = self.calc.calculate(telemetry, twin_pred)

        # 4. Sensor Cross-Validation
        val_report = self.validator.evaluate(
            actual=telemetry,
            twin_expected=twin_pred.__dict__,
            residuals=res.__dict__
        )

        # 5. Feature dict for ML models
        features = {
            "z_egt": res.z_egt,
            "z_cht": res.z_cht,
            "z_oil_p": res.z_oil_pressure,
            "z_oil_t": res.z_oil_temp,
            "z_fuel_flow": res.z_fuel_flow,
            "z_vibration": res.z_vibration,
            "res_egt": res.egt_residual,
            "res_cht": res.cht_residual,
            "res_oil_p": res.oil_pressure_residual,
            "res_oil_t": res.oil_temp_residual,
            "res_fuel_flow": res.fuel_flow_residual,
            "res_vibration": res.vibration_residual,
            "rpm": actual_rpm,
            "engine_load": eng_load
        }

        # 6. Unsupervised Anomaly Detection
        anom_res = self.anomaly_detector.predict(features)

        # If sensor drift detected by cross-validation, prioritize sensor drift diagnosis
        if not val_report.all_sensors_valid and "CHT Sensor" in val_report.suspect_sensors:
            fault_diagnosis = self.fault_classifier.predict(features)
            # Override to sensor drift to avoid false engine overheating alarm
            fault_diagnosis.predicted_fault = "Sensor Drift/Failure"
            fault_diagnosis.confidence = 0.94
            fault_diagnosis.severity = "Caution"
            fault_diagnosis.explanation = val_report.channel_reports["cht"].evidence
        else:
            fault_diagnosis = self.fault_classifier.predict(features)

        # 7. Engine Health Index
        health_assessment = self.health_calc.calculate(
            residuals=res,
            anomaly_score=anom_res.anomaly_score,
            degradation_factor=self.fault_severity * 0.5
        )

        # 8. Remaining Useful Life
        rul_assessment = self.rul_est.estimate(
            current_health_index=health_assessment.health_index,
            current_flight_hours=self.flight_hours,
            anomaly_score=anom_res.anomaly_score,
            sub_healths={
                "thermal": health_assessment.thermal_health,
                "lubrication": health_assessment.lubrication_health,
                "vibration": health_assessment.vibration_health,
                "efficiency": health_assessment.efficiency_health
            }
        )

        # 9. Explainable AI
        xai = XAIEngine.explain(
            diagnosis=fault_diagnosis.predicted_fault,
            confidence=fault_diagnosis.confidence,
            actual_telemetry=telemetry,
            twin_expected=twin_pred.__dict__,
            residuals=res.__dict__,
            maintenance_action=fault_diagnosis.maintenance_action
        )

        diagnostics = {
            "health_index": health_assessment.health_index,
            "health_status": health_assessment.status_label,
            "thermal_health": health_assessment.thermal_health,
            "lubrication_health": health_assessment.lubrication_health,
            "vibration_health": health_assessment.vibration_health,
            "efficiency_health": health_assessment.efficiency_health,
            "is_anomaly": anom_res.is_anomaly,
            "anomaly_score": anom_res.anomaly_score,
            "anomaly_severity": anom_res.severity,
            "affected_sensors": anom_res.affected_sensors,
            "predicted_fault": fault_diagnosis.predicted_fault,
            "confidence": fault_diagnosis.confidence,
            "fault_severity": fault_diagnosis.severity,
            "estimated_rul_hours": rul_assessment.estimated_rul_hours,
            "rul_confidence_lower": rul_assessment.confidence_interval_hours[0],
            "rul_confidence_upper": rul_assessment.confidence_interval_hours[1],
            "rul_status": rul_assessment.rul_status,
            "all_sensors_valid": val_report.all_sensors_valid,
            "suspect_sensors": val_report.suspect_sensors,
            "maintenance_action": fault_diagnosis.maintenance_action,
            "explanation_summary": xai.summary,
            "explanation": xai.__dict__
        }

        # 10. Persist to SQLite
        self.db.record_snapshot(
            telemetry=telemetry,
            twin=twin_pred.__dict__,
            residuals=res.__dict__,
            diagnostics=diagnostics
        )

        # 11. Publish over MQTT Gateway
        mqtt_gateway.publish_telemetry(telemetry)
        mqtt_gateway.publish_health({
            "timestamp": t,
            "health_index": health_assessment.health_index,
            "status": health_assessment.status_label,
            "rul_hours": rul_assessment.estimated_rul_hours
        })
        mqtt_gateway.publish_diagnostics(diagnostics)

        return {
            "telemetry": telemetry,
            "digital_twin": twin_pred.__dict__,
            "residuals": res.__dict__,
            "diagnostics": diagnostics
        }

    def _run_loop(self):
        """Continuous generator thread running at ~1 Hz."""
        while not self._stop_event.is_set():
            try:
                self.step()
            except Exception as e:
                print(f"Error in telemetry simulator step: {e}")
            time.sleep(1.0)

# Global singleton simulator
simulator = TelemetrySimulator()
