"""Ground Control Station: Predictive Health & Remaining Useful Life (RUL) Trajectory."""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from typing import Dict, Any

from aeris.dashboard.styles import PLOTLY_DARK_THEME, get_dark_layout
from aeris.ml.rul_estimator import PhysicsInformedRULEstimator

def render_health_rul_view(latest: Dict[str, Any], sim):
    """Renders Predictive Health degradation and physics-informed RUL forecasting."""
    st.markdown("### ⏳ Predictive Degradation & Remaining Useful Life (RUL)")
    st.caption("Physics-informed cumulative damage accumulation model predicting time-to-critical degradation.")

    if not latest:
        st.warning("Awaiting health calculation stream...")
        return

    health = latest.get("health_index", 95.0)
    anom_score = latest.get("anomaly_score", 0.0)
    curr_hours = sim.flight_hours

    # Run RUL Estimator
    rul_est = PhysicsInformedRULEstimator()
    rul_result = rul_est.estimate(
        current_health_index=health,
        current_flight_hours=curr_hours,
        anomaly_score=anom_score,
        sub_healths={
            "thermal": latest.get("thermal_health", 95.0),
            "lubrication": latest.get("lubrication_health", 95.0),
            "vibration": latest.get("vibration_health", 95.0),
            "efficiency": latest.get("efficiency_health", 95.0),
        }
    )

    # RUL Status Cards
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric(
            label="Estimated Remaining Useful Life",
            value=f"{rul_result.estimated_rul_hours:.0f} Flight Hrs",
            delta=f"TBO: 1400.0 hrs"
        )
    with c2:
        st.metric(
            label="90% Confidence Interval",
            value=f"[{rul_result.confidence_interval_hours[0]:.0f} - {rul_result.confidence_interval_hours[1]:.0f}] hrs",
            delta=f"Uncertainty: ±{(rul_result.confidence_interval_hours[1] - rul_result.estimated_rul_hours):.0f}h"
        )
    with c3:
        st.metric(
            label="Current Operating Hours",
            value=f"{curr_hours:.1f} hrs",
            delta="Logbook Flight Time"
        )
    with c4:
        st.metric(
            label="Limiting Sub-System",
            value=rul_result.limiting_component,
            delta=f"Status: {rul_result.rul_status}"
        )

    st.markdown(f"""
    <div style="font-size:0.78rem; color:#64748b; margin-bottom:16px; font-style:italic;">
        {rul_result.disclaimer}
    </div>
    """, unsafe_allow_html=True)

    # Future Health Trajectory Projection Chart
    traj_df = pd.DataFrame(rul_result.health_trajectory)
    
    fig_rul = go.Figure()
    # Historic operational line
    fig_rul.add_trace(go.Scatter(
        x=[curr_hours - 20, curr_hours],
        y=[min(100.0, health + 2.0), health],
        name="Historic Engine Health",
        mode="lines+markers",
        line=dict(color="#00e5a3", width=3)
    ))
    # Projected degradation trajectory
    fig_rul.add_trace(go.Scatter(
        x=traj_df["total_flight_hours"],
        y=traj_df["projected_health"],
        name="Forward Projected Health",
        mode="lines+markers",
        line=dict(color="#38bdf8", width=2.5, dash="dash")
    ))
    # Threshold zones
    fig_rul.add_hline(y=90, line_color="#00e5a3", line_dash="dot", annotation_text="Healthy Tier (90)")
    fig_rul.add_hline(y=70, line_color="#38bdf8", line_dash="dot", annotation_text="Watch Tier (70)")
    fig_rul.add_hline(y=50, line_color="#f59e0b", line_dash="dot", annotation_text="Degraded Tier (50)")
    fig_rul.add_hline(y=30, line_color="#ef4444", line_dash="dash", annotation_text="CRITICAL OVERHAUL LIMIT (30)")

    fig_rul.update_layout(
        **get_dark_layout(height=380),
        title="Physics-Informed Health Degradation Curve & RUL Horizon",
        xaxis_title="Cumulative Flight Hours",
        yaxis_title="Engine Health Index (0-100)"
    )
    st.plotly_chart(fig_rul, width='stretch')

    # Health Index Tier Reference Table
    with st.expander("ℹ️ Engine Health Index Tier Architecture", expanded=False):
        st.markdown("""
        | Health Score | Severity Tier | Operational Directive |
        | :--- | :--- | :--- |
        | **90 – 100** | 🟢 **Healthy** | Nominal UAV flight clearance. Standard scheduled line maintenance. |
        | **70 – 89** | 🔵 **Normal / Watch** | Normal telemetry within acceptable wear bounds. Monitor minor residual drift. |
        | **50 – 69** | 🟡 **Degraded** | Noticeable performance divergence. Schedule borescope & component inspection. |
        | **30 – 49** | 🟠 **Critical** | Accelerated thermal or mechanical damage. Restrict flight envelope / RTB. |
        | **0 – 29** | 🔴 **Severe** | Imminent failure risk. Immediate engine shutdown and mandatory overhaul. |
        """)
