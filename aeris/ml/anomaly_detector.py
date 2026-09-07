"""Unsupervised Anomaly Detection using Isolation Forest on Physics Residuals."""

import os
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Any, Optional
import numpy as np
import pandas as pd
import joblib
from sklearn.ensemble import IsolationForest

@dataclass
class AnomalyResult:
    is_anomaly: bool
    anomaly_score: float             # 0.0 (strictly nominal) to 1.0 (extreme anomaly)
    raw_decision_score: float
    severity: str                     # "Nominal", "Low", "Medium", "High", "Critical"
    affected_sensors: List[str]
    z_scores: Dict[str, float]

class IsolationForestAnomalyDetector:
    """Unsupervised anomaly detection trained on healthy physics residuals and operational states."""

    FEATURE_COLS = [
        "z_egt",
        "z_cht",
        "z_oil_p",
        "z_oil_t",
        "z_fuel_flow",
        "z_vibration",
        "rpm",
        "engine_load"
    ]

    def __init__(self, contamination: float = 0.02, random_state: int = 42):
        self.contamination = contamination
        self.random_state = random_state
        self.model = IsolationForest(
            n_estimators=120,
            contamination=contamination,
            random_state=random_state,
            n_jobs=-1
        )
        self.is_fitted: bool = False
        self._score_min: float = -0.35
        self._score_max: float = 0.20

    def fit(self, healthy_df: pd.DataFrame) -> "IsolationForestAnomalyDetector":
        """Fits the Isolation Forest on nominal/healthy flight records."""
        X = healthy_df[self.FEATURE_COLS].copy()
        self.model.fit(X)
        self.is_fitted = True
        
        # Calculate decision function statistics on training set to calibrate [0, 1] scoring
        train_scores = self.model.decision_function(X)
        self._score_min = float(np.percentile(train_scores, 1.0))
        self._score_max = float(np.percentile(train_scores, 99.0))
        return self

    def predict(
        self,
        features: Dict[str, float],
        z_dict: Optional[Dict[str, float]] = None
    ) -> AnomalyResult:
        """Evaluates incoming telemetry features for anomalous behavior."""
        if not self.is_fitted:
            # Fallback heuristic if model not loaded
            return self._heuristic_fallback(features, z_dict)

        # Build feature dataframe with exact columns to maintain feature name alignment
        x_vec = pd.DataFrame([{col: features.get(col, 0.0) for col in self.FEATURE_COLS}])
        
        # Isolation Forest decision_function: higher is normal, lower/negative is anomalous
        raw_score = float(self.model.decision_function(x_vec)[0])
        pred = int(self.model.predict(x_vec)[0])  # -1 is anomaly, 1 is normal
        
        # Normalize score into [0.0, 1.0] where 1.0 is maximum anomaly
        # Map: raw_score >= score_max -> 0.0; raw_score <= score_min -> 1.0
        norm_score = (self._score_max - raw_score) / (self._score_max - self._score_min + 1e-6)
        norm_score = float(np.clip(norm_score, 0.0, 1.0))

        # Determine severity tier
        if norm_score < 0.25:
            severity = "Nominal"
            is_anom = False
        elif norm_score < 0.50:
            severity = "Low"
            is_anom = (pred == -1)
        elif norm_score < 0.75:
            severity = "Medium"
            is_anom = True
        elif norm_score < 0.88:
            severity = "High"
            is_anom = True
        else:
            severity = "Critical"
            is_anom = True

        # Identify which sensors are most divergent (z-score >= 2.0)
        z_scores = z_dict or {
            "EGT": abs(features.get("z_egt", 0.0)),
            "CHT": abs(features.get("z_cht", 0.0)),
            "Oil Pressure": abs(features.get("z_oil_p", 0.0)),
            "Oil Temp": abs(features.get("z_oil_t", 0.0)),
            "Fuel Flow": abs(features.get("z_fuel_flow", 0.0)),
            "Vibration": abs(features.get("z_vibration", 0.0)),
        }

        affected = [sensor for sensor, z_val in z_scores.items() if z_val >= 2.0]
        if not affected and is_anom:
            # Pick highest single divergence
            sorted_sensors = sorted(z_scores.items(), key=lambda item: item[1], reverse=True)
            if sorted_sensors:
                affected = [sorted_sensors[0][0]]

        return AnomalyResult(
            is_anomaly=is_anom,
            anomaly_score=round(norm_score, 3),
            raw_decision_score=round(raw_score, 4),
            severity=severity,
            affected_sensors=affected,
            z_scores={k: round(v, 2) for k, v in z_scores.items()}
        )

    def _heuristic_fallback(
        self,
        features: Dict[str, float],
        z_dict: Optional[Dict[str, float]]
    ) -> AnomalyResult:
        """Heuristic calculation when model file is not yet trained."""
        z_vals = [
            abs(features.get("z_egt", 0.0)),
            abs(features.get("z_cht", 0.0)),
            abs(features.get("z_oil_p", 0.0)),
            abs(features.get("z_oil_t", 0.0)),
            abs(features.get("z_fuel_flow", 0.0)),
            abs(features.get("z_vibration", 0.0)),
        ]
        max_z = max(z_vals) if z_vals else 0.0
        score = min(1.0, max_z / 4.5)
        severity = "Nominal" if score < 0.25 else ("Low" if score < 0.5 else ("Medium" if score < 0.75 else "Critical"))
        affected = ["Sensor Residuals"] if score >= 0.5 else []
        return AnomalyResult(
            is_anomaly=(score >= 0.5),
            anomaly_score=round(score, 3),
            raw_decision_score=round(-score, 4),
            severity=severity,
            affected_sensors=affected,
            z_scores={}
        )

    def save(self, filepath: Path):
        filepath.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({
            "model": self.model,
            "score_min": self._score_min,
            "score_max": self._score_max,
            "is_fitted": self.is_fitted
        }, filepath)

    def load(self, filepath: Path) -> "IsolationForestAnomalyDetector":
        if filepath.exists():
            payload = joblib.load(filepath)
            self.model = payload["model"]
            self._score_min = payload["score_min"]
            self._score_max = payload["score_max"]
            self.is_fitted = payload["is_fitted"]
        return self
