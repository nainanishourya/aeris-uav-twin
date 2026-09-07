"""Engine Health Index (EHI) Computation Engine.

Calculates a composite 0-100 score combining:
- Thermal Health Sub-index (CHT, EGT residuals)
- Lubrication Health Sub-index (Oil P, Oil T residuals)
- Mechanical / Vibration Health Sub-index
- Fuel Efficiency / Combustion Health Sub-index
- Anomaly Penalty (Unsupervised Isolation Forest score)
- Degradation Trend Factor
"""

from dataclasses import dataclass, asdict
from typing import Dict, Any, Tuple
from aeris.config.engine_specs import HEALTH_THRESHOLDS
from aeris.core.residual_engine import SensorResiduals

@dataclass
class HealthAssessment:
    """Complete health evaluation breakdown."""
    health_index: float                # Overall composite (0 - 100)
    status_label: str                  # Healthy, Normal/Watch, Degraded, Critical, Severe
    thermal_health: float              # 0 - 100
    lubrication_health: float          # 0 - 100
    vibration_health: float            # 0 - 100
    efficiency_health: float           # 0 - 100
    anomaly_penalty: float             # 0 - 30 deduction
    degradation_penalty: float         # 0 - 25 deduction
    color_hex: str                     # UI color code

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class HealthIndexCalculator:
    """Computes transparent, physics-anchored 0-100 Engine Health Index."""

    def __init__(self, thresholds: Dict[str, float] = HEALTH_THRESHOLDS):
        self.thresholds = thresholds

    def _z_to_subscore(self, z_val: float, z_safe: float = 2.0, z_crit: float = 4.5) -> float:
        """Converts an absolute z-score residual into a 0-100 health subscore."""
        abs_z = abs(z_val)
        if abs_z <= z_safe:
            # 100 down to 85 within 2-sigma
            return 100.0 - (abs_z / z_safe) * 15.0
        elif abs_z <= z_crit:
            # 85 down to 35 between 2-sigma and 4.5-sigma
            ratio = (abs_z - z_safe) / (z_crit - z_safe)
            return 85.0 - ratio * 50.0
        else:
            # Extreme divergence
            excess = abs_z - z_crit
            return max(0.0, 35.0 - excess * 15.0)

    def calculate(
        self,
        residuals: SensorResiduals,
        anomaly_score: float = 0.0,       # 0.0 (normal) to 1.0 (extreme anomaly)
        degradation_factor: float = 0.0    # 0.0 (fresh) to 1.0 (end of life)
    ) -> HealthAssessment:
        """Calculates composite Engine Health Index and sub-indices."""
        # 1. Thermal Health (CHT and EGT residuals)
        cht_sub = self._z_to_subscore(residuals.z_cht, z_safe=2.0, z_crit=4.0)
        egt_sub = self._z_to_subscore(residuals.z_egt, z_safe=2.0, z_crit=4.0)
        thermal_health = round(0.55 * cht_sub + 0.45 * egt_sub, 1)

        # 2. Lubrication Health (Oil Pressure & Temperature)
        # Oil pressure drop is especially critical
        oil_p_sub = self._z_to_subscore(residuals.z_oil_pressure, z_safe=1.8, z_crit=3.8)
        oil_t_sub = self._z_to_subscore(residuals.z_oil_temp, z_safe=2.0, z_crit=4.0)
        lubrication_health = round(0.60 * oil_p_sub + 0.40 * oil_t_sub, 1)

        # 3. Vibration / Mechanical Health
        vibration_health = round(self._z_to_subscore(residuals.z_vibration, z_safe=1.8, z_crit=4.0), 1)

        # 4. Combustion & Efficiency Health (Fuel flow divergence)
        efficiency_health = round(self._z_to_subscore(residuals.z_fuel_flow, z_safe=2.0, z_crit=4.0), 1)

        # Weighted Subscore Base (sum of weights = 1.0)
        base_health = (
            0.28 * thermal_health +
            0.28 * lubrication_health +
            0.24 * vibration_health +
            0.20 * efficiency_health
        )

        # Anomaly Penalty (up to 30 points deducted for high anomaly confidence)
        anomaly_penalty = round(min(30.0, max(0.0, anomaly_score * 30.0)), 1)

        # Degradation Penalty (up to 20 points gradual wear)
        degradation_penalty = round(min(20.0, max(0.0, degradation_factor * 20.0)), 1)

        # Overall composite score clamped [0.0, 100.0]
        composite = max(0.0, min(100.0, base_health - (anomaly_penalty * 0.5) - degradation_penalty))
        composite = round(composite, 1)

        # Classify severity label & color
        if composite >= self.thresholds.get("HEALTHY", 90.0):
            label = "Healthy"
            color = "#00e5a3"  # Aerospace green
        elif composite >= self.thresholds.get("NORMAL_WATCH", 70.0):
            label = "Normal/Watch"
            color = "#38bdf8"  # Cyan / Blue watch
        elif composite >= self.thresholds.get("DEGRADED", 50.0):
            label = "Degraded"
            color = "#f59e0b"  # Amber warning
        elif composite >= self.thresholds.get("CRITICAL", 30.0):
            label = "Critical"
            color = "#f97316"  # Orange critical
        else:
            label = "Severe"
            color = "#ef4444"  # Red severe

        return HealthAssessment(
            health_index=composite,
            status_label=label,
            thermal_health=thermal_health,
            lubrication_health=lubrication_health,
            vibration_health=vibration_health,
            efficiency_health=efficiency_health,
            anomaly_penalty=anomaly_penalty,
            degradation_penalty=degradation_penalty,
            color_hex=color
        )
