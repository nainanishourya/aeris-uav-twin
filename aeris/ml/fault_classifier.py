"""Multi-Class Fault Classification Engine for Aero-Piston Engine."""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
import numpy as np
import pandas as pd
import joblib
from sklearn.ensemble import RandomForestClassifier

from aeris.ml.data_generator import FAULT_CLASSES

@dataclass
class FaultDiagnosis:
    predicted_fault: str
    confidence: float                 # 0.0 to 1.0 (probability of top class)
    severity: str                     # "Nominal", "Advisory", "Caution", "Critical", "Emergency"
    probabilities: Dict[str, float]
    contributing_features: List[Dict[str, Any]]
    explanation: str
    maintenance_action: str

# Rule & knowledge-base maintenance actions mapping
MAINTENANCE_ADVISORY_MAP = {
    "Healthy": (
        "Engine operating within nominal physics bounds.",
        "Continue scheduled line maintenance and standard pre-flight inspections."
    ),
    "Misfire": (
        "Sharp EGT drop accompanied by elevated vibration and RPM roughness indicates incomplete combustion in one or more cylinders.",
        "Inspect spark plugs, ignition harness, and high-tension leads. Perform cylinder compression check."
    ),
    "Injector Abnormality": (
        "Fuel flow residual is high alongside elevated EGT and thermal imbalance, indicating nozzle clogging, leakage, or calibration drift.",
        "Inspect fuel injection rail, ultrasonic clean injector nozzles, verify fuel spray pattern, and re-calibrate ECU fuel delivery map."
    ),
    "Lubrication Problem": (
        "Significant negative oil pressure residual combined with rising oil temperature indicates lubrication distress.",
        "Check engine oil quantity, inspect oil filter for metal filings/debris, inspect oil pressure relief valve, and examine oil scavenger pump."
    ),
    "Sensor Drift/Failure": (
        "Isolated sensor divergence detected while thermodynamic cross-sensors and physics model verify normal core engine states.",
        "Perform cross-sensor bench calibration, check transducer wiring and harness ground, replace suspected probe."
    ),
    "Combustion Instability": (
        "Cyclic combustion fluctuations and elevated vibration variance detected across multiple engine firing cycles.",
        "Check intake manifold airtightness, inspect turbo wastegate actuator for hunting, and inspect fuel pressure regulator."
    ),
    "Overheating": (
        "Concurrently elevated CHT and Oil Temperature residuals indicate heat dissipation bottleneck or coolant loss.",
        "Inspect liquid cooling radiator, verify coolant glycol ratio, inspect ram-air cowl flaps and cooling air ducts."
    ),
    "Abnormal Vibration": (
        "Vibration harmonic amplitude exceeds structural limits without combustion thermal anomalies.",
        "Inspect propeller dynamic balance, inspect rubber engine mount vibration isolators, and inspect reduction gearbox backlash."
    ),
    "General Degradation": (
        "Uniform moderate degradation across thermal efficiency, oil pressure, and specific fuel consumption.",
        "Schedule comprehensive 100-hour overhaul inspection, borescope cylinder walls, and evaluate valve seat wear."
    )
}

