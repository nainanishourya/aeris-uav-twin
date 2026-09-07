"""Ground Control Station: Historical Mission Telemetry Replay."""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from typing import Dict, Any, Optional

from aeris.dashboard.styles import PLOTLY_DARK_THEME
from aeris.ml.data_generator import SyntheticTelemetryGenerator

def render_replay_view():
    """Renders historical telemetry playback, timeline scrubber, and event markers."""
    st.markdown("### ⏪ Historical Mission Telemetry Replay")
    st.caption("Post-flight investigation player with synchronized physics residuals, anomaly flags, and fault markers.")

    # Flight selection / CSV upload
    c_source1, c_source2 = st.columns([1.5, 1.5])
    
    with c_source1:
        flight_preset = st.selectbox(
            "Select Historical Mission Flight Log",
            [
                "Flight-2026-0814 (Injector Abnormality Event)",
                "Flight-2026-0821 (Misfire Event at High Altitude)",
                "Flight-2026-0902 (Lubrication Distress Event)",
                "Flight-2026-0905 (Nominal 8h ISR Mission)"
            ]
        )

    with c_source2:
        uploaded_file = st.file_uploader("Or Upload Custom Mission CSV", type=["csv"])

    # Load dataset
    if "replay_data" not in st.session_state or st.session_state.get("current_preset") != flight_preset:
        gen = SyntheticTelemetryGenerator(seed=101)
        if "Injector" in flight_preset:
            df = gen.generate_flight_profile(duration_seconds=900, fault_type="Injector Abnormality", fault_onset_ratio=0.45)
        elif "Misfire" in flight_preset:
            df = gen.generate_flight_profile(duration_seconds=900, fault_type="Misfire", fault_onset_ratio=0.50, altitude_profile="high_altitude")
        elif "Lubrication" in flight_preset:
            df = gen.generate_flight_profile(duration_seconds=900, fault_type="Lubrication Problem", fault_onset_ratio=0.40)
        else:
            df = gen.generate_flight_profile(duration_seconds=900, fault_type="Healthy")

        # Compute synthetic health index for replay
        df["health_index"] = 96.0 - (df["degradation_severity"] * 45.0) - (df["is_anomaly"] * 12.0)
        df["health_index"] = df["health_index"].clip(25.0, 100.0)
        
        st.session_state.replay_data = df
        st.session_state.current_preset = flight_preset

    if uploaded_file is not None:
        try:
            custom_df = pd.read_csv(uploaded_file)
            st.session_state.replay_data = custom_df
            st.success(f"Loaded custom replay file: {uploaded_file.name} ({len(custom_df)} records)")
        except Exception as e:
            st.error(f"Error parsing uploaded file: {e}")

    df = st.session_state.replay_data
    total_steps = len(df)

    # Timeline Scrubber Controls
    st.markdown("#### Mission Timeline Scrubber")
    ctrl_col1, ctrl_col2, ctrl_col3 = st.columns([1, 4, 1])
    
    with ctrl_col1:
        play_btn = st.button("▶ Step +10s")
    with ctrl_col2:
        step_idx = st.slider("Scrub Mission Time (Seconds)", 0, total_steps - 1, 0, step=1)
    with ctrl_col3:
        jump_anomaly = st.button("⚡ Jump to Anomaly")

    if play_btn:
        step_idx = min(total_steps - 1, step_idx + 10)

    if jump_anomaly:
        anomaly_indices = df[df["is_anomaly"] == 1].index
        if len(anomaly_indices) > 0:
            step_idx = int(anomaly_indices[0])
            st.info(f"Jumped to first anomaly event at T = {df.iloc[step_idx]['timestamp_sec']:.0f}s")
        else:
            st.info("No anomaly events recorded in this flight log.")

    # Current Frame Synchronized Telemetry
    current_frame = df.iloc[step_idx]
    t_sec = current_frame.get("timestamp_sec", step_idx)
    curr_fault = current_frame.get("fault_label", "Healthy")
    is_anom = current_frame.get("is_anomaly", 0) == 1

    # Synchronized Frame Display
    st.markdown(f"""
    <div style="background:#162035; border:1px solid #233354; border-radius:8px; padding:12px 18px; margin-bottom:14px; display:flex; justify-content:space-between; align-items:center;">
        <div>
            <span style="color:#94a3b8; font-size:0.85rem;">REPLAY TIME:</span>
            <strong style="color:#f8fafc; font-size:1.2rem; margin-left:8px;">T+{t_sec:.0f}s ({t_sec/60:.1f} min)</strong>
        </div>
        <div>
            <span style="color:#94a3b8; font-size:0.85rem;">SYNCHRONIZED DIAGNOSIS:</span>
            <strong style="color:{'#ef4444' if is_anom else '#00e5a3'}; font-size:1.1rem; margin-left:8px;">{curr_fault.upper()}</strong>
        </div>
        <div>
            <span style="color:#94a3b8; font-size:0.85rem;">HEALTH INDEX:</span>
            <strong style="color:#38bdf8; font-size:1.2rem; margin-left:8px;">{current_frame.get('health_index', 95.0):.1f}</strong>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Replay KPI cards
    rk1, rk2, rk3, rk4, rk5, rk6 = st.columns(6)
    rk1.metric("RPM", f"{current_frame.get('rpm', 0):.0f}", f"Δ {current_frame.get('rpm', 0) - 5000:+.0f}")
    rk2.metric("CHT", f"{current_frame.get('cht_c', 0):.1f}°C", f"Δ {current_frame.get('res_cht', 0):+.1f}°C")
    rk3.metric("EGT", f"{current_frame.get('egt_c', 0):.0f}°C", f"Δ {current_frame.get('res_egt', 0):+.0f}°C")
    rk4.metric("Oil Pressure", f"{current_frame.get('oil_pressure_bar', 0):.2f}b", f"Δ {current_frame.get('res_oil_p', 0):+.2f}b")
    rk5.metric("Fuel Flow", f"{current_frame.get('fuel_flow_lph', 0):.1f} L", f"Δ {current_frame.get('res_fuel_flow', 0):+.1f} L")
    rk6.metric("Vibration", f"{current_frame.get('vibration_mms', 0):.2f}", f"Δ {current_frame.get('res_vibration', 0):+.2f}")

    # Synchronized Mission Plot with Anomaly Marker
    fig_replay = go.Figure()

    # Temperature trajectories
    fig_replay.add_trace(go.Scatter(
        x=df["timestamp_sec"], y=df["cht_c"],
        name="CHT (°C)", mode="lines",
        line=dict(color="#f59e0b", width=2)
    ))
    fig_replay.add_trace(go.Scatter(
        x=df["timestamp_sec"], y=df["egt_c"],
        name="EGT (°C)", mode="lines", yaxis="y2",
        line=dict(color="#ef4444", width=2)
    ))

    # Add vertical line for current scrubber position
    fig_replay.add_vline(
        x=t_sec, line_width=2, line_dash="solid", line_color="#38bdf8",
        annotation_text="Current Scrubber", annotation_position="top left"
    )

    # Anomaly Event markers
    anom_rows = df[df["is_anomaly"] == 1]
    if not anom_rows.empty:
        first_anom_time = anom_rows.iloc[0]["timestamp_sec"]
        fig_replay.add_vline(
            x=first_anom_time, line_width=2, line_dash="dash", line_color="#ef4444",
            annotation_text=f"Anomaly Onset ({curr_fault})", annotation_position="top right"
        )

    fig_replay.update_layout(
        **PLOTLY_DARK_THEME["layout"],
        title="Flight Mission Replay Profile & Anomaly Events",
        xaxis_title="Mission Seconds (s)",
        yaxis=dict(title="CHT (°C)"),
        yaxis2=dict(title="EGT (°C)", overlaying="y", side="right"),
        height=350
    )
    st.plotly_chart(fig_replay, use_container_width=True)
