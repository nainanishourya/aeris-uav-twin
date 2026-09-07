"""Unit tests for the Residual Engine."""

import pytest
from aeris.core.physics_twin import AeroPistonTwin
from aeris.core.residual_engine import ResidualCalculator

def test_residual_calculation_zero_deviation():
    """Residual should be near zero when actual matches twin prediction exactly."""
    twin = AeroPistonTwin()
    calc = ResidualCalculator()
    pred = twin.predict(rpm=5000.0, throttle=0.7)

    actual = {
        "egt_c": pred.egt_c,
        "cht_c": pred.cht_c,
        "oil_pressure_bar": pred.oil_pressure_bar,
        "oil_temp_c": pred.oil_temp_c,
        "fuel_flow_lph": pred.fuel_flow_lph,
        "vibration_mms": pred.vibration_mms
    }

    res = calc.calculate(actual, pred)
    assert abs(res.egt_residual) < 1e-4
    assert abs(res.cht_residual) < 1e-4
    assert abs(res.z_egt) < 1e-4
    assert abs(res.z_oil_pressure) < 1e-4

def test_residual_normalization():
    """Verify that z-scores scale correctly according to channel baseline std dev."""
    twin = AeroPistonTwin()
    calc = ResidualCalculator()
    pred = twin.predict(rpm=5000.0, throttle=0.7)

    # Inject +25°C EGT residual (baseline std dev for EGT is 12.5°C -> expected z = +2.0)
    actual = {
        "egt_c": pred.egt_c + 25.0,
        "cht_c": pred.cht_c,
        "oil_pressure_bar": pred.oil_pressure_bar,
        "oil_temp_c": pred.oil_temp_c,
        "fuel_flow_lph": pred.fuel_flow_lph,
        "vibration_mms": pred.vibration_mms
    }

    res = calc.calculate(actual, pred)
    assert pytest.approx(res.egt_residual, 0.05) == 25.0
    assert pytest.approx(res.z_egt, 0.05) == 2.0
