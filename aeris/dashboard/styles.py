"""Tactical Aerospace Ground Control Station (GCS) Styling and Custom CSS for AERIS."""

AERIS_CUSTOM_CSS = """
<style>
    /* Dark Aerospace Palette */
    :root {
        --bg-primary: #0b0f19;
        --bg-secondary: #121929;
        --bg-card: #162035;
        --border-color: #1e293b;
        --accent-green: #00e5a3;
        --accent-cyan: #38bdf8;
        --accent-amber: #f59e0b;
        --accent-red: #ef4444;
        --text-primary: #f8fafc;
        --text-secondary: #94a3b8;
    }

    /* Main container background */
    .stApp {
        background-color: var(--bg-primary);
        color: var(--text-primary);
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    }

    /* Top banner HUD styling */
    .aeris-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        background: linear-gradient(90deg, #101726 0%, #17233d 100%);
        border: 1px solid #233354;
        border-radius: 8px;
        padding: 14px 24px;
        margin-bottom: 20px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
    }

    .aeris-title {
        font-size: 1.6rem;
        font-weight: 800;
        letter-spacing: 1.5px;
        color: #f8fafc;
        display: flex;
        align-items: center;
        gap: 12px;
    }

    .aeris-tag {
        font-size: 0.72rem;
        background: #00e5a322;
        color: #00e5a3;
        border: 1px solid #00e5a388;
        padding: 4px 10px;
        border-radius: 4px;
        font-weight: 700;
        letter-spacing: 1px;
    }

    /* Metric Cards */
    .metric-card {
        background-color: var(--bg-card);
        border: 1px solid var(--border-color);
        border-radius: 8px;
        padding: 16px;
        text-align: center;
        box-shadow: 0 2px 8px rgba(0,0,0,0.3);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .metric-card:hover {
        border-color: #38bdf888;
        transform: translateY(-2px);
    }
    .metric-card .label {
        font-size: 0.78rem;
        color: var(--text-secondary);
        text-transform: uppercase;
        letter-spacing: 0.8px;
        margin-bottom: 6px;
    }
    .metric-card .value {
        font-size: 1.6rem;
        font-weight: 700;
        color: var(--text-primary);
        font-family: "Courier New", Courier, monospace;
    }
    .metric-card .delta {
        font-size: 0.8rem;
        margin-top: 4px;
        font-weight: 600;
    }

    /* Health Index Big Badge */
    .health-badge {
        display: inline-block;
        padding: 8px 16px;
        border-radius: 6px;
        font-size: 1.2rem;
        font-weight: 800;
        letter-spacing: 1px;
        text-align: center;
    }

    /* Status Pill */
    .status-pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        font-size: 0.8rem;
        font-weight: 700;
        padding: 4px 12px;
        border-radius: 12px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    /* Diagnostics Table / Card */
    .diag-card {
        background-color: #121a2d;
        border: 1px solid #1e2e4a;
        border-radius: 8px;
        padding: 18px;
        margin-bottom: 16px;
    }

    /* Custom Streamlit component overrides */
    div[data-testid="stSidebar"] {
        background-color: #0d1322;
        border-right: 1px solid #1e293b;
    }

    /* Button styling */
    div.stButton > button {
        background: linear-gradient(180deg, #1e293b 0%, #0f172a 100%);
        color: #f8fafc;
        border: 1px solid #334155;
        border-radius: 6px;
        font-weight: 600;
        padding: 8px 18px;
        transition: all 0.2s ease;
    }
    div.stButton > button:hover {
        border-color: #00e5a3;
        color: #00e5a3;
        box-shadow: 0 0 12px rgba(0, 229, 163, 0.25);
    }

    /* Demo Button styling */
    .demo-btn-highlight > div > button {
        background: linear-gradient(180deg, #059669 0%, #047857 100%) !important;
        border-color: #10b981 !important;
        color: #ffffff !important;
        font-weight: 700 !important;
        box-shadow: 0 0 15px rgba(16, 185, 129, 0.4) !important;
    }
</style>
"""

PLOTLY_DARK_THEME = {
    "layout": {
        "paper_bgcolor": "#0d1322",
        "plot_bgcolor": "#121929",
        "font": {"color": "#94a3b8", "family": "Inter, sans-serif"}
    }
}

def get_dark_layout(**overrides):
    """Safely merges overrides into default dark layout without keyword collisions."""
    base = {
        "paper_bgcolor": "#0d1322",
        "plot_bgcolor": "#121929",
        "font": {"color": "#94a3b8", "family": "Inter, sans-serif"},
        "xaxis": {
            "gridcolor": "#1e293b",
            "zerolinecolor": "#1e293b",
            "tickfont": {"color": "#64748b"}
        },
        "yaxis": {
            "gridcolor": "#1e293b",
            "zerolinecolor": "#1e293b",
            "tickfont": {"color": "#64748b"}
        },
        "margin": {"l": 40, "r": 20, "t": 40, "b": 35}
    }
    base.update(overrides)
    return base
