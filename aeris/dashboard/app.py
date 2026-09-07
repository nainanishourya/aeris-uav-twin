"""AERIS Ground Control Station (GCS) - Main Streamlit Entry Point.

Smart India Hackathon 2026 - Problem Statement SIH26054 (DRDO)
Physics-Anchored Digital Twin & AI Intelligence System for MALE UAV Aero-Piston Engines.
"""

import sys
import time
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Streamlit page config (must be first Streamlit call)
st.set_page_config(
    page_title="AERIS Ground Control Station | DRDO SIH26054",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

from aeris.dashboard.styles import AERIS_CUSTOM_CSS
from aeris.telemetry.simulator import simulator
from aeris.telemetry.database import AerisDatabase
from aeris.ml.data_generator import FAULT_CLASSES

# View renderers
from aeris.dashboard.views.overview import render_overview
from aeris.dashboard.views.telemetry_view import render_telemetry_view
from aeris.dashboard.views.digital_twin_view import render_digital_twin_view
from aeris.dashboard.views.diagnostics_view import render_diagnostics_view
from aeris.dashboard.views.health_rul_view import render_health_rul_view
from aeris.dashboard.views.mission_view import render_mission_view
from aeris.dashboard.views.replay_view import render_replay_view
from aeris.dashboard.views.maintenance_view import render_maintenance_view
from aeris.dashboard.views.system_info import render_system_info

# Apply tactical dark CSS
st.markdown(AERIS_CUSTOM_CSS, unsafe_allow_html=True)

# Database instance
db = AerisDatabase()

# Sidebar: Tactical Navigation & Simulation Controls
with st.sidebar:
    st.markdown("""
    <div style="text-align:center; padding: 10px 0 16px 0; border-bottom: 1px solid #1e293b;">
        <div style="font-size: 1.4rem; font-weight: 900; letter-spacing: 2px; color:#00e5a3;">A E R I S</div>
        <div style="font-size: 0.72rem; color:#94a3b8; letter-spacing: 1px;">AI ENGINE RELIABILITY & INTELLIGENCE</div>
        <div style="font-size: 0.65rem; color:#64748b; margin-top:2px;">DRDO SIH26054 PROTOTYPE</div>
    </div>
    """, unsafe_allow_html=True)

    # 1-CLICK DEMO BUTTON
    st.markdown("<div style='margin-top:14px;'></div>", unsafe_allow_html=True)
    st.markdown("<div class='demo-btn-highlight'>", unsafe_allow_html=True)
    if st.button("🚀 START DEMO SCENARIO", use_container_width=True):
        simulator.start_demo_scenario()
        st.toast("Started 1-Click Injector Degradation Demo Scenario!", icon="🚀")
    st.markdown("</div>", unsafe_allow_html=True)
    
    if simulator.demo_active:
        st.info(f"Demo Step: {simulator.demo_step}/{simulator.demo_total_steps} (Fault: {simulator.current_fault}, Sev: {simulator.fault_severity:.2f})")

    st.markdown("---")
    
    # Section Navigation
    st.markdown("<div style='font-size:0.75rem; color:#64748b; font-weight:700; text-transform:uppercase;'>Navigation</div>", unsafe_allow_html=True)
    page = st.radio(
        "Select Sub-System View",
        [
            "1. Tactical Overview",
            "2. Live Telemetry",
            "3. Digital Twin Comparison",
            "4. AI Diagnostics & XAI",
            "5. Predictive Health & RUL",
            "6. Mission Profile Simulator",
            "7. Historical Mission Replay",
            "8. Predictive Maintenance",
            "9. System Architecture & ML Info"
        ],
        label_visibility="collapsed"
    )

    st.markdown("---")

    # Real-Time Telemetry Controls
    st.markdown("<div style='font-size:0.75rem; color:#64748b; font-weight:700; text-transform:uppercase;'>Telemetry Simulator Stream</div>", unsafe_allow_html=True)
    
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        if st.button("▶ Step Once", use_container_width=True):
            simulator.step()
    with col_s2:
        auto_refresh = st.checkbox("Auto-Stream (1s)", value=False)

    with st.expander("⚙️ Dynamic Flight Controls", expanded=False):
        thr = st.slider("Throttle Demand", 0.3, 1.0, float(simulator.throttle), 0.05)
        alt = st.slider("Altitude (m)", 100.0, 7000.0, float(simulator.altitude_m), 100.0)
        temp = st.slider("Ambient Temp (°C)", -30.0, 50.0, float(simulator.ambient_temp_c), 1.0)
        simulator.set_operating_point(throttle=thr, altitude_m=alt, ambient_temp_c=temp)

    with st.expander("⚠️ Manual Fault Injection", expanded=False):
        fault_choice = st.selectbox("Inject Fault Mode", FAULT_CLASSES, index=FAULT_CLASSES.index(simulator.current_fault) if simulator.current_fault in FAULT_CLASSES else 0)
        sev_choice = st.slider("Fault Severity", 0.0, 2.0, float(simulator.fault_severity), 0.1)
        if st.button("Apply Fault Setting", use_container_width=True):
            simulator.set_operating_point(fault=fault_choice, severity=sev_choice)
            st.toast(f"Injected: {fault_choice} (Sev: {sev_choice:.1f})")

    st.markdown("---")
    st.caption("AERIS v1.0.0 | Offline-Ready | Open-Source")

# Ensure at least 1 step exists in DB
latest_data = db.get_latest_telemetry()
if not latest_data:
    simulator.step()
    latest_data = db.get_latest_telemetry()

history_data = db.get_telemetry_history(limit=50)

# Dispatch to view
if "1. Tactical Overview" in page:
    render_overview(latest_data, simulator)
elif "2. Live Telemetry" in page:
    render_telemetry_view(history_data)
elif "3. Digital Twin Comparison" in page:
    render_digital_twin_view(latest_data, history_data)
elif "4. AI Diagnostics & XAI" in page:
    render_diagnostics_view(latest_data, simulator)
elif "5. Predictive Health & RUL" in page:
    render_health_rul_view(latest_data, simulator)
elif "6. Mission Profile Simulator" in page:
    render_mission_view()
elif "7. Historical Mission Replay" in page:
    render_replay_view()
elif "8. Predictive Maintenance" in page:
    render_maintenance_view(db, latest_data)
elif "9. System Architecture" in page:
    render_system_info()

# Auto-stream loop
if auto_refresh:
    time.sleep(1.0)
    simulator.step()
    st.rerun()
