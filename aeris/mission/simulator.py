"""Mission Profile Simulator for MALE UAV Operations.

Simulates forward-in-time engine performance, cumulative degradation,
health index deterioration, and mission risk scoring across operational presets.
"""

from dataclasses import dataclass, asdict
from typing import Dict, List, Any, Optional
import math
import numpy as np

from aeris.core.physics_twin import AeroPistonTwin
from aeris.core.health_index import HealthIndexCalculator
from aeris.core.residual_engine import ResidualCalculator

@dataclass
class MissionProfile:
    name: str
    description: str
    duration_hours: float
    cruise_altitude_m: float
    ambient_temp_c: float
    cruise_throttle: float
    throttle_transients: bool
    initial_health_index: float

MISSION_PRESETS: Dict[str, MissionProfile] = {
    "Normal ISR": MissionProfile(
        name="Normal ISR",
        description="Standard Intelligence, Surveillance & Reconnaissance patrol at moderate altitude and steady cruise.",
        duration_hours=8.0,
        cruise_altitude_m=3000.0,
        ambient_temp_c=15.0,
        cruise_throttle=0.70,
        throttle_transients=False,
        initial_health_index=95.0
    ),
    "Long Endurance": MissionProfile(
        name="Long Endurance",
        description="Extended 18-hour loiter mission maximizing fuel economy at economy throttle setting.",
        duration_hours=18.0,
        cruise_altitude_m=4200.0,
        ambient_temp_c=5.0,
        cruise_throttle=0.62,
        throttle_transients=False,
        initial_health_index=94.0
    ),
    "High Altitude": MissionProfile(
        name="High Altitude",
        description="High-altitude cruise near 20,000 ft ceiling with low ambient air density and maximum turbocharger duty.",
        duration_hours=6.0,
        cruise_altitude_m=6200.0,
        ambient_temp_c=-22.0,
        cruise_throttle=0.88,
        throttle_transients=False,
        initial_health_index=92.0
    ),
    "Hot Weather": MissionProfile(
        name="Hot Weather",
        description="Desert operations in high ambient heat (ISA +25°C) challenging cooling margins and oil temperatures.",
        duration_hours=5.0,
        cruise_altitude_m=1200.0,
        ambient_temp_c=45.0,
        cruise_throttle=0.76,
        throttle_transients=False,
        initial_health_index=91.0
    ),
    "Rapid Throttle Transition": MissionProfile(
        name="Rapid Throttle Transition",
        description="Tactical profile with cyclic power changes, rapid climbs, dashes, and loiters testing thermal fatigue.",
        duration_hours=4.0,
        cruise_altitude_m=2800.0,
        ambient_temp_c=25.0,
        cruise_throttle=0.80,
        throttle_transients=True,
        initial_health_index=93.0
    )
}

