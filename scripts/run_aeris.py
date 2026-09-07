"""Single-command entrypoint launcher for AERIS platform.

Launches:
- Optional background model training / evaluation verification
- Telemetry simulation daemon
- FastAPI REST backend (port 8000)
- Streamlit Ground Control Station Dashboard (port 8501)
"""

import sys
import subprocess
import argparse
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

def launch_dashboard():
    """Launch Streamlit Dashboard."""
    cmd = [
        sys.executable, "-m", "streamlit", "run",
        str(BASE_DIR / "aeris" / "dashboard" / "app.py"),
        "--server.port=8501",
        "--server.headless=false",
        "--theme.base=dark"
    ]
    print("Launching AERIS Ground Control Station on http://localhost:8501 ...")
    subprocess.run(cmd, cwd=str(BASE_DIR))

def launch_api():
    """Launch FastAPI server."""
    cmd = [
        sys.executable, "-m", "uvicorn", "aeris.api.main:app",
        "--host", "0.0.0.0",
        "--port", "8000",
        "--reload"
    ]
    print("Launching AERIS REST API on http://localhost:8000 (Docs at /docs) ...")
    subprocess.run(cmd, cwd=str(BASE_DIR))

def main():
    parser = argparse.ArgumentParser(description="AERIS Platform Launcher")
    parser.add_argument("--mode", choices=["all", "dashboard", "api", "train", "demo"], default="dashboard",
                        help="Operating mode to start")
    args = parser.parse_args()

    if args.mode == "train":
        from aeris.ml.train_pipeline import run_training_pipeline
        run_training_pipeline()
    elif args.mode == "demo":
        from aeris.demo.demo_scenario import run_demo_scenario
        run_demo_scenario()
    elif args.mode == "api":
        launch_api()
    elif args.mode == "dashboard":
        launch_dashboard()
    elif args.mode == "all":
        print("Starting AERIS Full Stack (API in background + Dashboard in foreground)...")
        api_proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "aeris.api.main:app", "--host", "0.0.0.0", "--port", "8000"],
            cwd=str(BASE_DIR)
        )
        time.sleep(2)
        try:
            launch_dashboard()
        finally:
            api_proc.terminate()

if __name__ == "__main__":
    main()
