"""Ground Control Station: Overview & Tactical Health HUD."""

import streamlit as st
import plotly.graph_objects as go
from typing import Dict, Any

from aeris.dashboard.styles import PLOTLY_DARK_THEME, get_dark_layout

def render_overview(latest: Dict[str, Any], sim):
    """Renders main Ground Control Station Overview."""
    if not latest:
        st.warning("No telemetry stream received yet. Initializing system...")
        return

    # Extract metrics
    health = latest.get("health_index", 100.0)
    health_status = latest.get("health_status", "Healthy")
    fault = latest.get("predicted_fault", "Healthy")
    conf = latest.get("confidence", 1.0)
    anom_score = latest.get("anomaly_score", 0.0)
    rul = latest.get("estimated_rul_hours", 1000.0)
    uav_id = latest.get("uav_id", "UAV-MALE-01")

    # Color definitions
    color_map = {
        "Healthy": "#00e5a3",
        "Normal/Watch": "#38bdf8",
        "Degraded": "#f59e0b",
        "Critical": "#f97316",
        "Severe": "#ef4444"
    }
    status_color = color_map.get(health_status, "#00e5a3")

    # Top Status Bar
    st.markdown(f"""
    <div class="aeris-header">
        <div>
            <div class="aeris-title">
                <span>🛡️ AERIS TACTICAL GCS</span>
                <span class="aeris-tag">{uav_id}</span>
                <span class="aeris-tag" style="background:#1e293b; color:#94a3b8; border-color:#334155;">DRDO SIH26054</span>
            </div>
            <div style="color:#94a3b8; font-size:0.85rem; margin-top:4px;">
                MALE UAV Aero-Piston Propulsion Reliability & Digital Twin Intelligence Unit
            </div>
        </div>
        <div style="text-align:right;">
            <div style="font-size:0.8rem; color:#94a3b8; text-transform:uppercase; letter-spacing:1px;">Fleet Status</div>
            <div style="display:inline-block; background:{status_color}22; color:{status_color}; border:1px solid {status_color}; padding:4px 14px; border-radius:20px; font-weight:800; font-size:0.95rem;">
                ● {health_status.upper()}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Active Diagnostic Banner
    if fault != "Healthy" and conf > 0.60:
        st.markdown(f"""
        <div style="background: rgba(239, 68, 68, 0.15); border: 1px solid #ef4444; border-radius: 8px; padding: 12px 18px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center;">
            <div>
                <strong style="color: #ef4444; font-size: 1.05rem;">⚠️ ACTIVE FAULT DETECTED: {fault.upper()}</strong>
                <span style="color: #f8fafc; margin-left: 12px; font-size: 0.9rem;">Confidence: {conf * 100:.1f}%</span>
                <div style="color: #cbd5e1; font-size: 0.85rem; margin-top: 4px;">
                    {latest.get('maintenance_action', 'Inspect engine telemetry.')}
                </div>
            </div>
            <div style="background: #ef4444; color: white; padding: 4px 12px; border-radius: 4px; font-weight: 700; font-size: 0.8rem;">
                ACTION REQUIRED
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Row 1: Engine Health Index Gauge & Core Sub-Indices
    c1, c2 = st.columns([1.1, 1.9])

    with c1:
        # Gauge chart for Engine Health Index
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number",
            value=health,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': "ENGINE HEALTH INDEX (0-100)", 'font': {'size': 14, 'color': '#94a3b8'}},
            number={'suffix': "", 'font': {'size': 44, 'color': status_color, 'family': 'Courier New'}},
            gauge={
                'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "#334155"},
                'bar': {'color': status_color, 'thickness': 0.28},
                'bgcolor': "#162035",
                'borderwidth': 1,
                'bordercolor': "#1e293b",
                'steps': [
                    {'range': [0, 30], 'color': 'rgba(239, 68, 68, 0.25)'},
                    {'range': [30, 50], 'color': 'rgba(249, 115, 22, 0.2)'},
                    {'range': [50, 70], 'color': 'rgba(245, 158, 11, 0.2)'},
                    {'range': [70, 90], 'color': 'rgba(56, 189, 248, 0.2)'},
                    {'range': [90, 100], 'color': 'rgba(0, 229, 163, 0.2)'}
                ],
                'threshold': {
                    'line': {'color': "#ffffff", 'width': 3},
                    'thickness': 0.8,
                    'value': health
                }
            }
        ))
        fig_gauge.update_layout(
            **get_dark_layout(
                height=240,
                margin={"l": 25, "r": 25, "t": 40, "b": 20}
            )
        )
        st.plotly_chart(fig_gauge, use_container_width=True)

    with c2:
        st.markdown("<div style='font-size:0.85rem; color:#94a3b8; font-weight:700; margin-bottom:10px; letter-spacing:1px;'>SUB-SYSTEM HEALTH BREAKDOWN & AI PENALTIES</div>", unsafe_allow_html=True)
        
        # Sub-health progress bars
        sub1, sub2 = st.columns(2)
        with sub1:
            st.caption(f"Thermal Sub-Index: {latest.get('thermal_health', 100.0):.1f}%")
            st.progress(min(1.0, max(0.0, latest.get('thermal_health', 100.0) / 100.0)))

            st.caption(f"Lubrication Sub-Index: {latest.get('lubrication_health', 100.0):.1f}%")
            st.progress(min(1.0, max(0.0, latest.get('lubrication_health', 100.0) / 100.0)))

        with sub2:
            st.caption(f"Vibration & Mechanical: {latest.get('vibration_health', 100.0):.1f}%")
            st.progress(min(1.0, max(0.0, latest.get('vibration_health', 100.0) / 100.0)))

            st.caption(f"Combustion & Fuel Efficiency: {latest.get('efficiency_health', 100.0):.1f}%")
            st.progress(min(1.0, max(0.0, latest.get('efficiency_health', 100.0) / 100.0)))

        st.markdown(f"""
        <div style="background:#121929; border:1px solid #1e293b; border-radius:6px; padding:10px 14px; margin-top:12px; display:flex; justify-content:space-between; font-size:0.85rem;">
            <span>Anomaly Penalty: <strong style="color:#f59e0b;">{(anom_score * 30.0):.1f} pts</strong> (Score: {anom_score:.2f})</span>
            <span>Est. Remaining Useful Life: <strong style="color:#00e5a3;">{rul:.0f} hrs</strong></span>
            <span>Operating Hours: <strong style="color:#38bdf8;">{sim.flight_hours:.1f} hrs</strong></span>
        </div>
        """, unsafe_allow_html=True)

    # Row 2: Live Primary Telemetry Cards
    st.markdown("<div style='font-size:0.85rem; color:#94a3b8; font-weight:700; margin:16px 0 8px 0; letter-spacing:1px;'>REAL-TIME ENGINE TELEMETRY CHANNELS</div>", unsafe_allow_html=True)
    
    k1, k2, k3, k4, k5, k6, k7, k8 = st.columns(8)
    
    with k1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="label">Engine RPM</div>
            <div class="value">{latest.get('rpm', 0):.0f}</div>
            <div class="delta" style="color:#94a3b8;">Load: {latest.get('engine_load', 0)*100:.0f}%</div>
        </div>
        """, unsafe_allow_html=True)

    with k2:
        cht = latest.get('cht_c', 0)
        res_cht = latest.get('res_cht', 0)
        c_color = "#ef4444" if cht > 130 else ("#f59e0b" if cht > 120 else "#00e5a3")
        st.markdown(f"""
        <div class="metric-card">
            <div class="label">CHT</div>
            <div class="value" style="color:{c_color};">{cht:.1f}°C</div>
            <div class="delta" style="color:#94a3b8;">Δ {res_cht:+.1f}°C</div>
        </div>
        """, unsafe_allow_html=True)

    with k3:
        egt = latest.get('egt_c', 0)
        res_egt = latest.get('res_egt', 0)
        e_color = "#ef4444" if egt > 820 else ("#f59e0b" if egt > 780 else "#00e5a3")
        st.markdown(f"""
        <div class="metric-card">
            <div class="label">EGT</div>
            <div class="value" style="color:{e_color};">{egt:.0f}°C</div>
            <div class="delta" style="color:#94a3b8;">Δ {res_egt:+.0f}°C</div>
        </div>
        """, unsafe_allow_html=True)

    with k4:
        oil_p = latest.get('oil_pressure_bar', 0)
        res_oil_p = latest.get('res_oil_p', 0)
        op_color = "#ef4444" if oil_p < 2.0 else ("#f59e0b" if oil_p < 2.8 else "#00e5a3")
        st.markdown(f"""
        <div class="metric-card">
            <div class="label">Oil Pressure</div>
            <div class="value" style="color:{op_color};">{oil_p:.2f}b</div>
            <div class="delta" style="color:#94a3b8;">Δ {res_oil_p:+.2f}b</div>
        </div>
        """, unsafe_allow_html=True)

    with k5:
        oil_t = latest.get('oil_temp_c', 0)
        res_oil_t = latest.get('res_oil_t', 0)
        ot_color = "#ef4444" if oil_t > 115 else ("#f59e0b" if oil_t > 105 else "#00e5a3")
        st.markdown(f"""
        <div class="metric-card">
            <div class="label">Oil Temp</div>
            <div class="value" style="color:{ot_color};">{oil_t:.1f}°C</div>
            <div class="delta" style="color:#94a3b8;">Δ {res_oil_t:+.1f}°C</div>
        </div>
        """, unsafe_allow_html=True)

    with k6:
        ff = latest.get('fuel_flow_lph', 0)
        res_ff = latest.get('res_fuel_flow', 0)
        st.markdown(f"""
        <div class="metric-card">
            <div class="label">Fuel Flow</div>
            <div class="value">{ff:.1f} L</div>
            <div class="delta" style="color:#94a3b8;">Δ {res_ff:+.1f} L</div>
        </div>
        """, unsafe_allow_html=True)

    with k7:
        vib = latest.get('vibration_mms', 0)
        res_vib = latest.get('res_vibration', 0)
        v_color = "#ef4444" if vib > 4.5 else ("#f59e0b" if vib > 3.0 else "#00e5a3")
        st.markdown(f"""
        <div class="metric-card">
            <div class="label">Vibration</div>
            <div class="value" style="color:{v_color};">{vib:.2f}</div>
            <div class="delta" style="color:#94a3b8;">Δ {res_vib:+.2f}</div>
        </div>
        """, unsafe_allow_html=True)

    with k8:
        alt = latest.get('altitude_m', 0)
        st.markdown(f"""
        <div class="metric-card">
            <div class="label">Altitude</div>
            <div class="value">{alt:.0f}m</div>
            <div class="delta" style="color:#94a3b8;">{(alt * 3.28084):.0f} ft</div>
        </div>
        """, unsafe_allow_html=True)
