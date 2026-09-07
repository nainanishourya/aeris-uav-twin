"""AERIS 1-Click Demonstration Scenario: Injector Degradation Sequence.

Reproducibly demonstrates the end-to-end twin divergence, anomaly detection,
health decay, and predictive maintenance trigger.
"""

import time
from aeris.telemetry.simulator import simulator

def run_demo_scenario(steps: int = 30, delay: float = 0.2):
    """Executes the complete injector degradation demonstration sequence."""
    print("=" * 75)
    print("AERIS: Starting Reproducible Demo Scenario - Injector Degradation")
    print("=" * 75)
    print("Phase 1: Nominal Baseline Operation (Health ~ 96)")
    print("-" * 75)
    
    # Phase 1: Nominal
    simulator.set_operating_point(fault="Healthy", severity=0.0, throttle=0.75)
    for i in range(5):
        frame = simulator.step()
        diag = frame["diagnostics"]
        tel = frame["telemetry"]
        res = frame["residuals"]
        print(
            f"Step {i+1:02d} | RPM: {tel['rpm']:.0f} | CHT: {tel['cht_c']:.1f}°C | EGT: {tel['egt_c']:.0f}°C | "
            f"FF: {tel['fuel_flow_lph']:.1f} L/h | Health: {diag['health_index']:.1f} ({diag['health_status']}) | "
            f"Fault: {diag['predicted_fault']} ({diag['confidence']*100:.0f}%)"
        )
        time.sleep(delay)

    # Phase 2: Progressive Injector Degradation
    print("\nPhase 2: Injecting Progressive Fuel Injector Degradation...")
    print("-" * 75)
    for i in range(steps):
        severity = ((i + 1) / steps) * 1.3
        simulator.set_operating_point(fault="Injector Abnormality", severity=severity)
        frame = simulator.step()
        diag = frame["diagnostics"]
        tel = frame["telemetry"]
        res = frame["residuals"]
        
        # Display key markers as thresholds trigger
        alert = ""
        if diag["is_anomaly"] and i < 8:
            alert = " <-- [ANOMALY DETECTED by Isolation Forest]"
        if diag["predicted_fault"] == "Injector Abnormality" and i == 8:
            alert = " <-- [FAULT CLASSIFIED: Injector Abnormality]"
        if diag["health_index"] < 70 and i == 14:
            alert = " <-- [HEALTH DROPPED TO WATCH/DEGRADED]"
        if diag["health_index"] < 50 and i == 22:
            alert = " <-- [CRITICAL MAINTENANCE DUE: RUL Depleted]"

        print(
            f"Step {i+6:02d} | FF Δ: {res['fuel_flow_residual']:+.1f} L/h (z={res['z_fuel_flow']:+.1f}) | "
            f"EGT Δ: {res['egt_residual']:+.0f}°C | Anom: {diag['anomaly_score']:.2f} | "
            f"Health: {diag['health_index']:.1f} ({diag['health_status']}) | "
            f"RUL: {diag['estimated_rul_hours']:.0f}h | "
            f"Fault: {diag['predicted_fault']} ({diag['confidence']*100:.0f}%){alert}"
        )
        time.sleep(delay)

    print("=" * 75)
    print("DEMO SUMMARY:")
    print(f"Final Health: {diag['health_index']:.1f} ({diag['health_status']})")
    print(f"Final Diagnosis: {diag['predicted_fault']} (Confidence: {diag['confidence']*100:.1f}%)")
    print(f"Maintenance Action: {diag['maintenance_action']}")
    print("=" * 75)

if __name__ == "__main__":
    run_demo_scenario(steps=25, delay=0.1)
