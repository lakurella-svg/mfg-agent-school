# Runbook: Check-in Storm (station/job)

**Alert type:** `CHECKIN_STORM` · **Typical severity:** CRITICAL

A checkin storm is a surge of station check-in attempts, usually after a
line restart, a misbehaving device fleet, or a shift-change misconfiguration.
The station layer sees station_checkin_rate and mes_message_rate spike while
station_auth_success_rate and control_handshake_success_rate sag; job setup
KPIs can degrade as the surge propagates.

## Triage

1. Confirm the window: compare station_checkin_rate and mes_message_rate
   against the pre-alert baseline (the alert feed carries before/during deltas).
2. Check whether station_auth_success_rate dropped more than 5 percent;
   if so the storm is saturating the authentication service, not just the
   station layer.
3. Correlate with job_release_rate on the job layer to see if the storm is
   propagating to job setup.

## Remediation

1. Enable or tighten check-in back-off on the station gateways so
   re-attempts spread out.
2. If a specific cell or device fleet dominates, apply check-in rate
   limiting for that group.
3. Add station-gateway capacity if capacity_utilization_pct stays above 80
   percent after back-off is in place.

## Validation

station_checkin_rate returns to baseline within two back-off cycles;
station authentication and control handshake success rates recover above
99 percent.