class EngineFaultClassifier:
    """Random Forest classifier for 8 aero-piston fault modes + nominal operations."""

    FEATURE_COLS = [
        "z_egt",
        "z_cht",
        "z_oil_p",
        "z_oil_t",
        "z_fuel_flow",
        "z_vibration",
        "res_egt",
        "res_cht",
        "res_oil_p",
        "res_oil_t",
        "res_fuel_flow",
        "res_vibration",
        "rpm",
        "engine_load"
    ]

    def __init__(self, random_state: int = 42):
        self.random_state = random_state
        self.model = RandomForestClassifier(
            n_estimators=120,
            max_depth=12,
            min_samples_split=4,
            random_state=random_state,
            class_weight="balanced",
            n_jobs=-1
        )
        self.classes_ = FAULT_CLASSES
        self.is_fitted: bool = False

    def fit(self, train_df: pd.DataFrame) -> "EngineFaultClassifier":
        """Fit classifier on synthetic training corpus."""
        X = train_df[self.FEATURE_COLS].copy()
        y = train_df["fault_label"].copy()
        self.model.fit(X, y)
        self.classes_ = list(self.model.classes_)
        self.is_fitted = True
        return self

    def predict(
        self,
        features: Dict[str, float],
        z_dict: Optional[Dict[str, float]] = None
    ) -> FaultDiagnosis:
        """Classify fault and generate explainable diagnostics with maintenance action."""
        if not self.is_fitted:
            return self._heuristic_diagnose(features)

        x_vec = pd.DataFrame([{col: features.get(col, 0.0) for col in self.FEATURE_COLS}])
        probs = self.model.predict_proba(x_vec)[0]
        top_idx = int(np.argmax(probs))
        pred_label = self.classes_[top_idx]
        confidence = float(probs[top_idx])

        # Probabilities dictionary
        prob_dict = {cls: round(float(p), 3) for cls, p in zip(self.classes_, probs)}

        # Determine severity
        if pred_label == "Healthy":
            severity = "Nominal"
        elif confidence < 0.60:
            severity = "Advisory"
        elif pred_label in ["Misfire", "Lubrication Problem", "Overheating"]:
            severity = "Critical" if confidence > 0.75 else "Caution"
        else:
            severity = "Caution" if confidence > 0.70 else "Advisory"

        # Feature contributions: calculate impact of normalized residuals
        contributions = []
        feature_labels = {
            "z_egt": ("EGT Residual", abs(features.get("z_egt", 0.0))),
            "z_cht": ("CHT Residual", abs(features.get("z_cht", 0.0))),
            "z_oil_p": ("Oil Pressure Residual", abs(features.get("z_oil_p", 0.0))),
            "z_oil_t": ("Oil Temp Residual", abs(features.get("z_oil_t", 0.0))),
            "z_fuel_flow": ("Fuel Flow Residual", abs(features.get("z_fuel_flow", 0.0))),
            "z_vibration": ("Vibration Residual", abs(features.get("z_vibration", 0.0))),
        }
        
        # Sort by residual deviation magnitude
        sorted_features = sorted(feature_labels.items(), key=lambda item: item[1][1], reverse=True)
        for _, (name, val) in sorted_features[:4]:
            contributions.append({
                "feature": name,
                "importance_score": round(val, 2),
                "formatted_weight": f"{min(100.0, val * 22.0):.1f}%"
            })

        # Explanations and maintenance recommendations
        expl, maint = MAINTENANCE_ADVISORY_MAP.get(
            pred_label,
            ("Unknown condition detected.", "Conduct general engine diagnostic scan.")
        )

        return FaultDiagnosis(
            predicted_fault=pred_label,
            confidence=round(confidence, 3),
            severity=severity,
            probabilities=prob_dict,
            contributing_features=contributions,
            explanation=expl,
            maintenance_action=maint
        )

    def _heuristic_diagnose(self, features: Dict[str, float]) -> FaultDiagnosis:
        """Heuristic rule diagnosis prior to fitting."""
        z_egt = features.get("z_egt", 0.0)
        z_cht = features.get("z_cht", 0.0)
        z_oil_p = features.get("z_oil_p", 0.0)
        z_oil_t = features.get("z_oil_t", 0.0)
        z_ff = features.get("z_fuel_flow", 0.0)
        z_vib = features.get("z_vibration", 0.0)

        if abs(z_cht) > 3.0 and abs(z_egt) < 1.5 and abs(z_oil_t) < 1.5:
            pred = "Sensor Drift/Failure"
            conf = 0.85
        elif z_egt < -3.0 and z_vib > 2.0:
            pred = "Misfire"
            conf = 0.90
        elif z_ff > 2.5 and z_egt > 2.0:
            pred = "Injector Abnormality"
            conf = 0.88
        elif z_oil_p < -2.5 and z_oil_t > 2.0:
            pred = "Lubrication Problem"
            conf = 0.92
        elif z_cht > 2.5 and z_oil_t > 2.0:
            pred = "Overheating"
            conf = 0.86
        elif z_vib > 3.0:
            pred = "Abnormal Vibration"
            conf = 0.84
        else:
            pred = "Healthy"
            conf = 0.95

        expl, maint = MAINTENANCE_ADVISORY_MAP.get(pred, ("Nominal", "Inspect"))
        return FaultDiagnosis(
            predicted_fault=pred,
            confidence=conf,
            severity="Nominal" if pred == "Healthy" else "Caution",
            probabilities={c: 0.1 for c in FAULT_CLASSES},
            contributing_features=[],
            explanation=expl,
            maintenance_action=maint
        )

    def save(self, filepath: Path):
        filepath.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({
            "model": self.model,
            "classes": self.classes_,
            "is_fitted": self.is_fitted
        }, filepath)

    def load(self, filepath: Path) -> "EngineFaultClassifier":
        if filepath.exists():
            payload = joblib.load(filepath)
            self.model = payload["model"]
            self.classes_ = payload["classes"]
            self.is_fitted = payload["is_fitted"]
        return self
