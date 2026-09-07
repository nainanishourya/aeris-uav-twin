"""Model Training and Evaluation Pipeline for AERIS.

Performs:
1. Generation of synthetic flight telemetry datasets
2. Train / Test split
3. Unsupervised Isolation Forest training and validation
4. Multi-class Fault Classifier training with full metric report (Precision, Recall, F1, Confusion Matrix)
5. Model persistence into `models/` directory.
"""

import json
from pathlib import Path
from typing import Dict, Any
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix, precision_recall_fscore_support

from aeris.config.settings import settings
from aeris.ml.data_generator import SyntheticTelemetryGenerator, FAULT_CLASSES
from aeris.ml.anomaly_detector import IsolationForestAnomalyDetector
from aeris.ml.fault_classifier import EngineFaultClassifier

def run_training_pipeline(save_models: bool = True) -> Dict[str, Any]:
    """Runs complete model generation, training, and evaluation workflow."""
    print("=" * 60)
    print("AERIS: Starting Physics-Anchored ML Training Pipeline...")
    print("=" * 60)

    # 1. Generate Synthetic Corpus
    print("[1/4] Generating synthetic telemetry training corpus...")
    gen = SyntheticTelemetryGenerator(seed=42)
    corpus_df = gen.generate_training_corpus(
        nominal_flights=20,
        fault_flights_per_class=5,
        flight_duration=600
    )
    print(f"      Total telemetry samples generated: {len(corpus_df):,}")
    print(f"      Class distribution:\n{corpus_df['fault_label'].value_counts().to_string()}")

    # 2. Train Isolation Forest (strictly on Healthy records)
    print("\n[2/4] Training Isolation Forest on nominal physics residuals...")
    healthy_subset = corpus_df[corpus_df["fault_label"] == "Healthy"].copy()
    iso_detector = IsolationForestAnomalyDetector(contamination=0.03, random_state=42)
    iso_detector.fit(healthy_subset)

    # Evaluate Anomaly Detector on full dataset using fast vectorized matrix
    X_anom = corpus_df[iso_detector.FEATURE_COLS]
    raw_preds = iso_detector.model.predict(X_anom)
    predicted_anom = np.array([1 if p == -1 else 0 for p in raw_preds])
    ground_truth_anom = corpus_df["is_anomaly"].values
    
    anom_precision, anom_recall, anom_f1, _ = precision_recall_fscore_support(
        ground_truth_anom, predicted_anom, average="binary", zero_division=0
    )
    print(f"      Anomaly Detection - Precision: {anom_precision:.3f} | Recall: {anom_recall:.3f} | F1: {anom_f1:.3f}")

    # 3. Train Multi-Class Fault Classifier
    print("\n[3/4] Training Multi-Class Random Forest Fault Classifier...")
    train_df, test_df = train_test_split(
        corpus_df,
        test_size=0.25,
        random_state=42,
        stratify=corpus_df["fault_label"]
    )
    
    classifier = EngineFaultClassifier(random_state=42)
    classifier.fit(train_df)

    # Evaluate on Test Set
    X_test = test_df[classifier.FEATURE_COLS]
    y_test = test_df["fault_label"]
    y_pred = classifier.model.predict(X_test)

    clf_report = classification_report(y_test, y_pred, output_dict=True, zero_division=0)
    conf_mat = confusion_matrix(y_test, y_pred, labels=classifier.classes_)

    print("\n--- FAULT CLASSIFIER EVALUATION REPORT ---")
    print(classification_report(y_test, y_pred, zero_division=0))

    # 4. Model Persistence
    metrics = {
        "dataset": {
            "total_samples": len(corpus_df),
            "train_samples": len(train_df),
            "test_samples": len(test_df),
            "features": classifier.FEATURE_COLS
        },
        "anomaly_detection": {
            "model": "IsolationForest",
            "precision": round(float(anom_precision), 4),
            "recall": round(float(anom_recall), 4),
            "f1_score": round(float(anom_f1), 4)
        },
        "fault_classifier": {
            "model": "RandomForestClassifier",
            "accuracy": round(float(clf_report.get("accuracy", 0.0)), 4),
            "macro_f1": round(float(clf_report.get("macro avg", {}).get("f1-score", 0.0)), 4),
            "weighted_f1": round(float(clf_report.get("weighted avg", {}).get("f1-score", 0.0)), 4),
            "classes": classifier.classes_,
            "confusion_matrix": conf_mat.tolist()
        }
    }

    if save_models:
        print("[4/4] Persisting trained models to disk...")
        iso_detector.save(settings.anomaly_model_path)
        classifier.save(settings.fault_classifier_path)
        
        # Save metrics json
        metrics_file = settings.models_dir / "evaluation_metrics.json"
        with open(metrics_file, "w") as f:
            json.dump(metrics, f, indent=2)
        print(f"      Saved models to: {settings.models_dir}")
        print(f"      Saved evaluation metrics to: {metrics_file}")

    print("=" * 60)
    print("AERIS Training Pipeline Completed Successfully!")
    print("=" * 60)
    return metrics

if __name__ == "__main__":
    run_training_pipeline()
