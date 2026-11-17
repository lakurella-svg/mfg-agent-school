# Runbook: Resource Exhaustion (station/job/line)

**Alert type:** `RESOURCE_EXHAUSTION` · **Typical severity:** CRITICAL / MAJOR

Capacity, buffer, or conveyor pressure on a production unit. On the line
this shows as capacity_utilization_pct and conveyor_fill_pct climbing while
line_throughput drops and scrap_rate and cycle_time rise. On the station and
job layers it shows as capacity and buffer growth with success-rate erosion.

## Triage

1. Identify which resource is exhausted: capacity_utilization_pct,
   buffer_occupancy_pct, or (line) conveyor_fill_pct.
2. Check whether the pressure is load-driven (units_processed_rate or
   message rates also up) or leak-driven (load flat, buffer climbing).
3. Review the alert feed deltas to bound the impact window.

## Remediation

1. Load-driven: add capacity to the affected unit; for the line, rebalance
   lots across parallel lines before adding capacity.
2. Leak-driven: restart the affected controller during a maintenance window
   and capture a diagnostic snapshot first.
3. Re-apply quality admission thresholds if spec_compliance_rate degraded.

## Validation

Utilization back under 70 percent; scrap_rate under 0.2 percent;
cycle_time within 20 percent of baseline for 30 consecutive minutes.
