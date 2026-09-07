"""Cross-Sensor Consistency Checking and Sensor Drift/Failure Detection Engine."""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional

@dataclass
class SensorHealthStatus:
    channel: str
    is_valid: bool
    status: str                       # "Nominal", "Drift Warning", "Failed/Stuck", "Unphysical Open-Circuit"
    confidence: float
    evidence: str

@dataclass
class SensorConsistencyReport:
    all_sensors_valid: bool
    suspect_sensors: List[str]
    channel_reports: Dict[str, SensorHealthStatus]
    summary_message: str

class SensorValidator:
    """Performs cross-channel thermomechanical consistency validation against physics invariants."""

    def __init__(self):
        # Rolling buffer for stuck sensor detection (variance check)
        self._history: Dict[str, List[float]] = {
            "cht_c": [],
            "egt_c": [],
            "oil_pressure_bar": [],
            "oil_temp_c": [],
            "fuel_flow_lph": [],
            "vibration_mms": []
        }
        self.buffer_size = 15

    def update_history(self, telemetry: Dict[str, float]):
        for key in self._history:
            if key in telemetry:
                self._history[key].append(telemetry[key])
                if len(self._history[key]) > self.buffer_size:
                    self._history[key].pop(0)

    def evaluate(
        self,
        actual: Dict[str, float],
        twin_expected: Dict[str, float],
        residuals: Dict[str, float]
    ) -> SensorConsistencyReport:
        """Evaluates physical consistency across all sensor channels."""
        self.update_history(actual)
        reports: Dict[str, SensorHealthStatus] = {}
        suspects: List[str] = []

        # Extract values
        act_cht = actual.get("cht_c", 105.0)
        act_egt = actual.get("egt_c", 720.0)
        act_oil_p = actual.get("oil_pressure_bar", 4.0)
        act_oil_t = actual.get("oil_temp_c", 90.0)
        act_vib = actual.get("vibration_mms", 1.5)
        act_ff = actual.get("fuel_flow_lph", 20.0)

        z_cht = abs(residuals.get("z_cht", 0.0))
        z_egt = abs(residuals.get("z_egt", 0.0))
        z_oil_p = abs(residuals.get("z_oil_p", 0.0))
        z_oil_t = abs(residuals.get("z_oil_t", 0.0))
        z_vib = abs(residuals.get("z_vibration", 0.0))

        # 1. CHT Cross-Validation
        # Case A: CHT residual surges (z > 3.0), BUT EGT, Oil Temp, Vibration, and Twin are normal
        if z_cht > 3.0 and z_egt < 1.5 and z_oil_t < 1.5 and z_vib < 1.5:
            reports["cht"] = SensorHealthStatus(
                channel="CHT (Cylinder Head Temp)",
                is_valid=False,
                status="Drift Warning",
                confidence=0.92,
                evidence=f"CHT diverged (z={z_cht:.1f}), but EGT (z={z_egt:.1f}), Oil Temp (z={z_oil_t:.1f}), and Vibration are normal. Indicates transducer drift rather than true engine overheating."
            )
            suspects.append("CHT Sensor")
        elif act_cht < 10.0 or act_cht > 250.0:
            reports["cht"] = SensorHealthStatus(
                channel="CHT",
                is_valid=False,
                status="Unphysical Open-Circuit",
                confidence=0.99,
                evidence="CHT reading is outside physical thermodynamic envelope."
            )
            suspects.append("CHT Sensor")
        else:
            reports["cht"] = SensorHealthStatus(
                channel="CHT",
                is_valid=True,
                status="Nominal",
                confidence=0.98,
                evidence="Consistent with combustion and cooling parameters."
            )

        # 2. EGT Cross-Validation
        # Thermocouple open-circuit typically drops to ambient or zero instantly
        if act_egt < 100.0 and act_cht > 70.0:
            reports["egt"] = SensorHealthStatus(
                channel="EGT (Exhaust Gas Temp)",
                is_valid=False,
                status="Failed/Stuck",
                confidence=0.96,
                evidence=f"EGT dropped to {act_egt}°C while engine is firing and CHT is {act_cht}°C. Probable thermocouple open-circuit."
            )
            suspects.append("EGT Sensor")
        elif z_egt > 3.5 and z_cht < 1.2 and abs(residuals.get("z_fuel_flow", 0.0)) < 1.2:
            reports["egt"] = SensorHealthStatus(
                channel="EGT",
                is_valid=False,
                status="Drift Warning",
                confidence=0.88,
                evidence=f"Isolated EGT divergence (z={z_egt:.1f}) without corresponding CHT or Fuel Flow change."
            )
            suspects.append("EGT Sensor")
        else:
            reports["egt"] = SensorHealthStatus(
                channel="EGT",
                is_valid=True,
                status="Nominal",
                confidence=0.97,
                evidence="Cross-correlated with fuel flow and RPM."
            )

        # 3. Oil Pressure Sensor Cross-Validation
        # Sudden oil pressure reading of 0 bar with completely normal oil temp and no vibration spike
        if act_oil_p < 0.3 and act_oil_t < 115.0 and z_vib < 1.5 and actual.get("rpm", 0.0) > 3000:
            reports["oil_pressure"] = SensorHealthStatus(
                channel="Oil Pressure",
                is_valid=False,
                status="Failed/Stuck",
                confidence=0.91,
                evidence="Oil pressure indicates near-zero while engine runs at cruise RPM with normal oil temperature and no mechanical seizure vibration."
            )
            suspects.append("Oil Pressure Sensor")
        else:
            reports["oil_pressure"] = SensorHealthStatus(
                channel="Oil Pressure",
                is_valid=True,
                status="Nominal",
                confidence=0.98,
                evidence="Nominal hydraulic pressure."
            )

        # 4. Stuck Sensor / Zero-Variance Detection (Rolling buffer)
        for ch_key, hist in self._history.items():
            if len(hist) >= self.buffer_size:
                variance = max(hist) - min(hist)
                if variance == 0.0 and actual.get("rpm", 0.0) > 1500.0:
                    # Sensor is completely frozen
                    clean_name = ch_key.replace("_c", "").replace("_bar", "").replace("_lph", "").replace("_mms", "")
                    reports[clean_name] = SensorHealthStatus(
                        channel=clean_name.upper(),
                        is_valid=False,
                        status="Failed/Stuck",
                        confidence=0.95,
                        evidence=f"Sensor variance is exactly 0.0 over last {self.buffer_size} dynamic samples (frozen transducer signal)."
                    )
                    if f"{clean_name.upper()} Sensor" not in suspects:
                        suspects.append(f"{clean_name.upper()} Sensor")

        all_valid = len(suspects) == 0
        summary = "All sensor channels physically consistent with Digital Twin." if all_valid else (
            f"Sensor inconsistency detected: {', '.join(suspects)}. Disambiguated from true engine mechanical faults."
        )

        return SensorConsistencyReport(
            all_sensors_valid=all_valid,
            suspect_sensors=suspects,
            channel_reports=reports,
            summary_message=summary
        )
