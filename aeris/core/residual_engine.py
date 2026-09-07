"""Residual Engine: Computes raw and normalized residual vectors between actual sensors and physics twin."""

from dataclasses import dataclass, asdict
from typing import Dict, Any, List
from aeris.config.engine_specs import RESIDUAL_BASELINE_STDS
from aeris.core.physics_twin import TwinPrediction

@dataclass
class SensorResiduals:
    """Residuals computed for key engine channels."""
    # Raw residuals (Actual - Twin)
    egt_residual: float
    cht_residual: float
    oil_pressure_residual: float
    oil_temp_residual: float
    fuel_flow_residual: float
    vibration_residual: float
    
    # Normalized residuals (z-scores relative to healthy standard deviations)
    z_egt: float
    z_cht: float
    z_oil_pressure: float
    z_oil_temp: float
    z_fuel_flow: float
    z_vibration: float
    
    # Percentage deviations
    pct_egt: float
    pct_cht: float
    pct_oil_pressure: float
    pct_oil_temp: float
    pct_fuel_flow: float
    pct_vibration: float

    def to_feature_vector(self) -> List[float]:
        """Returns normalized residual vector for ML inference."""
        return [
            self.z_egt,
            self.z_cht,
            self.z_oil_pressure,
            self.z_oil_temp,
            self.z_fuel_flow,
            self.z_vibration
        ]

    def to_dict(self) -> Dict[str, float]:
        return asdict(self)

class ResidualCalculator:
    """Calculates, tracks, and normalizes telemetry residuals against the Digital Twin."""

    def __init__(self, baselines: Dict[str, float] = RESIDUAL_BASELINE_STDS):
        self.baselines = baselines

    def calculate(
        self,
        actual_telemetry: Dict[str, float],
        twin_pred: TwinPrediction
    ) -> SensorResiduals:
        """Compute residuals from actual telemetry and twin predictions."""
        # Raw differences: Delta = Actual - Expected
        raw_egt = actual_telemetry.get("egt_c", 0.0) - twin_pred.egt_c
        raw_cht = actual_telemetry.get("cht_c", 0.0) - twin_pred.cht_c
        raw_oil_p = actual_telemetry.get("oil_pressure_bar", 0.0) - twin_pred.oil_pressure_bar
        raw_oil_t = actual_telemetry.get("oil_temp_c", 0.0) - twin_pred.oil_temp_c
        raw_ff = actual_telemetry.get("fuel_flow_lph", 0.0) - twin_pred.fuel_flow_lph
        raw_vib = actual_telemetry.get("vibration_mms", 0.0) - twin_pred.vibration_mms

        # Normalized z-scores: z = Delta / sigma
        z_egt = raw_egt / self.baselines.get("egt", 12.5)
        z_cht = raw_cht / self.baselines.get("cht", 3.2)
        z_oil_p = raw_oil_p / self.baselines.get("oil_pressure", 0.18)
        z_oil_t = raw_oil_t / self.baselines.get("oil_temp", 2.1)
        z_ff = raw_ff / self.baselines.get("fuel_flow", 0.65)
        z_vib = raw_vib / self.baselines.get("vibration", 0.25)

        # Percentage deviations relative to twin expected value
        pct_egt = (raw_egt / max(1.0, twin_pred.egt_c)) * 100.0
        pct_cht = (raw_cht / max(1.0, twin_pred.cht_c)) * 100.0
        pct_oil_p = (raw_oil_p / max(0.5, twin_pred.oil_pressure_bar)) * 100.0
        pct_oil_t = (raw_oil_t / max(1.0, twin_pred.oil_temp_c)) * 100.0
        pct_ff = (raw_ff / max(1.0, twin_pred.fuel_flow_lph)) * 100.0
        pct_vib = (raw_vib / max(0.1, twin_pred.vibration_mms)) * 100.0

        return SensorResiduals(
            egt_residual=round(raw_egt, 2),
            cht_residual=round(raw_cht, 2),
            oil_pressure_residual=round(raw_oil_p, 3),
            oil_temp_residual=round(raw_oil_t, 2),
            fuel_flow_residual=round(raw_ff, 2),
            vibration_residual=round(raw_vib, 2),
            z_egt=round(z_egt, 3),
            z_cht=round(z_cht, 3),
            z_oil_pressure=round(z_oil_p, 3),
            z_oil_temp=round(z_oil_t, 3),
            z_fuel_flow=round(z_ff, 3),
            z_vibration=round(z_vib, 3),
            pct_egt=round(pct_egt, 2),
            pct_cht=round(pct_cht, 2),
            pct_oil_pressure=round(pct_oil_p, 2),
            pct_oil_temp=round(pct_oil_t, 2),
            pct_fuel_flow=round(pct_ff, 2),
            pct_vibration=round(pct_vib, 2),
        )
