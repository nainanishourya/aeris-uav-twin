"""Unit tests for Health Index computation and RUL estimator."""

import pytest
from aeris.core.health_index import HealthIndexCalculator
from aeris.core.residual_engine import SensorResiduals
from aeris.ml.rul_estimator import PhysicsInformedRULEstimator

def test_health_index_bounds_and_monotonicity():
    """Verify health index is bounded between 0 and 100, and decreases with residual divergence."""
    calc = HealthIndexCalculator()

    # Nominal residuals
    healthy_res = SensorResiduals(
        egt_residual=0, cht_residual=0, oil_pressure_residual=0, oil_temp_residual=0,
        fuel_flow_residual=0, vibration_residual=0,
        z_egt=0.2, z_cht=0.1, z_oil_pressure=0.0, z_oil_temp=0.1, z_fuel_flow=0.1, z_vibration=0.1,
        pct_egt=0, pct_cht=0, pct_oil_pressure=0, pct_oil_temp=0, pct_fuel_flow=0, pct_vibration=0
    )
    h_nominal = calc.calculate(healthy_res, anomaly_score=0.0)
    assert 90.0 <= h_nominal.health_index <= 100.0
    assert h_nominal.status_label == "Healthy"

    # Moderate degradation
    degraded_res = SensorResiduals(
        egt_residual=40, cht_residual=8, oil_pressure_residual=-0.4, oil_temp_residual=5,
        fuel_flow_residual=2, vibration_residual=0.4,
        z_egt=2.6, z_cht=2.5, z_oil_pressure=-2.2, z_oil_temp=2.3, z_fuel_flow=2.1, z_vibration=1.6,
        pct_egt=5, pct_cht=6, pct_oil_pressure=-10, pct_oil_temp=5, pct_fuel_flow=10, pct_vibration=20
    )
    h_degraded = calc.calculate(degraded_res, anomaly_score=0.45)
    assert h_degraded.health_index < h_nominal.health_index
    assert h_degraded.status_label in ["Normal/Watch", "Degraded"]

def test_rul_estimation_confidence_interval():
    """Verify RUL returns positive hours, proper confidence bounds, and decreases with health drop."""
    rul_est = PhysicsInformedRULEstimator()

    rul_fresh = rul_est.estimate(current_health_index=96.0, current_flight_hours=100.0, anomaly_score=0.0)
    assert rul_fresh.estimated_rul_hours > 800.0
    assert rul_fresh.confidence_interval_hours[0] < rul_fresh.estimated_rul_hours < rul_fresh.confidence_interval_hours[1]

    rul_worn = rul_est.estimate(current_health_index=45.0, current_flight_hours=800.0, anomaly_score=0.7)
    assert rul_worn.estimated_rul_hours < rul_fresh.estimated_rul_hours
    assert rul_worn.rul_status == "Critical Maintenance Due"
