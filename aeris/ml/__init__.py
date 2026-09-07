"""Machine Learning and Diagnostics Suite."""
from .data_generator import SyntheticTelemetryGenerator, FAULT_CLASSES
from .anomaly_detector import IsolationForestAnomalyDetector, AnomalyResult
from .fault_classifier import EngineFaultClassifier, FaultDiagnosis
from .sensor_validator import SensorValidator, SensorConsistencyReport
from .rul_estimator import PhysicsInformedRULEstimator, RULEstimate
from .explainability import XAIEngine, XAIExplanation

__all__ = [
    "SyntheticTelemetryGenerator",
    "FAULT_CLASSES",
    "IsolationForestAnomalyDetector",
    "AnomalyResult",
    "EngineFaultClassifier",
    "FaultDiagnosis",
    "SensorValidator",
    "SensorConsistencyReport",
    "PhysicsInformedRULEstimator",
    "RULEstimate",
    "XAIEngine",
    "XAIExplanation"
]
