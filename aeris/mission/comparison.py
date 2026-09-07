"""Multi-Mission Profile Comparison Engine for AERIS."""

from typing import List, Dict, Any
import pandas as pd
from aeris.mission.simulator import MissionSimulator, MissionProfile, MissionSimulationResult, MISSION_PRESETS

class MissionComparisonEngine:
    """Compares multiple operational mission profiles to guide mission commanders on engine risk."""

    def __init__(self):
        self.simulator = MissionSimulator()

    def compare_profiles(
        self,
        profiles: List[MissionProfile],
        baseline_health: float = 95.0
    ) -> Dict[str, Any]:
        """Runs simulations across candidate profiles and produces comparative analysis."""
        results: List[MissionSimulationResult] = []
        for p in profiles:
            p.initial_health_index = baseline_health
            res = self.simulator.run_simulation(p)
            results.append(res)

        # Summary comparison table rows
        comparison_rows = []
        for r in results:
            comparison_rows.append({
                "Mission Profile": r.profile_name,
                "Duration (hrs)": r.duration_hours,
                "Risk Tier": r.mission_risk_score,
                "Initial Health": r.initial_health,
                "Projected Health": r.final_health,
                "Health Impact (Δ)": f"-{r.health_delta:.1f}",
                "Accelerated RUL Penalty": f"-{r.rul_impact_hours:.1f} hrs",
                "Est. Fuel Used": f"{r.fuel_consumed_liters:.1f} L",
                "Peak CHT": f"{r.max_cht_c:.1f} °C",
                "Peak Oil Temp": f"{r.max_oil_temp_c:.1f} °C"
            })

        # Generate comparative insight explanation
        # Sort results from lowest health impact to highest
        sorted_res = sorted(results, key=lambda x: x.health_delta)
        best = sorted_res[0]
        worst = sorted_res[-1]

        delta_diff = worst.health_delta - best.health_delta
        comparative_insight = (
            f"'{best.profile_name}' produces the lowest engine degradation (-{best.health_delta:.1f} health points), "
            f"whereas '{worst.profile_name}' inflicts the highest cumulative wear (-{worst.health_delta:.1f} health points, "
            f"an increase of {delta_diff:.1f} points). Key contributing driver: {worst.risk_explanation}"
        )

        return {
            "comparison_table": comparison_rows,
            "results": results,
            "comparative_insight": comparative_insight,
            "safest_profile": best.profile_name,
            "highest_risk_profile": worst.profile_name
        }
