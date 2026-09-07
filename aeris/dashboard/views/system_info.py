"""Ground Control Station: System Architecture, ML Model Evaluation & Disclaimers."""

import json
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.figure_factory as ff
from typing import Dict, Any

from aeris.config.settings import settings
from aeris.config.engine_specs import EngineParameters

def render_system_info():
    """Renders system architecture, engineering specs, and ML evaluation results."""
    st.markdown("### ℹ️ System Architecture & Model Intelligence Suite")
    st.caption("AERIS Prototype - Smart India Hackathon 2026 Problem Statement SIH26054 (DRDO)")

    # Architecture Pipeline Diagram
    st.markdown("#### End-to-End Hybrid Architecture Pipeline")
    st.markdown("""
    ```
    ENGINE / SIMULATOR (MQTT / Direct Stream)
      │ (RPM, CHT, EGT, Oil P/T, Fuel Flow, Vib, Batt, Throttle, Alt, Amb Temp, Load)
      ▼
    TELEMETRY GATEWAY & INGESTION (FastAPI / MQTT / SQLite)
      │
      ▼
    VALIDATION & FILTERING (Pydantic / Statistical Bounds)
      │
      ▼
    DIGITAL TWIN (Generic 4-Stroke Turbocharged Aero-Piston Thermodynamic Model)
      │  ├── Energy balance, BSFC, manifold pressure, lubrication hydrodynamics
      │  └── Computes Residual Vector: Δ = Actual - Twin_Expected (Normalized z-scores)
      ▼
    ANALYTICS & SENSOR FUSION ENGINE
      │  ├── Isolation Forest (Unsupervised Anomaly Detection on Residuals)
      │  ├── Multi-Class Random Forest (8 Fault Mode Classifications)
      │  ├── Cross-Sensor Consistency Engine (Drift / Transducer Disambiguation)
      │  ├── Engine Health Index (0-100 composite index across 5 severity tiers)
      │  └── Physics-Informed RUL Estimator (Remaining Useful Life with 90% bounds)
      ▼
    EXPLAINABLE AI (XAI) & PREDICTIVE MAINTENANCE
      │  ├── Feature & Residual Attribution Ranking
      │  └── Model-Driven Actionable Maintenance Work Orders
      ▼
    MISSION SIMULATOR & GROUND CONTROL DASHBOARD
    ```
    """)

    # ML Evaluation Metrics Section
    st.markdown("---")
    st.markdown("#### Machine Learning Evaluation & Validation Metrics")
    
    metrics_file = settings.models_dir / "evaluation_metrics.json"
    if metrics_file.exists():
        with open(metrics_file, "r") as f:
            metrics = json.load(f)

        m_col1, m_col2, m_col3, m_col4 = st.columns(4)
        m_col1.metric("Training Samples", f"{metrics['dataset']['total_samples']:,}", "Synthetic Flight Telemetry")
        m_col2.metric("Classifier Accuracy", f"{metrics['fault_classifier']['accuracy']*100:.1f}%", "9 Classes")
        m_col3.metric("Classifier Weighted F1", f"{metrics['fault_classifier']['weighted_f1']*100:.1f}%", "Test Split (25%)")
        m_col4.metric("Anomaly Det. Precision", f"{metrics['anomaly_detection']['precision']*100:.1f}%", "Isolation Forest")

        # Confusion Matrix
        if "confusion_matrix" in metrics["fault_classifier"]:
            classes = metrics["fault_classifier"]["classes"]
            conf_mat = metrics["fault_classifier"]["confusion_matrix"]

            st.markdown("##### Fault Classifier Confusion Matrix (Test Split)")
            fig_cm = go.Figure(data=go.Heatmap(
                z=conf_mat,
                x=[c[:10] for c in classes],
                y=[c[:10] for c in classes],
                colorscale='Viridis',
                showscale=True,
                hoverongaps=False,
            ))
            fig_cm.update_layout(
                paper_bgcolor="#0d1322",
                plot_bgcolor="#121929",
                font=dict(color="#94a3b8"),
                height=450,
                xaxis=dict(title="Predicted Class"),
                yaxis=dict(title="True Class")
            )
            st.plotly_chart(fig_cm, use_container_width=True)
    else:
        st.info("Model metrics file not found. Run training pipeline to generate.")

    # Engine Physics Baseline Specifications
    st.markdown("---")
    st.markdown("#### Demonstrator Engine Specifications")
    params = EngineParameters()
    spec_col1, spec_col2 = st.columns(2)
    with spec_col1:
        st.markdown(f"""
        - **Displacement**: {params.displacement_cc:.0f} cc
        - **Configuration**: 4-cylinder, 4-stroke, spark ignition
        - **Rated Power**: {params.rated_power_kw:.1f} kW (~115 HP)
        - **Max Takeoff Power**: {params.max_power_kw:.1f} kW (~140 HP)
        - **Max Takeoff RPM**: {params.max_rpm:.0f} RPM
        """)
    with spec_col2:
        st.markdown(f"""
        - **Nominal Cruise RPM**: {params.nominal_cruise_rpm:.0f} RPM
        - **Idle RPM**: {params.idle_rpm:.0f} RPM
        - **Max Turbo Boost**: {params.turbo_boost_max_inhg:.1f} inHg MAP
        - **Cooling Concept**: {params.cooling_type}
        - **Fuel Compatibility**: {params.fuel_type}
        """)

    # Disclaimers
    st.markdown("---")
    st.markdown("""
    <div style="background:#162035; border:1px solid #334155; border-radius:6px; padding:14px; font-size:0.85rem; color:#94a3b8;">
        <strong>RESEARCH & PROTOTYPE DISCLAIMER:</strong><br>
        1. This system uses a generic aero-piston thermodynamic demonstrator model indicative of civilian / dual-use 115-140 HP engines. It does NOT utilize or reveal classified DRDO or defence propulsion parameters.<br>
        2. All training datasets are deterministically synthesized via physics simulations.<br>
        3. Built entirely on free, open-source technologies (Python, FastAPI, Streamlit, Plotly, SQLite, scikit-learn, Mosquitto) for offline, air-gapped readiness.
    </div>
    """, unsafe_allow_html=True)
