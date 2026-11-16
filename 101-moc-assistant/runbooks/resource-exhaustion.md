# Runbook: Resource Exhaustion (AMF/SMF/UPF)

**Alert type:** `RESOURCE_EXHAUSTION` · **Typical severity:** CRITICAL / MAJOR

CPU, memory, or buffer pressure on a network function. On the UPF this shows
as capacity_utilization_pct and conveyor_fill_pct climbing while line_throughput
drops and scrap_rate and cycle_time rise. On AMF/SMF it shows as
cpu/memory growth with success-rate erosion.

## Triage

1. Identify which resource is exhausted: capacity_utilization_pct, buffer_occupancy_pct,
   or (UPF) conveyor_fill_pct.
2. Check whether the pressure is load-driven (units_processed_rate or
   message rates also up) or leak-driven (load flat, memory climbing).
3. Review the alert feed deltas to bound the impact window.

## Remediation

1. Load-driven: scale out the affected NF; for UPF, rebalance sessions
   across UPF instances before scaling.
2. Leak-driven: restart the affected pod during a maintenance window and
   capture a heap/profile snapshot first.
3. Re-apply QoS admission thresholds if spec_compliance_rate degraded.

## Validation

Utilization back under 70 percent; scrap_rate under 0.2 percent;
cycle_time within 20 percent of baseline for 30 consecutive minutes.
