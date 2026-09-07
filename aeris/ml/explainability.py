"""Explainable AI (XAI) Diagnostic Attribution Engine for AERIS."""

from dataclasses import dataclass, asdict
from typing import Dict, List, Any, Optional

@dataclass
class XAIExplanation:
    diagnosis: str
    confidence_pct: float
    summary: str
    factor_bars: List[Dict[str, Any]]
    physical_evidence: List[str]
    maintenance_action: str

class XAIEngine:
    """Generates human-interpretable feature attributions and root-cause evidence."""

    @staticmethod
    def explain(
        diagnosis: str,
        confidence: float,
        actual_telemetry: Dict[str, float],
        twin_expected: Dict[str, float],
        residuals: Dict[str, float],
        maintenance_action: str
    ) -> XAIExplanation:
        """Constructs an explainability packet with visual bar weights and physical evidence."""
        # Calculate divergence contributions
        feature_weights = [
            ("Fuel Flow Residual", abs(residuals.get("z_fuel_flow", 0.0)), "res_fuel_flow", "L/h"),
            ("EGT Residual", abs(residuals.get("z_egt", 0.0)), "res_egt", "°C"),
            ("CHT Residual", abs(residuals.get("z_cht", 0.0)), "res_cht", "°C"),
            ("Oil Pressure Residual", abs(residuals.get("z_oil_p", 0.0)), "res_oil_p", "bar"),
            ("Oil Temp Residual", abs(residuals.get("z_oil_t", 0.0)), "res_oil_t", "°C"),
            ("Vibration Residual", abs(residuals.get("z_vibration", 0.0)), "res_vibration", "mm/s"),
        ]

        total_mag = sum(item[1] for item in feature_weights) + 1e-6
        sorted_weights = sorted(feature_weights, key=lambda x: x[1], reverse=True)

        factor_bars = []
        for name, z_val, raw_key, unit in sorted_weights[:4]:
            pct_share = round((z_val / total_mag) * 100.0, 1)
            raw_val = residuals.get(raw_key, 0.0)
            sign = "+" if raw_val >= 0 else ""
            
            # Construct text bar representation
            num_blocks = int(round(pct_share / 10.0))
            bar_text = "█" * max(1, num_blocks)

            factor_bars.append({
                "factor_name": name,
                "share_pct": pct_share,
                "z_score": round(z_val, 2),
                "delta_formatted": f"{sign}{raw_val:.2f} {unit}",
                "ascii_bar": bar_text
            })

        # Physical evidence bullet points
        evidence = []
        if abs(residuals.get("z_fuel_flow", 0.0)) >= 2.0:
            evidence.append(
                f"Fuel flow measured {actual_telemetry.get('fuel_flow_lph', 0):.1f} L/h vs twin expected {twin_expected.get('fuel_flow_lph', 0):.1f} L/h (Δ = {residuals.get('res_fuel_flow', 0):+.1f} L/h)"
            )
        if abs(residuals.get("z_egt", 0.0)) >= 2.0:
            evidence.append(
                f"EGT measured {actual_telemetry.get('egt_c', 0):.1f}°C vs twin expected {twin_expected.get('egt_c', 0):.1f}°C (Δ = {residuals.get('res_egt', 0):+.1f}°C)"
            )
        if abs(residuals.get("z_oil_p", 0.0)) >= 2.0:
            evidence.append(
                f"Oil pressure measured {actual_telemetry.get('oil_pressure_bar', 0):.2f} bar vs twin expected {twin_expected.get('oil_pressure_bar', 0):.2f} bar (Δ = {residuals.get('res_oil_p', 0):+.2f} bar)"
            )
        if abs(residuals.get("z_cht", 0.0)) >= 2.0:
            evidence.append(
                f"CHT measured {actual_telemetry.get('cht_c', 0):.1f}°C vs twin expected {twin_expected.get('cht_c', 0):.1f}°C (Δ = {residuals.get('res_cht', 0):+.1f}°C)"
            )
        if abs(residuals.get("z_vibration", 0.0)) >= 2.0:
            evidence.append(
                f"Vibration measured {actual_telemetry.get('vibration_mms', 0):.2f} mm/s vs twin expected {twin_expected.get('vibration_mms', 0):.2f} mm/s (Δ = {residuals.get('res_vibration', 0):+.2f} mm/s)"
            )
        if not evidence:
            evidence.append("All sensor channels tracking within normal ±2σ standard deviation bounds.")

        summary = (
            f"Diagnosis: {diagnosis} (Confidence: {confidence * 100:.1f}%). "
            f"Primary driving signal is {factor_bars[0]['factor_name']} ({factor_bars[0]['delta_formatted']})."
        )

        return XAIExplanation(
            diagnosis=diagnosis,
            confidence_pct=round(confidence * 100.0, 1),
            summary=summary,
            factor_bars=factor_bars,
            physical_evidence=evidence,
            maintenance_action=maintenance_action
        )
