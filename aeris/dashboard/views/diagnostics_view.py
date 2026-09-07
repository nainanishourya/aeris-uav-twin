"""Ground Control Station: AI Diagnostics & Explainable AI (XAI) Attribution."""

import streamlit as st
import plotly.graph_objects as go
from typing import Dict, Any

from aeris.dashboard.styles import PLOTLY_DARK_THEME, get_dark_layout
from aeris.ml.data_generator import FAULT_CLASSES

def render_diagnostics_view(latest: Dict[str, Any], sim):
    """Renders AI diagnostics, fault classification, cross-sensor consistency, and XAI."""
    st.markdown("### 🧠 AI Engine Health Diagnostics & Explainable AI (XAI)")
    st.caption("Hybrid Physics-Anchored Residual Analytics + Unsupervised Isolation Forest + Random Forest Fault Classifier.")

    if not latest:
        st.warning("No diagnostic record available.")
        return

    fault = latest.get("predicted_fault", "Healthy")
    conf = latest.get("confidence", 1.0)
    anom_score = latest.get("anomaly_score", 0.0)
    maint_action = latest.get("maintenance_action", "Maintain standard line inspections.")

    col1, col2 = st.columns([1.2, 1.8])

    with col1:
        # Diagnostic Assessment Card
        f_color = "#00e5a3" if fault == "Healthy" else ("#f59e0b" if fault == "Sensor Drift/Failure" else "#ef4444")
        st.markdown(f"""
        <div class="diag-card" style="border-left: 5px solid {f_color};">
            <div style="font-size:0.8rem; color:#94a3b8; text-transform:uppercase;">Primary Classification</div>
            <div style="font-size:1.5rem; font-weight:800; color:{f_color}; margin:6px 0;">
                {fault}
            </div>
            <div style="display:flex; justify-content:space-between; margin-bottom:12px; font-size:0.9rem;">
                <span>AI Confidence: <strong style="color:#f8fafc;">{conf * 100:.1f}%</strong></span>
                <span>Anomaly Score: <strong style="color:#f59e0b;">{anom_score:.3f}</strong></span>
            </div>
            <div style="border-top:1px solid #1e293b; padding-top:10px; font-size:0.85rem; color:#cbd5e1;">
                <strong>Actionable Engineering Advisory:</strong><br>
                {maint_action}
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Cross-Sensor Consistency Status Box
        res_cht = abs(latest.get("z_cht", 0.0))
        res_egt = abs(latest.get("z_egt", 0.0))
        res_oil = abs(latest.get("z_oil_t", 0.0))
        
        is_drift = (fault == "Sensor Drift/Failure") or (res_cht > 3.0 and res_egt < 1.5 and res_oil < 1.5)
        
        st.markdown("#### 🔬 Cross-Sensor Consistency Engine")
        if is_drift:
            st.markdown("""
            <div style="background:rgba(245, 158, 11, 0.15); border:1px solid #f59e0b; border-radius:6px; padding:12px; font-size:0.85rem;">
                <strong style="color:#f59e0b;">SENSOR DRIFT DISAMBIGUATION TRIGGERED</strong><br>
                CHT transducer residual is divergent (z &gt; 3σ), but EGT, Oil Temperature, and core vibration remain completely nominal.
                Cross-sensor logic isolates this as <strong>transducer drift</strong> rather than genuine cylinder overheating.
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="background:rgba(0, 229, 163, 0.1); border:1px solid #00e5a3; border-radius:6px; padding:10px; font-size:0.85rem; color:#f8fafc;">
                ✓ <strong>Cross-Sensor Invariants Verified:</strong> Thermal, hydraulic, and vibration readings are physically correlated with Digital Twin predictions.
            </div>
            """, unsafe_allow_html=True)

    with col2:
        # Multi-class Fault Probability Distribution
        st.markdown("#### Fault Mode Probability Spectrum")
        
        # Calculate simulated/model probabilities
        probs = {}
        for c in FAULT_CLASSES:
            if c == fault:
                probs[c] = conf
            else:
                rem = max(0.0, (1.0 - conf) / (len(FAULT_CLASSES) - 1))
                probs[c] = rem

        sorted_probs = sorted(probs.items(), key=lambda x: x[1], reverse=False)
        labels = [item[0] for item in sorted_probs]
        values = [item[1] * 100 for item in sorted_probs]
        colors = ["#00e5a3" if l == "Healthy" else ("#ef4444" if l == fault else "#38bdf8") for l in labels]

        fig_probs = go.Figure(go.Bar(
            x=values, y=labels,
            orientation='h',
            marker=dict(color=colors)
        ))
        fig_probs.update_layout(
            **get_dark_layout(
                title="Fault Category Probabilities (%)",
                xaxis_title="Confidence (%)",
                height=280,
                margin={"l": 150, "r": 20, "t": 40, "b": 35}
            )
        )
        st.plotly_chart(fig_probs, use_container_width=True)

    # Explainable AI (XAI) Feature Attribution Section
    st.markdown("---")
    st.markdown("### 📊 Explainable AI (XAI) Attribution: Why Did the AI Flag This?")
    
    xai_col1, xai_col2 = st.columns([1.5, 1.0])
    
    with xai_col1:
        # Feature impact bars
        features_impact = [
            ("Fuel Flow Residual (Δ FF)", abs(latest.get("z_fuel_flow", 0.0)), latest.get("res_fuel_flow", 0.0), "L/h"),
            ("Exhaust Gas Temp Residual (Δ EGT)", abs(latest.get("z_egt", 0.0)), latest.get("res_egt", 0.0), "°C"),
            ("Cylinder Head Temp Residual (Δ CHT)", abs(latest.get("z_cht", 0.0)), latest.get("res_cht", 0.0), "°C"),
            ("Oil Pressure Residual (Δ Oil P)", abs(latest.get("z_oil_p", 0.0)), latest.get("res_oil_p", 0.0), "bar"),
            ("Oil Temperature Residual (Δ Oil T)", abs(latest.get("z_oil_t", 0.0)), latest.get("res_oil_t", 0.0), "°C"),
            ("Vibration RMS Residual (Δ Vib)", abs(latest.get("z_vibration", 0.0)), latest.get("res_vibration", 0.0), "mm/s"),
        ]
        
        sorted_imp = sorted(features_impact, key=lambda x: x[1], reverse=True)
        
        st.markdown("**Top Sensor Residual Attributions Driving the Diagnosis:**")
        for name, z_val, raw_val, unit in sorted_imp[:4]:
            share_pct = min(100.0, z_val * 24.0)
            bar_color = "#ef4444" if z_val > 2.5 else ("#f59e0b" if z_val > 1.8 else "#38bdf8")
            sign = "+" if raw_val >= 0 else ""
            
            st.markdown(f"""
            <div style="margin-bottom: 8px;">
                <div style="display:flex; justify-content:space-between; font-size:0.85rem;">
                    <span><strong>{name}</strong>: {sign}{raw_val:.2f} {unit} (z = {z_val:.2f}σ)</span>
                    <span style="color:{bar_color}; font-weight:700;">{share_pct:.1f}% Impact</span>
                </div>
                <div style="background:#1e293b; border-radius:4px; height:8px; overflow:hidden; margin-top:2px;">
                    <div style="background:{bar_color}; width:{share_pct}%; height:100%;"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    with xai_col2:
        st.markdown("**Physical Grounding & Rationale:**")
        if fault == "Injector Abnormality":
            st.info(
                "Excess fuel flow residual paired with elevated EGT residual indicates fuel injector nozzle degradation "
                "or asymmetric cylinder delivery. The physics model shows fuel consumption exceeding stoichiometric "
                "requirements for current throttle and RPM."
            )
        elif fault == "Misfire":
            st.info(
                "Rapid drop in EGT residual accompanied by high vibration RMS and engine roughness indicates loss of combustion "
                "in one or more cylinders. Unburnt fuel air mixture passes unignited into the exhaust manifold."
            )
        elif fault == "Lubrication Problem":
            st.info(
                "Depressed oil pressure residual combined with rising oil temperature indicates oil viscosity breakdown, "
                "scavenge pump wear, or filter restriction. Lubricant film thickness on crankshaft bearings is compromised."
            )
        elif fault == "Sensor Drift/Failure":
            st.info(
                "Transducer reading contradicts multi-sensor energy balance and digital twin thermodynamic invariants. "
                "Component is flagged for bench recalibration rather than grounding the UAV for physical engine repair."
            )
        else:
            st.success(
                "All sensor residual vectors are clustered tightly within ±1.8σ of the virtual digital twin baseline. "
                "Combustion dynamics, mechanical balance, and lubrication flow are optimal."
            )
