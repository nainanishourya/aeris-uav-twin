"""Unit tests for ML models, Anomaly Detection, and Fault Classification."""

import pytest
from aeris.ml.anomaly_detector import IsolationForestAnomalyDetector
from aeris.ml.fault_classifier import EngineFaultClassifier
from aeris.ml.sensor_validator import SensorValidator
from aeris.config.settings import settings

def test_anomaly_detector_nominal_vs_divergent():
    """Verify anomaly detector scores healthy signals low and anomalies high."""
    detector = IsolationForestAnomalyDetector().load(settings.anomaly_model_path)
    
    # Healthy residuals
    healthy_features = {
        "z_egt": 0.2, "z_cht": -0.1, "z_oil_p": 0.0, "z_oil_t": 0.3,
        "z_fuel_flow": 0.1, "z_vibration": 0.2, "rpm": 5000.0, "engine_load": 0.72
    }
    healthy_res = detector.predict(healthy_features)
    assert healthy_res.anomaly_score < 0.50

    # Divergent residuals (e.g. Misfire or Overheating)
    fault_features = {
        "z_egt": -6.5, "z_cht": 4.5, "z_oil_p": -4.2, "z_oil_t": 4.8,
        "z_fuel_flow": 5.0, "z_vibration": 6.2, "rpm": 4800.0, "engine_load": 0.72
    }
    fault_res = detector.predict(fault_features)
    assert fault_res.anomaly_score > 0.60
    assert fault_res.is_anomaly is True

def test_fault_classifier_injector_abnormality():
    """Verify classifier correctly recognizes injector abnormality features."""
    classifier = EngineFaultClassifier().load(settings.fault_classifier_path)
    
    # Features indicative of Injector Abnormality: high fuel flow, high EGT
    injector_features = {
        "z_egt": 3.8, "z_cht": 1.5, "z_oil_p": 0.0, "z_oil_t": 0.2,
        "z_fuel_flow": 5.2, "z_vibration": 1.5,
        "res_egt": 48.0, "res_cht": 5.0, "res_oil_p": 0.0, "res_oil_t": 0.5,
        "res_fuel_flow": 3.5, "res_vibration": 0.4,
        "rpm": 5050.0, "engine_load": 0.75
    }
    diag = classifier.predict(injector_features)
    assert diag.predicted_fault == "Injector Abnormality"
    assert diag.confidence > 0.65
    assert "injector" in diag.maintenance_action.lower()

def test_sensor_validator_drift_disambiguation():
    """Verify that isolated CHT spike is caught as Sensor Drift, NOT engine overheating."""
    validator = SensorValidator()
    
    actual = {
        "cht_c": 165.0, # High CHT
        "egt_c": 715.0, # Normal
        "oil_pressure_bar": 4.2, # Normal
        "oil_temp_c": 88.0, # Normal
        "fuel_flow_lph": 20.0,
        "vibration_mms": 1.4,
        "rpm": 5000.0
    }
    twin_exp = {
        "cht_c": 105.0,
        "egt_c": 715.0,
        "oil_pressure_bar": 4.2,
        "oil_temp_c": 88.0
    }
    residuals = {
        "z_cht": 4.2,
        "z_egt": 0.1,
        "z_oil_p": 0.0,
        "z_oil_t": 0.2,
        "z_vibration": 0.1
    }

    report = validator.evaluate(actual, twin_exp, residuals)
    assert report.all_sensors_valid is False
    assert "CHT Sensor" in report.suspect_sensors
    assert report.channel_reports["cht"].status == "Drift Warning"
