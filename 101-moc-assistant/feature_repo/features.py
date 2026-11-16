"""Feast feature definitions for the houprod telemetry (lakurella/mfgcore-prod).

One entity (`nf`: amf | smf | upf) and one feature view per network
function. Each view carries the raw per-minute KPIs plus 1-hour rolling
aggregates (<kpi>_1h_mean/min/max) computed by the ingest pipeline
(ingest.py), and two model outputs written by the anomaly scoring step
(anomaly_score, anomaly_flag). The online store therefore always serves the
latest engineered vector per NF — the same features the anomaly model was
trained on — which is what the NOC agent's tools consume on RHOAI.

Sources are PushSources: the ingest pipeline computes features and pushes
them; the batch FileSource behind each push source is the parquet the
pipeline writes for offline (training) retrieval.
"""

from datetime import timedelta

from feast import Entity, FeatureService, FeatureView, Field, FileSource, PushSource
from feast.types import Float64, Int64

nf = Entity(name="nf", join_keys=["nf"], description="5G core network function (amf|smf|upf)")

# Raw KPI columns per NF, as published in lakurella/mfgcore-prod.
NF_KPIS = {
    "amf": [
        "mfg_link_connectivity", "capacity_utilization_pct", "buffer_occupancy_pct",
        "registration_rate", "job_setup_success_rate", "station_auth_success_rate",
        "mes_message_rate", "station_checkin_success_rate",
        "line_assignment_success_rate", "nas_security_success_rate", "control_handshake_success_rate",
    ],
    "smf": [
        "capacity_utilization_pct", "buffer_occupancy_pct", "session_establishment_rate",
        "n4_message_rate", "session_modification_rate", "policy_installation_rate",
        "pfcp_message_rate", "session_success_rate",
    ],
    "upf": [
        "capacity_utilization_pct", "buffer_occupancy_pct", "packet_processing_rate",
        "tunnel_establishment_rate", "buffer_utilization", "qos_flow_success_rate",
        "throughput_mbps", "packet_drop_rate", "latency_ms",
    ],
}

# Published file per NF in lakurella/mfgcore-prod (and the bundled data/ copy).
NF_FILES = {"amf": "station_metrics.csv", "smf": "job_metrics.csv", "upf": "line_metrics.csv"}

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
        entities=[nf],
        ttl=timedelta(days=3650),  # historical dataset; keep point-in-time joins valid
        schema=_schema(kpis),
        source=push,
        online=True,
    )


amf_kpis = _view("amf", NF_KPIS["amf"])
smf_kpis = _view("smf", NF_KPIS["smf"])
upf_kpis = _view("upf", NF_KPIS["upf"])

# What the NOC agent consumes: everything, one service.
moc_telemetry = FeatureService(
    name="moc_telemetry",
    features=[amf_kpis, smf_kpis, upf_kpis],
)
