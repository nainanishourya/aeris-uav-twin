"""Remaining Useful Life (RUL) Estimator for Aero-Piston Engines.

Uses physics-informed cumulative damage accumulation and degradation trajectory modeling
to predict Remaining Flight Hours with confidence intervals.
"""

import math
from dataclasses import dataclass, asdict
from typing import Dict, List, Tuple, Any, Optional
import numpy as np

@dataclass
class RULEstimate:
    """Estimated Remaining Useful Life Assessment."""
    estimated_rul_hours: float
    confidence_interval_hours: Tuple[float, float]
    confidence_level_pct: float
    current_operating_hours: float
    health_trajectory: List[Dict[str, float]]
    degradation_rate_per_hour: float
    limiting_component: str
    rul_status: str                     # "Nominal Life", "Accelerated Wear", "Critical Maintenance Due"
    disclaimer: str = "Estimated Remaining Useful Life - Model-based estimation for research and prototyping only."

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["confidence_interval_hours"] = list(self.confidence_interval_hours)
        return d

class PhysicsInformedRULEstimator:
    """Estimates Remaining Useful Life based on health index, residual divergence, and flight regime history."""

    BASE_TBO_HOURS = 1400.0   # Typical Time-Between-Overhaul for modern aero-piston engine

    def __init__(self, tbo_hours: float = BASE_TBO_HOURS):
        self.tbo_hours = tbo_hours
        self.critical_health_threshold = 30.0

    def estimate(
        self,
        current_health_index: float,
        current_flight_hours: float = 380.0,
        anomaly_score: float = 0.0,
        sub_healths: Optional[Dict[str, float]] = None,
        recent_trend_slope: float = -0.01  # Health index delta per hour
    ) -> RULEstimate:
        """Projects degradation forward to determine remaining flight hours and confidence interval."""
        sub_healths = sub_healths or {
            "thermal": 95.0,
            "lubrication": 95.0,
            "vibration": 95.0,
            "efficiency": 95.0
        }

        # Identify limiting sub-component
        limiting_comp = min(sub_healths.items(), key=lambda x: x[1])
        limiting_name = f"{limiting_comp[0].capitalize()} System"

        # Baseline wear rate: ~ (100 - 30) / TBO = 70 / 1400 = 0.05 health points per normal flight hour
        nominal_wear_rate = 70.0 / self.tbo_hours

        # Stress acceleration multiplier based on health deterioration & anomaly score
        # When engine is healthy (health ~ 95, anom ~ 0), factor is 1.0
        health_deficit = max(0.0, 100.0 - current_health_index)
        stress_factor = 1.0 + (health_deficit / 20.0) ** 1.6 + (anomaly_score * 3.5)

        # Dynamic degradation rate (points of health index lost per flight hour)
        effective_wear_rate = nominal_wear_rate * stress_factor

        # Incorporate recent trend slope if negative and faster than stress factor
        if recent_trend_slope < -0.05:
            effective_wear_rate = max(effective_wear_rate, abs(recent_trend_slope))

        # Margin to critical threshold (Health Index = 30)
        remaining_health_margin = max(0.0, current_health_index - self.critical_health_threshold)

        if current_health_index <= self.critical_health_threshold:
            rul_hours = 0.0
            lower_bound = 0.0
            upper_bound = 2.0
            status = "Critical Maintenance Due"
        else:
            rul_hours = remaining_health_margin / effective_wear_rate
            # Bound by remaining physical TBO hours
            remaining_tbo = max(5.0, self.tbo_hours - current_flight_hours)
            rul_hours = min(rul_hours, remaining_tbo)
            
            # Confidence bounds: higher uncertainty as anomaly or degradation rises
            uncertainty_pct = 0.12 + 0.25 * (anomaly_score) + 0.15 * (health_deficit / 70.0)
            lower_bound = max(0.0, rul_hours * (1.0 - uncertainty_pct))
            upper_bound = rul_hours * (1.0 + uncertainty_pct)

            if rul_hours > 600.0:
                status = "Nominal Life"
            elif rul_hours > 150.0:
                status = "Accelerated Wear"
            else:
                status = "Critical Maintenance Due"

        # Forward projection trajectory (future 20 steps)
        trajectory = []
        proj_steps = 15
        step_hours = max(5.0, rul_hours / proj_steps) if rul_hours > 0 else 1.0
        projected_h = current_health_index

        for step in range(proj_steps + 1):
            h_time = step * step_hours
            trajectory.append({
                "future_hours": round(h_time, 1),
                "total_flight_hours": round(current_flight_hours + h_time, 1),
                "projected_health": round(max(0.0, projected_h), 1)
            })
            # Non-linear accelerating degradation curve
            step_decay = effective_wear_rate * step_hours * (1.0 + 0.03 * step)
            projected_h -= step_decay

        return RULEstimate(
            estimated_rul_hours=round(rul_hours, 1),
            confidence_interval_hours=(round(lower_bound, 1), round(upper_bound, 1)),
            confidence_level_pct=90.0,
            current_operating_hours=round(current_flight_hours, 1),
            health_trajectory=trajectory,
            degradation_rate_per_hour=round(effective_wear_rate, 3),
            limiting_component=limiting_name,
            rul_status=status
        )
