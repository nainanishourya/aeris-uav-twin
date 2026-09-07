"""Unit tests for the Aero-Piston Physics Digital Twin."""

import pytest
from aeris.core.physics_twin import AeroPistonTwin, TwinPrediction

def test_atmospheric_model():
    """Verify atmospheric pressure and density lapse with altitude."""
    sea_level = AeroPistonTwin.atmospheric_model(0.0, 15.0)
    high_alt = AeroPistonTwin.atmospheric_model(5000.0, -17.5)

    assert sea_level["pressure_pa"] > high_alt["pressure_pa"]
    assert sea_level["density_kgm3"] > high_alt["density_kgm3"]
    assert 1.20 <= sea_level["density_kgm3"] <= 1.25

def test_twin_prediction_cruise():
    """Verify digital twin produces physically valid engine state under cruise."""
    twin = AeroPistonTwin()
    pred = twin.predict(rpm=5000.0, throttle=0.72, altitude_m=2000.0, ambient_temp_c=10.0)

    assert isinstance(pred, TwinPrediction)
    assert 650.0 <= pred.egt_c <= 820.0
    assert 85.0 <= pred.cht_c <= 135.0
    assert 2.5 <= pred.oil_pressure_bar <= 5.5
    assert 75.0 <= pred.oil_temp_c <= 115.0
    assert 10.0 <= pred.fuel_flow_lph <= 35.0
    assert 0.5 <= pred.vibration_mms <= 4.0
    assert 0.20 <= pred.engine_efficiency <= 0.38

def test_twin_power_scaling_with_rpm():
    """Verify brake power scales up with RPM and throttle."""
    twin = AeroPistonTwin()
    idle = twin.predict(rpm=1600.0, throttle=0.2, altitude_m=500.0)
    cruise = twin.predict(rpm=5000.0, throttle=0.75, altitude_m=500.0)
    takeoff = twin.predict(rpm=5800.0, throttle=1.0, altitude_m=500.0)

    assert idle.brake_power_kw < cruise.brake_power_kw < takeoff.brake_power_kw
    assert idle.fuel_flow_lph < cruise.fuel_flow_lph < takeoff.fuel_flow_lph
