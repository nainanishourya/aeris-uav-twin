"""Synthetic Telemetry Data Generator for Aero-Piston Engine.

Produces realistic nominal, degraded, and fault-labeled flight telemetry.
Fully deterministic via configurable random seeds.
Explicitly synthetic - for prototyping and validation only.
"""

import math
import random
from typing import Dict, List, Tuple, Any, Optional
import numpy as np
import pandas as pd

from aeris.core.physics_twin import AeroPistonTwin
from aeris.core.residual_engine import ResidualCalculator

FAULT_CLASSES = [
    "Healthy",
    "Misfire",
    "Injector Abnormality",
    "Lubrication Problem",
    "Sensor Drift/Failure",
    "Combustion Instability",
    "Overheating",
    "Abnormal Vibration",
    "General Degradation"
]

class SyntheticTelemetryGenerator:
    """Generates synthetic telemetry streams anchored to the physics digital twin."""

    def __init__(self, seed: int = 42):
        self.seed = seed
        random.seed(seed)
        np.random.seed(seed)
        self.twin = AeroPistonTwin()
        self.calc = ResidualCalculator()

    def generate_flight_profile(
        self,
        duration_seconds: int = 1800,
        dt: float = 1.0,
        fault_type: str = "Healthy",
        fault_onset_ratio: float = 0.5,
        fault_severity: float = 1.0,
        altitude_profile: str = "cruise"
    ) -> pd.DataFrame:
        """Generates a complete time-series flight telemetry record with physics twin residuals.

        Args:
            duration_seconds: Flight duration in seconds
            dt: Sampling step in seconds
            fault_type: One of FAULT_CLASSES
            fault_onset_ratio: Fraction of mission when fault starts (0.0 - 1.0)
            fault_severity: Multiplier for fault intensity [0.1 to 2.0]
            altitude_profile: 'cruise', 'high_altitude', 'climb_descent', 'hot_day'
        """
        records = []
        self.twin.reset()
        
        # Base environmental setup
        base_altitude = 2500.0 # meters (~8,200 ft)
        base_temp = 18.0       # deg C
        
        if altitude_profile == "high_altitude":
            base_altitude = 5500.0 # ~18,000 ft
            base_temp = -12.0
        elif altitude_profile == "hot_day":
            base_altitude = 1200.0
            base_temp = 42.0       # Hot desert conditions

        num_steps = int(duration_seconds / dt)
        fault_start_step = int(num_steps * fault_onset_ratio)

        for step in range(num_steps):
            t = step * dt
            
            # Flight phase simulation
            progress = step / num_steps
            if progress < 0.10:
                # Takeoff & initial climb
                throttle = 0.95
                rpm = 5500.0 + random.gauss(0, 20)
                alt = 100.0 + (progress / 0.10) * base_altitude
            elif progress < 0.85:
                # Cruise / Loiter
                throttle = 0.72 + 0.05 * math.sin(t / 120.0)
                rpm = 4950.0 + 50.0 * math.sin(t / 90.0) + random.gauss(0, 15)
                alt = base_altitude + 50.0 * math.sin(t / 300.0)
            else:
                # Descent & approach
                throttle = 0.45
                rpm = 3800.0 + random.gauss(0, 25)
                alt = base_altitude * (1.0 - (progress - 0.85) / 0.15)
                alt = max(50.0, alt)

            # Ambient temperature adjusts with altitude lapse
            amb_temp = base_temp - 0.0065 * alt + random.gauss(0, 0.2)

            # Compute theoretical Digital Twin expected values
            twin_pred = self.twin.predict(
                rpm=rpm,
                throttle=throttle,
                altitude_m=alt,
                ambient_temp_c=amb_temp,
                dt_seconds=dt
            )

            # Baseline sensor noise (inherent measurement noise)
            noise_egt = random.gauss(0, 3.5)
            noise_cht = random.gauss(0, 0.8)
            noise_oil_p = random.gauss(0, 0.04)
            noise_oil_t = random.gauss(0, 0.5)
            noise_ff = random.gauss(0, 0.15)
            noise_vib = random.gauss(0, 0.08)

            # Fault Injection Deltas
            d_egt = 0.0
            d_cht = 0.0
            d_oil_p = 0.0
            d_oil_t = 0.0
            d_ff = 0.0
            d_vib = 0.0
            d_rpm = 0.0

            current_label = "Healthy"
            degradation_level = 0.0

            if step >= fault_start_step and fault_type != "Healthy":
                current_label = fault_type
                # Ramp up fault severity gradually
                ramp = min(1.0, (step - fault_start_step) / (num_steps * 0.15 + 1e-5))
                eff_sev = fault_severity * ramp
                degradation_level = eff_sev

                if fault_type == "Misfire":
                    # Cylinder misfire: EGT drops, vibration surges, RPM roughness
                    d_egt = -160.0 * eff_sev
                    d_vib = 2.4 * eff_sev + random.gauss(0, 0.4)
                    d_rpm = -80.0 * eff_sev + random.gauss(0, 40)
                    d_ff = 1.2 * eff_sev
                elif fault_type == "Injector Abnormality":
                    # Partially clogged/leaking injector: excessive fuel flow, high EGT, mild vibration
                    d_ff = 5.5 * eff_sev
                    d_egt = 65.0 * eff_sev
                    d_vib = 0.8 * eff_sev
                    d_cht = 8.0 * eff_sev
                elif fault_type == "Lubrication Problem":
                    # Oil pump wear or filter clog: Oil P drops, Oil T climbs
                    d_oil_p = -1.8 * eff_sev
                    d_oil_t = 24.0 * eff_sev
                    d_vib = 0.6 * eff_sev
                elif fault_type == "Sensor Drift/Failure":
                    # Single sensor (CHT) drifts upward artificially; physical twin and cross-sensors stay normal
                    d_cht = 42.0 * eff_sev
                    # Other sensors have zero anomaly delta!
                elif fault_type == "Combustion Instability":
                    # Unstable flame front / timing jitter: volatile EGT and vibration
                    d_egt = 30.0 * eff_sev * math.sin(t / 4.0)
                    d_vib = 1.8 * eff_sev + abs(random.gauss(0, 0.6))
                    d_rpm = 60.0 * eff_sev * math.sin(t / 3.0)
                elif fault_type == "Overheating":
                    # Cooling radiator blockage or coolant loss: both CHT and Oil T surge
                    d_cht = 32.0 * eff_sev
                    d_oil_t = 28.0 * eff_sev
                    d_egt = 25.0 * eff_sev
                elif fault_type == "Abnormal Vibration":
                    # Propeller or mount mechanical defect: high vibration without thermal fault
                    d_vib = 4.2 * eff_sev + random.gauss(0, 0.5)
                elif fault_type == "General Degradation":
                    # Piston ring wear, valve seat leakage: gradual loss of efficiency, mild oil P loss
                    d_ff = 2.5 * eff_sev
                    d_oil_p = -0.45 * eff_sev
                    d_vib = 0.6 * eff_sev
                    d_cht = 6.0 * eff_sev
                    d_egt = 18.0 * eff_sev

            # Actual simulated sensor reading = Twin expectation + Fault Delta + Measurement Noise
            actual_rpm = round(max(1000.0, rpm + d_rpm), 1)
            actual_egt = round(twin_pred.egt_c + d_egt + noise_egt, 2)
            actual_cht = round(twin_pred.cht_c + d_cht + noise_cht, 2)
            actual_oil_p = round(max(0.2, twin_pred.oil_pressure_bar + d_oil_p + noise_oil_p), 3)
            actual_oil_t = round(twin_pred.oil_temp_c + d_oil_t + noise_oil_t, 2)
            actual_ff = round(max(2.0, twin_pred.fuel_flow_lph + d_ff + noise_ff), 2)
            actual_vib = round(max(0.1, twin_pred.vibration_mms + d_vib + noise_vib), 2)
            battery_v = round(14.2 - 0.2 * (actual_rpm < 2000.0) + random.gauss(0, 0.05), 2)
            injection_timing = round(-21.0 + (rpm / 1000.0) * -0.5, 2)
            engine_load = round(throttle * (actual_rpm / 5800.0), 3)

            # Compute residuals
            res = self.calc.calculate(
                actual_telemetry={
                    "egt_c": actual_egt,
                    "cht_c": actual_cht,
                    "oil_pressure_bar": actual_oil_p,
                    "oil_temp_c": actual_oil_t,
                    "fuel_flow_lph": actual_ff,
                    "vibration_mms": actual_vib
                },
                twin_pred=twin_pred
            )

            records.append({
                "timestamp_sec": round(t, 2),
                "rpm": actual_rpm,
                "throttle": round(throttle, 3),
                "altitude_m": round(alt, 1),
                "ambient_temp_c": round(amb_temp, 1),
                "engine_load": engine_load,
                "cht_c": actual_cht,
                "egt_c": actual_egt,
                "oil_pressure_bar": actual_oil_p,
                "oil_temp_c": actual_oil_t,
                "fuel_flow_lph": actual_ff,
                "vibration_mms": actual_vib,
                "battery_v": battery_v,
                "injection_timing_deg": injection_timing,
                
                # Digital Twin expected values
                "twin_egt_c": twin_pred.egt_c,
                "twin_cht_c": twin_pred.cht_c,
                "twin_oil_pressure_bar": twin_pred.oil_pressure_bar,
                "twin_oil_temp_c": twin_pred.oil_temp_c,
                "twin_fuel_flow_lph": twin_pred.fuel_flow_lph,
                "twin_vibration_mms": twin_pred.vibration_mms,
                "twin_efficiency": twin_pred.engine_efficiency,
                "twin_map_inhg": twin_pred.manifold_pressure_inhg,
                
                # Residuals (Actual - Twin)
                "res_egt": res.egt_residual,
                "res_cht": res.cht_residual,
                "res_oil_p": res.oil_pressure_residual,
                "res_oil_t": res.oil_temp_residual,
                "res_fuel_flow": res.fuel_flow_residual,
                "res_vibration": res.vibration_residual,
                
                # Normalized z-residuals
                "z_egt": res.z_egt,
                "z_cht": res.z_cht,
                "z_oil_p": res.z_oil_pressure,
                "z_oil_t": res.z_oil_temp,
                "z_fuel_flow": res.z_fuel_flow,
                "z_vibration": res.z_vibration,
                
                # Ground truth targets
                "fault_label": current_label,
                "is_anomaly": 0 if current_label == "Healthy" else 1,
                "degradation_severity": round(degradation_level, 3)
            })

        return pd.DataFrame(records)

    def generate_training_corpus(
        self,
        nominal_flights: int = 15,
        fault_flights_per_class: int = 4,
        flight_duration: int = 600
    ) -> pd.DataFrame:
        """Generates a rich, balanced training corpus across all operational and fault regimes."""
        all_dfs = []
        alt_profiles = ["cruise", "high_altitude", "hot_day"]

        # Nominal flights
        for i in range(nominal_flights):
            prof = alt_profiles[i % len(alt_profiles)]
            df = self.generate_flight_profile(
                duration_seconds=flight_duration,
                fault_type="Healthy",
                altitude_profile=prof
            )
            all_dfs.append(df)

        # Fault flights
        fault_types = [fc for fc in FAULT_CLASSES if fc != "Healthy"]
        for fc in fault_types:
            for j in range(fault_flights_per_class):
                prof = alt_profiles[j % len(alt_profiles)]
                df = self.generate_flight_profile(
                    duration_seconds=flight_duration,
                    fault_type=fc,
                    fault_onset_ratio=0.35,
                    fault_severity=random.uniform(0.7, 1.4),
                    altitude_profile=prof
                )
                all_dfs.append(df)

        corpus = pd.concat(all_dfs, ignore_index=True)
        return corpus
