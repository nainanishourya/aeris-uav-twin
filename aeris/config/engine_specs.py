"""Generic Aero-Piston Engine Technical Specifications and Nominal Operating Bounds.

DISCLAIMER:
This specification model represents a generic 4-cylinder, 4-stroke, turbocharged,
spark-ignition aero-piston engine indicative of civilian/dual-use UAV propulsion systems
(approx 115-140 HP class). It does NOT disclose or model classified DRDO proprietary specs.
"""

from dataclasses import dataclass
from typing import Dict, Tuple

@dataclass(frozen=True)
class EngineParameters:
    displacement_cc: float = 1211.0          # 1.2L 4-cylinder boxer / inline
    compression_ratio: float = 9.0           # Compression ratio
    rated_power_kw: float = 85.0             # ~115 HP
    max_power_kw: float = 104.0              # ~140 HP at takeoff
    max_rpm: float = 5800.0                  # Max takeoff RPM
    nominal_cruise_rpm: float = 5000.0       # Cruise RPM
    idle_rpm: float = 1600.0                 # Idle RPM
    turbo_boost_max_inhg: float = 39.0       # Max manifold pressure
    cooling_type: str = "Liquid-cooled heads, air-cooled cylinders"
    fuel_type: str = "AVGAS 100LL / MOGAS RON 95"

@dataclass(frozen=True)
class OperatingLimits:
    """Safe, Caution, and Critical operational envelopes."""
    # Sensor: (Min_Safe, Max_Safe, Max_Caution, Max_Critical)
    rpm: Tuple[float, float, float, float] = (1400.0, 5500.0, 5700.0, 6000.0)
    cht_celsius: Tuple[float, float, float, float] = (70.0, 125.0, 135.0, 145.0)
    egt_celsius: Tuple[float, float, float, float] = (620.0, 780.0, 830.0, 880.0)
    oil_pressure_bar: Tuple[float, float, float, float] = (2.0, 5.0, 6.0, 7.0) # min critical is < 1.5
    oil_temp_celsius: Tuple[float, float, float, float] = (70.0, 110.0, 120.0, 130.0)
    fuel_flow_lph: Tuple[float, float, float, float] = (10.0, 32.0, 36.0, 42.0)
    vibration_mms: Tuple[float, float, float, float] = (0.5, 3.0, 4.5, 7.0)
    battery_voltage: Tuple[float, float, float, float] = (13.2, 14.5, 15.0, 15.8) # min critical < 12.0

# Baseline standard deviations of healthy physics residuals for normalization
RESIDUAL_BASELINE_STDS: Dict[str, float] = {
    "cht": 3.2,           # °C standard deviation under steady state
    "egt": 12.5,          # °C standard deviation
    "oil_pressure": 0.18, # bar standard deviation
    "oil_temp": 2.1,      # °C standard deviation
    "fuel_flow": 0.65,    # L/h standard deviation
    "vibration": 0.25,    # mm/s standard deviation
}

# Health index severity thresholds (Configurable)
HEALTH_THRESHOLDS = {
    "HEALTHY": 90.0,
    "NORMAL_WATCH": 70.0,
    "DEGRADED": 50.0,
    "CRITICAL": 30.0,
    "SEVERE": 0.0
}
