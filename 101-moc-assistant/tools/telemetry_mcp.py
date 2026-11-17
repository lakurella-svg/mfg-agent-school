"""MCP server exposing the telemetry skills (stdio transport).

Run standalone for MCP-native harnesses, or put an MCP gateway in front for
claims-based tool authorization; the skill logic stays in lib.py either way.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastmcp import FastMCP  # noqa: E402

from tools import lib  # noqa: E402

mcp = FastMCP("moc-telemetry")


@mcp.tool()
def get_kpi_summary(unit: str = "all", window_minutes: int = 60) -> str:
    """Summarize mfg core KPIs for a production unit (station|job|line|all)."""
    return lib.get_kpi_summary(unit=unit, window_minutes=window_minutes)


@mcp.tool()
def detect_anomalies(unit: str = "all", contamination: float = 0.02) -> str:
    """Isolation Forest anomaly detection on station/job/line KPI series."""
    return lib.detect_anomalies(unit=unit, contamination=contamination)


@mcp.tool()
def get_active_alerts(component: str = "all") -> str:
    """Fetch the structured alert feed (type, severity, component, KPI deltas)."""
    return lib.get_active_alerts(component=component)


if __name__ == "__main__":
    mcp.run()
