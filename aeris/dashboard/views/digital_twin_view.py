"""Ground Control Station: Digital Twin vs Actual Telemetry & Residual Divergence."""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from typing import List, Dict, Any

from aeris.dashboard.styles import PLOTLY_DARK_THEME

def render_digital_twin_view(latest: Dict[str, Any], history: List[Dict[str, Any]]):
    """Renders Digital Twin comparison overlays and residual vectors."""
    st.markdown("### 🧬 Physics Digital Twin vs Actual Engine Telemetry")
    st.caption(
        "Generic 4-Stroke Turbocharged Aero-Piston Thermodynamic Model. "
        "Calculates expected physical parameters from RPM, throttle, altitude, and ambient temperature."
    )

    if not latest:
        st.warning("Awaiting Digital Twin synchronization...")
        return

    # Digital Twin Schematic & Thermodynamic Status
    with st.expander("🛠️ Virtual Aero-Piston Core Physics Status", expanded=True):
        sc1, sc2, sc3, sc4 = st.columns(4)
        sc1.metric("Expected Power", f"{latest.get('engine_load', 0.7) * 98:.1f} kW", f"{latest.get('rpm', 5000):.0f} RPM")
        sc2.metric("Manifold Pressure", f"{latest.get('twin_map_inhg', 32.5):.1f} inHg", "Turbo Boost Active")
        sc3.metric("Thermal Efficiency", f"{latest.get('twin_efficiency', 0.31)*100:.1f}%", "Nominal 31-34%")
        sc4.metric("Ambient Density Ratio", f"{1.0 - (latest.get('altitude_m', 2000)/10000)*0.6:.3f}", f"Alt: {latest.get('altitude_m', 2000):.0f}m")

    # Residual Cards Row
    st.markdown("#### Normalized Residual Vector (Δ = Actual - Twin Expected)")
    r1, r2, r3, r4, r5, r6 = st.columns(6)

    residuals_data = [
        ("EGT Residual", latest.get("res_egt", 0.0), "°C", latest.get("z_egt", 0.0), r1),
        ("CHT Residual", latest.get("res_cht", 0.0), "°C", latest.get("z_cht", 0.0), r2),
        ("Oil P Residual", latest.get("res_oil_p", 0.0), "bar", latest.get("z_oil_p", 0.0), r3),
        ("Oil T Residual", latest.get("res_oil_t", 0.0), "°C", latest.get("z_oil_t", 0.0), r4),
        ("Fuel Flow Residual", latest.get("res_fuel_flow", 0.0), "L/h", latest.get("z_fuel_flow", 0.0), r5),
        ("Vib Residual", latest.get("res_vibration", 0.0), "mm/s", latest.get("z_vibration", 0.0), r6),
    ]

    for title, val, unit, z_score, col in residuals_data:
        with col:
            abs_z = abs(z_score)
            z_col = "#00e5a3" if abs_z < 1.8 else ("#f59e0b" if abs_z < 3.0 else "#ef4444")
            st.markdown(f"""
            <div class="metric-card" style="border-color:{z_col}66;">
                <div class="label">{title}</div>
                <div class="value" style="color:{z_col}; font-size:1.3rem;">{val:+.1f} {unit}</div>
                <div class="delta" style="color:{z_col}; font-size:0.75rem;">z = {z_score:+.2f}σ</div>
            </div>
            """, unsafe_allow_html=True)

    if not history or len(history) < 2:
        return

    df = pd.DataFrame(history)
    df["relative_time_s"] = df["timestamp"] - df["timestamp"].iloc[0]

    # Overlay Charts: Actual vs Twin
    st.markdown("#### Physical Sensor vs Digital Twin Expected Overlays")
    g1, g2 = st.columns(2)

    with g1:
        # EGT Comparison
        fig_egt = go.Figure()
        fig_egt.add_trace(go.Scatter(
            x=df["relative_time_s"], y=df["egt_c"],
            name="Actual Sensor EGT", mode="lines",
            line=dict(color="#ef4444", width=2.5)
        ))
        fig_egt.add_trace(go.Scatter(
            x=df["relative_time_s"], y=df["twin_egt_c"],
            name="Digital Twin Expected EGT", mode="lines",
            line=dict(color="#38bdf8", width=2.0, dash="dash")
        ))
        fig_egt.update_layout(
            **PLOTLY_DARK_THEME["layout"],
            title="Exhaust Gas Temp (EGT): Actual vs Virtual Twin",
            xaxis_title="Elapsed Time (s)",
            yaxis_title="°C",
            height=280
        )
        st.plotly_chart(fig_egt, use_container_width=True)

        # Oil Pressure Comparison
        fig_op = go.Figure()
        fig_op.add_trace(go.Scatter(
            x=df["relative_time_s"], y=df["oil_pressure_bar"],
            name="Actual Oil Pressure", mode="lines",
            line=dict(color="#00e5a3", width=2.5)
        ))
        fig_op.add_trace(go.Scatter(
            x=df["relative_time_s"], y=df["twin_oil_pressure_bar"],
            name="Digital Twin Expected Oil P", mode="lines",
            line=dict(color="#f59e0b", width=2.0, dash="dash")
        ))
        fig_op.update_layout(
            **PLOTLY_DARK_THEME["layout"],
            title="Oil Pressure: Actual vs Virtual Twin",
            xaxis_title="Elapsed Time (s)",
            yaxis_title="bar",
            height=280
        )
        st.plotly_chart(fig_op, use_container_width=True)

    with g2:
        # CHT Comparison
        fig_cht = go.Figure()
        fig_cht.add_trace(go.Scatter(
            x=df["relative_time_s"], y=df["cht_c"],
            name="Actual Sensor CHT", mode="lines",
            line=dict(color="#f59e0b", width=2.5)
        ))
        fig_cht.add_trace(go.Scatter(
            x=df["relative_time_s"], y=df["twin_cht_c"],
            name="Digital Twin Expected CHT", mode="lines",
            line=dict(color="#38bdf8", width=2.0, dash="dash")
        ))
        fig_cht.update_layout(
            **PLOTLY_DARK_THEME["layout"],
            title="Cylinder Head Temp (CHT): Actual vs Virtual Twin",
            xaxis_title="Elapsed Time (s)",
            yaxis_title="°C",
            height=280
        )
        st.plotly_chart(fig_cht, use_container_width=True)

        # Fuel Flow Comparison
        fig_ff = go.Figure()
        fig_ff.add_trace(go.Scatter(
            x=df["relative_time_s"], y=df["fuel_flow_lph"],
            name="Actual Fuel Flow", mode="lines",
            line=dict(color="#06b6d4", width=2.5)
        ))
        fig_ff.add_trace(go.Scatter(
            x=df["relative_time_s"], y=df["twin_fuel_flow_lph"],
            name="Digital Twin Expected Fuel Flow", mode="lines",
            line=dict(color="#a855f7", width=2.0, dash="dash")
        ))
        fig_ff.update_layout(
            **PLOTLY_DARK_THEME["layout"],
            title="Fuel Consumption: Actual vs Virtual Twin",
            xaxis_title="Elapsed Time (s)",
            yaxis_title="L/h",
            height=280
        )
        st.plotly_chart(fig_ff, use_container_width=True)