@dataclass
class MissionSimulationResult:
    profile_name: str
    duration_hours: float
    initial_health: float
    final_health: float
    health_delta: float
    mission_risk_score: str            # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    risk_color: str
    risk_explanation: str
    rul_impact_hours: float            # Accelerated wear penalty
    fuel_consumed_liters: float
    max_cht_c: float
    max_oil_temp_c: float
    min_oil_press_bar: float
    trajectory: List[Dict[str, float]]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class MissionSimulator:
    """Projects aero-piston digital twin through user-configured operational flight profiles."""

    def __init__(self):
        self.twin = AeroPistonTwin()
        self.calc = ResidualCalculator()
        self.health_calc = HealthIndexCalculator()

    def run_simulation(
        self,
        profile: MissionProfile,
        existing_degradation_factor: float = 0.0
    ) -> MissionSimulationResult:
        """Runs forward simulation across the mission duration."""
        self.twin.reset()
        
        # Sample points: 30 discrete time-steps across mission duration
        num_steps = 30
        dt_hours = profile.duration_hours / num_steps
        trajectory = []
        
        curr_health = profile.initial_health_index
        total_fuel = 0.0
        max_cht = 0.0
        max_oil_t = 0.0
        min_oil_p = 10.0

        for i in range(num_steps + 1):
            t_hour = round(i * dt_hours, 2)
            
            # Dynamic throttle
            throttle = profile.cruise_throttle
            if profile.throttle_transients:
                # Oscillate throttle between 0.55 and 0.95
                throttle = profile.cruise_throttle + 0.18 * math.sin(i * 0.8)
                throttle = max(0.40, min(1.0, throttle))

            rpm = 2200.0 + throttle * 3400.0
            alt = profile.cruise_altitude_m
            
            # Evaluate digital twin prediction
            twin_pred = self.twin.predict(
                rpm=rpm,
                throttle=throttle,
                altitude_m=alt,
                ambient_temp_c=profile.ambient_temp_c,
                dt_seconds=dt_hours * 3600.0
            )

            # Cumulative degradation progression over the mission
            wear_rate_base = 0.04  # standard health loss per hour
            
            # Thermal stress multiplier
            thermal_stress = 1.0
            if twin_pred.cht_c > 120.0 or profile.ambient_temp_c > 38.0:
                thermal_stress += 1.2 * ((twin_pred.cht_c - 115.0) / 10.0)
            
            # Altitude turbo stress multiplier
            altitude_stress = 1.0 + (alt / 6000.0) ** 1.8
            
            # Transient mechanical stress multiplier
            transient_stress = 1.5 if profile.throttle_transients else 1.0

            total_wear_mult = thermal_stress * altitude_stress * transient_stress * (1.0 + existing_degradation_factor * 2.0)
            step_wear = wear_rate_base * dt_hours * total_wear_mult
            curr_health = max(10.0, curr_health - step_wear)

            # Accumulate metrics
            total_fuel += twin_pred.fuel_flow_lph * dt_hours
            max_cht = max(max_cht, twin_pred.cht_c)
            max_oil_t = max(max_oil_t, twin_pred.oil_temp_c)
            min_oil_p = min(min_oil_p, twin_pred.oil_pressure_bar)

            trajectory.append({
                "mission_hour": t_hour,
                "projected_health": round(curr_health, 1),
                "throttle": round(throttle, 2),
                "rpm": round(rpm, 0),
                "predicted_cht": round(twin_pred.cht_c, 1),
                "predicted_egt": round(twin_pred.egt_c, 1),
                "predicted_oil_temp": round(twin_pred.oil_temp_c, 1),
                "predicted_oil_press": round(twin_pred.oil_pressure_bar, 2),
                "fuel_flow_lph": round(twin_pred.fuel_flow_lph, 1)
            })

        health_delta = round(profile.initial_health_index - curr_health, 1)
        rul_impact_hours = round(health_delta * 14.5, 1)

        # Risk scoring logic
        risk_score = "LOW"
        risk_color = "#00e5a3" # Green
        reasons = []

        if profile.ambient_temp_c >= 40.0:
            reasons.append(f"Elevated ambient temperature ({profile.ambient_temp_c}°C) reduces cooling margin, elevating peak oil temperature to {max_oil_t:.1f}°C.")
        if profile.cruise_altitude_m >= 5500.0:
            reasons.append(f"High altitude ({profile.cruise_altitude_m:.0f}m) enforces continuous maximum turbocharger boost and thinner cooling air.")
        if profile.throttle_transients:
            reasons.append("Frequent cyclic throttle transitions induce severe thermal-mechanical fatigue on cylinder heads and valve seats.")
        if profile.duration_hours >= 16.0:
            reasons.append(f"Extended endurance ({profile.duration_hours}h) elevates oil breakdown and continuous thermal soak risk.")
        if curr_health < 75.0:
            reasons.append(f"End-of-mission projected health drops into Degraded tier ({curr_health:.1f}).")

        if curr_health < 65.0 or (profile.ambient_temp_c > 42.0 and profile.cruise_altitude_m > 5000.0):
            risk_score = "CRITICAL"
            risk_color = "#ef4444"
        elif len(reasons) >= 2 or health_delta > 7.0:
            risk_score = "HIGH"
            risk_color = "#f97316"
        elif len(reasons) == 1 or health_delta > 3.5:
            risk_score = "MEDIUM"
            risk_color = "#f59e0b"
        else:
            risk_score = "LOW"
            risk_color = "#00e5a3"
            reasons.append("All engine parameters remain comfortably inside steady-state nominal operating envelope.")

        risk_explanation = " ".join(reasons)

        return MissionSimulationResult(
            profile_name=profile.name,
            duration_hours=round(profile.duration_hours, 1),
            initial_health=round(profile.initial_health_index, 1),
            final_health=round(curr_health, 1),
            health_delta=health_delta,
            mission_risk_score=risk_score,
            risk_color=risk_color,
            risk_explanation=risk_explanation,
            rul_impact_hours=rul_impact_hours,
            fuel_consumed_liters=round(total_fuel, 1),
            max_cht_c=round(max_cht, 1),
            max_oil_temp_c=round(max_oil_t, 1),
            min_oil_press_bar=round(min_oil_p, 2),
            trajectory=trajectory
        )
