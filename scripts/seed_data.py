"""Seed SQLite database with initial flight telemetry and maintenance history."""

import sys
import time
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from aeris.telemetry.simulator import simulator
from aeris.telemetry.database import AerisDatabase

def seed_database(num_steps: int = 40):
    """Populates database with nominal telemetry steps."""
    print("Seeding AERIS SQLite database with baseline flight records...")
    db = AerisDatabase()
    
    # 30 healthy steps
    simulator.set_operating_point(fault="Healthy", severity=0.0, throttle=0.74)
    for _ in range(num_steps):
        simulator.step()
        time.sleep(0.02)
        
    print(f"Successfully populated {num_steps} baseline telemetry and diagnostic frames into database.")

if __name__ == "__main__":
    seed_database()
