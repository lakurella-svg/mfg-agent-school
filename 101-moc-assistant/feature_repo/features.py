"""Feast feature definitions for the houprod telemetry (lakurella/mfgcore-prod).

One entity (`unit`: station | job | line) and one feature view per production
unit. Each view carries the raw per-minute KPIs plus 1-hour rolling
aggregates (<kpi>_1h_mean/min/max) computed by the ingest pipeline
(ingest.py), and two model outputs written by the anomaly scoring step
(anomaly_score, anomaly_flag). The online store therefore always serves the
latest engineered vector per unit — the same features the anomaly model was
trained on — which is what the MOC agent's tools consume on the AI platform.

Sources are PushSources: the ingest pipeline computes features and pushes
them; the batch FileSource behind each push source is the parquet the
pipeline writes for offline (training) retrieval.
"""

from datetime import timedelta

from feast import Entity, FeatureService, FeatureView, Field, FileSource, PushSource
from feast.types import Float64, Int64

unit = Entity(name="unit", join_keys=["unit"], description="mfg core production unit (station|job|line)")

# Raw KPI columns per unit, as published in lakurella/mfgcore-prod.
UNIT_KPIS = {
    "station": [
        "mfg_link_connectivity", "capacity_utilization_pct", "buffer_occupancy_pct",
        "station_checkin_rate", "job_setup_success_rate", "station_auth_success_rate",
        "mes_message_rate", "station_checkin_success_rate",
        "line_assignment_success_rate", "device_security_success_rate", "control_handshake_success_rate",
    ],
    "job": [
        "capacity_utilization_pct", "buffer_occupancy_pct", "job_release_rate",
        "line_command_rate", "job_change_rate", "recipe_apply_rate",
        "program_download_rate", "job_completion_success_rate",
    ],
    "line": [
        "capacity_utilization_pct", "buffer_occupancy_pct", "units_processed_rate",
        "lot_start_rate", "conveyor_fill_pct", "spec_compliance_rate",
        "line_throughput", "scrap_rate", "cycle_time",
    ],
}

# Published file per unit in lakurella/mfgcore-prod (and the bundled data/ copy).
UNIT_FILES = {"station": "station_metrics.csv", "job": "job_metrics.csv", "line": "line_metrics.csv"}

AGGS = ("1h_mean", "1h_min", "1h_max")


def _schema(kpis: list[str]) -> list[Field]:
    fields = [Field(name=k, dtype=Float64) for k in kpis]
    fields += [Field(name=f"{k}_{a}", dtype=Float64) for k in kpis for a in AGGS]
    fields += [Field(name="anomaly_score", dtype=Float64),
               Field(name="anomaly_flag", dtype=Int64)]
    return fields


def _view(name: str, kpis: list[str]) -> FeatureView:
    batch = FileSource(
        name=f"{name}_batch",
        path=f"data/{name}_features.parquet",
        timestamp_field="event_timestamp",
    )
    push = PushSource(name=f"{name}_push", batch_source=batch)
    return FeatureView(
        name=f"{name}_kpis",
        entities=[unit],
        ttl=timedelta(days=3650),  # historical dataset; keep point-in-time joins valid
        schema=_schema(kpis),
        source=push,
        online=True,
    )


station_kpis = _view("station", UNIT_KPIS["station"])
job_kpis = _view("job", UNIT_KPIS["job"])
line_kpis = _view("line", UNIT_KPIS["line"])

# What the MOC agent consumes: everything, one service.
moc_telemetry = FeatureService(
    name="moc_telemetry",
    features=[station_kpis, job_kpis, line_kpis],
)
