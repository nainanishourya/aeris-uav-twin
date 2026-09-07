"""Ground Control Station: Mission Profile Simulator & Multi-Mission Trade-off Comparison."""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from typing import Dict, Any

from aeris.dashboard.styles import PLOTLY_DARK_THEME
from aeris.mission.simulator import MissionSimulator, MissionProfile, MISSION_PRESETS
from aeris.mission.comparison import MissionComparisonEngine

def render_mission_view():
    """Renders Mission Simulator and Multi-Mission Comparison tool."""
    st.markdown("### 🗺️ Mission Profile Simulator & Risk Evaluation")
    st.caption("Forward-time digital twin projection evaluating propulsion degradation and mission feasibility.")

    tab_single, tab_compare = st.tabs(["🎯 Single Mission Simulation", "⚖️ Multi-Mission Comparison"])

    simulator = MissionSimulator()

    with tab_single:
        c1, c2 = st.columns([1.0, 2.0])

        with c1:
            st.markdown("#### Mission Configuration")
            preset_choice = st.selectbox("Select Mission Preset", list(MISSION_PRESETS.keys()) + ["Custom Profile"])
            
            if preset_choice != "Custom Profile":
                base_preset = MISSION_PRESETS[preset_choice]
                def_dur = base_preset.duration_hours
                def_alt = base_preset.cruise_altitude_m
                def_temp = base_preset.ambient_temp_c
                def_thr = base_preset.cruise_throttle
                def_trans = base_preset.throttle_transients
            else:
                def_dur = 8.0
                def_alt = 3000.0
                def_temp = 20.0
                def_thr = 0.72
                def_trans = False

            duration = st.slider("Mission Duration (Hours)", 1.0, 24.0, float(def_dur), 0.5)
            altitude = st.slider("Cruise Altitude (meters)", 500.0, 7500.0, float(def_alt), 100.0)
            ambient_temp = st.slider("Ambient Temperature (°C)", -35.0, 50.0, float(def_temp), 1.0)
            throttle = st.slider("Cruise Throttle Demand", 0.40, 1.00, float(def_thr), 0.02)
            transients = st.checkbox("Simulate Cyclic Throttle Transients", value=def_trans)
            init_health = st.slider("Engine Initial Health Index", 50.0, 100.0, 95.0, 1.0)

            run_btn = st.button("🚀 Run Forward Mission Simulation", use_container_width=True)

        with c2:
            profile = MissionProfile(
                name=preset_choice,
                description="Selected mission simulation profile",
                duration_hours=duration,
                cruise_altitude_m=altitude,
                ambient_temp_c=ambient_temp,
                cruise_throttle=throttle,
                throttle_transients=transients,
                initial_health_index=init_health
            )
            sim_res = simulator.run_simulation(profile)

            # Mission Risk Badge
            risk_color = sim_res.risk_color
            st.markdown(f"""
            <div style="background:{risk_color}18; border:2px solid {risk_color}; border-radius:8px; padding:16px; margin-bottom:16px;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div>
                        <div style="font-size:0.8rem; color:#94a3b8; text-transform:uppercase;">Mission Propulsion Risk Assessment</div>
                        <div style="font-size:1.8rem; font-weight:900; color:{risk_color}; letter-spacing:1px;">
                            {sim_res.mission_risk_score} RISK
                        </div>
                    </div>
                    <div style="text-align:right;">
                        <div style="font-size:0.8rem; color:#94a3b8;">Health Impact</div>
                        <div style="font-size:1.4rem; font-weight:800; color:#cbd5e1;">-{sim_res.health_delta:.1f} pts</div>
                    </div>
                </div>
                <div style="margin-top:10px; font-size:0.88rem; color:#f1f5f9; line-height:1.4;">
                    <strong>Why this risk exists:</strong> {sim_res.risk_explanation}
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Key Mission Metrics
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Est. Fuel Consumed", f"{sim_res.fuel_consumed_liters:.1f} L", f"{sim_res.fuel_consumed_liters/duration:.1f} L/h")
            m2.metric("Peak CHT", f"{sim_res.max_cht_c:.1f} °C", "Limit: 135°C")
            m3.metric("Peak Oil Temp", f"{sim_res.max_oil_temp_c:.1f} °C", "Limit: 120°C")
            m4.metric("RUL Accelerated Wear", f"-{sim_res.rul_impact_hours:.1f} hrs", "Wear Penalty")

            # Trajectory Chart
            traj_df = pd.DataFrame(sim_res.trajectory)
            fig_sim = go.Figure()
            fig_sim.add_trace(go.Scatter(
                x=traj_df["mission_hour"], y=traj_df["projected_health"],
                name="Projected Health Index", mode="lines+markers",
                line=dict(color="#00e5a3", width=2.5)
            ))
            fig_sim.add_trace(go.Scatter(
                x=traj_df["mission_hour"], y=traj_df["predicted_cht"],
                name="Predicted CHT (°C)", mode="lines", yaxis="y2",
                line=dict(color="#f59e0b", width=2.0)
            ))
            fig_sim.update_layout(
                **PLOTLY_DARK_THEME["layout"],
                title="Mission Forward Trajectory: Health Degradation & Thermal Profile",
                xaxis_title="Mission Flight Hours",
                yaxis=dict(title="Health Index (0-100)", range=[30, 105]),
                yaxis2=dict(title="CHT (°C)", overlaying="y", side="right", range=[60, 160]),
                height=320
            )
            st.plotly_chart(fig_sim, use_container_width=True)

    with tab_compare:
        st.markdown("#### Multi-Mission Candidate Trade-off Comparison")
        st.caption("Compare mission feasibility and propulsion degradation across candidate operational profiles.")

        comp_engine = MissionComparisonEngine()
        candidate_profiles = [
            MISSION_PRESETS["Normal ISR"],
            MISSION_PRESETS["High Altitude"],
            MISSION_PRESETS["Hot Weather"],
            MISSION_PRESETS["Rapid Throttle Transition"]
        ]

        comp_analysis = comp_engine.compare_profiles(candidate_profiles, baseline_health=95.0)

        # Comparative Insight Box
        st.markdown(f"""
        <div style="background:#162035; border:1px solid #38bdf8; border-radius:8px; padding:14px; margin-bottom:18px;">
            <strong style="color:#38bdf8; font-size:0.95rem;">💡 Comparative Mission Intelligence:</strong>
            <p style="margin:6px 0 0 0; font-size:0.88rem; color:#e2e8f0;">
                {comp_analysis['comparative_insight']}
            </p>
        </div>
        """, unsafe_allow_html=True)

        # Comparison Table
        comp_df = pd.DataFrame(comp_analysis["comparison_table"])
        st.dataframe(comp_df, use_container_width=True)

        # Multi-mission Health Trajectory Comparison Chart
        fig_multi = go.Figure()
        colors = ["#00e5a3", "#38bdf8", "#f59e0b", "#ef4444"]

        for idx, res in enumerate(comp_analysis["results"]):
            t_df = pd.DataFrame(res.trajectory)
            fig_multi.add_trace(go.Scatter(
                x=t_df["mission_hour"], y=t_df["projected_health"],
                name=f"{res.profile_name} ({res.mission_risk_score} Risk)",
                mode="lines",
                line=dict(color=colors[idx % len(colors)], width=2.5)
            ))

        fig_multi.update_layout(
            **PLOTLY_DARK_THEME["layout"],
            title="Comparative Engine Health Trajectories Across Profiles",
            xaxis_title="Mission Flight Hours",
            yaxis_title="Projected Health Index",
            height=340
        )
        st.plotly_chart(fig_multi, use_container_width=True)
