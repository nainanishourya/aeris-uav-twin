"""Application settings and environment configurations."""

import os
from pathlib import Path
from dataclasses import dataclass, field

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "models"

@dataclass
class Settings:
    app_name: str = "AERIS - AI Engine Reliability & Intelligence System"
    version: str = "1.0.0"
    base_dir: Path = BASE_DIR
    data_dir: Path = DATA_DIR
    models_dir: Path = MODELS_DIR
    
    # SQLite Database
    db_path: Path = DATA_DIR / "aeris_telemetry.db"
    
    # MQTT Configuration
    mqtt_broker_host: str = os.getenv("AERIS_MQTT_HOST", "localhost")
    mqtt_broker_port: int = int(os.getenv("AERIS_MQTT_PORT", 1883))
    mqtt_uav_id: str = os.getenv("AERIS_UAV_ID", "UAV-MALE-01")
    mqtt_keepalive: int = 60
    
    # Telemetry Topics
    topic_telemetry: str = f"aeris/uav/{mqtt_uav_id}/engine/telemetry"
    topic_health: str = f"aeris/uav/{mqtt_uav_id}/engine/health"
    topic_alerts: str = f"aeris/uav/{mqtt_uav_id}/engine/alerts"
    topic_diagnostics: str = f"aeris/uav/{mqtt_uav_id}/engine/diagnostics"
    
    # ML Models paths
    anomaly_model_path: Path = MODELS_DIR / "isolation_forest.joblib"
    fault_classifier_path: Path = MODELS_DIR / "fault_classifier.joblib"
    rul_model_path: Path = MODELS_DIR / "rul_regressor.joblib"
    scaler_path: Path = MODELS_DIR / "feature_scaler.joblib"
    
    # Sampling frequency (Hz)
    telemetry_rate_hz: float = 1.0

# Singleton settings instance
settings = Settings()

# Ensure directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR.mkdir(parents=True, exist_ok=True)
