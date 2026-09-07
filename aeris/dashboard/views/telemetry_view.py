"""Ground Control Station: Live Telemetry Channels and Strip Charts."""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from typing import List, Dict, Any

from aeris.dashboard.styles import PLOTLY_DARK_THEME, get_dark_layout

def render_telemetry_view(history: List[Dict[str, Any]]):
    """Renders real-time telemetry time-series strip charts."""
    st.markdown("### 📡 Live Multi-Channel Engine Telemetry")
    
    if not history or len(history) < 2:
        st.info("Awaiting sufficient telemetry frames for strip charting (minimum 2 samples required)...")
        return

    df = pd.DataFrame(history)
    df["relative_time_s"] = df["timestamp"] - df["timestamp"].iloc[0]

    # Row 1: RPM & Temperatures
    c1, c2 = st.columns(2)

    with c1:
        # RPM & Throttle Chart
        fig_rpm = go.Figure()
        fig_rpm.add_trace(go.Scatter(
            x=df["relative_time_s"], y=df["rpm"],
            name="RPM", mode="lines",
            line=dict(color="#38bdf8", width=2.5)
        ))
        fig_rpm.add_hline(y=5800, line_dash="dash", line_color="#ef4444", annotation_text="Max Takeoff (5800)")
        fig_rpm.add_hline(y=5500, line_dash="dot", line_color="#f59e0b", annotation_text="Max Continuous (5500)")
        fig_rpm.update_layout(
            **get_dark_layout(height=300),
            title="Engine Speed (RPM)",
            xaxis_title="Mission Elapsed Time (s)",
            yaxis_title="RPM"
        )
        st.plotly_chart(fig_rpm, width='stretch')

    with c2:
        # Thermal: CHT & EGT
        fig_temp = go.Figure()
        fig_temp.add_trace(go.Scatter(
            x=df["relative_time_s"], y=df["cht_c"],
            name="CHT (°C)", mode="lines",
            line=dict(color="#f59e0b", width=2.5)
        ))
        fig_temp.add_trace(go.Scatter(
            x=df["relative_time_s"], y=df["egt_c"],
            name="EGT (°C)", mode="lines", yaxis="y2",
            line=dict(color="#ef4444", width=2.0)
        ))
        fig_temp.update_layout(
            **dict(get_dark_layout(height=300), yaxis=dict(title=dict(text="CHT (°C)", font=dict(color="#f59e0b")), tickfont=dict(color="#f59e0b"))),
            title="Thermal Dynamics: CHT & EGT",
            xaxis_title="Mission Elapsed Time (s)",
            yaxis2=dict(title=dict(text="EGT (°C)", font=dict(color="#ef4444")), tickfont=dict(color="#ef4444"), overlaying="y", side="right")
        )
        st.plotly_chart(fig_temp, width='stretch')

    # Row 2: Lubrication & Dynamics
    c3, c4 = st.columns(2)

    with c3:
        # Oil Pressure & Oil Temp
        fig_oil = go.Figure()
        fig_oil.add_trace(go.Scatter(
            x=df["relative_time_s"], y=df["oil_pressure_bar"],
            name="Oil Pressure (bar)", mode="lines",
            line=dict(color="#00e5a3", width=2.5)
        ))
        fig_oil.add_trace(go.Scatter(
            x=df["relative_time_s"], y=df["oil_temp_c"],
            name="Oil Temp (°C)", mode="lines", yaxis="y2",
            line=dict(color="#f97316", width=2.0)
        ))
        fig_oil.add_hline(y=2.0, line_dash="dash", line_color="#ef4444", annotation_text="Min Oil P (2.0 bar)")
        fig_oil.update_layout(
            **dict(get_dark_layout(height=300), yaxis=dict(title=dict(text="Oil Pressure (bar)", font=dict(color="#00e5a3")), tickfont=dict(color="#00e5a3"))),
            title="Lubrication Hydrodynamics: Oil P & Oil Temp",
            xaxis_title="Mission Elapsed Time (s)",
            yaxis2=dict(title=dict(text="Oil Temp (°C)", font=dict(color="#f97316")), tickfont=dict(color="#f97316"), overlaying="y", side="right")
        )
        st.plotly_chart(fig_oil, width='stretch')

    with c4:
        # Vibration & Fuel Flow
        fig_vf = go.Figure()
        fig_vf.add_trace(go.Scatter(
            x=df["relative_time_s"], y=df["vibration_mms"],
            name="Vibration (mm/s)", mode="lines",
            line=dict(color="#a855f7", width=2.5)
        ))
        fig_vf.add_trace(go.Scatter(
            x=df["relative_time_s"], y=df["fuel_flow_lph"],
            name="Fuel Flow (L/h)", mode="lines", yaxis="y2",
            line=dict(color="#06b6d4", width=2.0)
        ))
        fig_vf.add_hline(y=4.5, line_dash="dash", line_color="#ef4444", annotation_text="Caution Vib (4.5 mm/s)")
        fig_vf.update_layout(
            **dict(get_dark_layout(height=300), yaxis=dict(title=dict(text="Vibration (mm/s RMS)", font=dict(color="#a855f7")), tickfont=dict(color="#a855f7"))),
            title="Vibration Velocity & Fuel Consumption",
            xaxis_title="Mission Elapsed Time (s)",
            yaxis2=dict(
                title=dict(text="Fuel Flow (L/h)", font=dict(color="#06b6d4")),
                tickfont=dict(color="#06b6d4"), overlaying="y", side="right"
            )
        )
        st.plotly_chart(fig_vf, width='stretch')

    # Detailed Raw Sensor Table Expander
    with st.expander("🔍 Inspect Full Raw Telemetry Records (Latest 20 Samples)", expanded=False):
        display_cols = [
            "timestamp", "rpm", "throttle", "altitude_m", "ambient_temp_c",
            "cht_c", "egt_c", "oil_pressure_bar", "oil_temp_c", "fuel_flow_lph",
            "vibration_mms", "battery_v", "health_index", "predicted_fault"
        ]
        available_cols = [c for c in display_cols if c in df.columns]
        st.dataframe(df[available_cols].tail(20), use_container_width=True)
