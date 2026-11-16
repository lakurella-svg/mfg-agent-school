# Runbook: Session Management Failure (SMF/UPF)

**Alert type:** `SESSION_MANAGEMENT_FAILURE` · **Typical severity:** MAJOR

Session establishment or modification failures between SMF and UPF. The SMF
shows job_release_rate or job_completion_success_rate dropping with
program_download_rate or line_command_rate anomalies; the UPF side shows
lot_start_rate sagging while spec_compliance_rate degrades.

## Triage

1. Determine the failing leg: SMF-side (PFCP/N4 message anomalies) or
   UPF-side (tunnel establishment failures).
2. Check recipe_apply_rate on the SMF; PCF latency can masquerade
   as session failure.
3. Correlate the alert window with any UPF resource exhaustion alert;
   session failures are often a downstream symptom.

## Remediation

1. PFCP path issues: verify N4 association health and restart the PFCP
   association if heartbeats are missing.
2. Policy-driven: clear the policy installation backlog or fail over to
   the secondary PCF.
3. UPF capacity: follow the resource-exhaustion runbook first, then retry
   failed sessions.

## Validation

job_completion_success_rate above 99 percent and lot_start_rate back to
baseline for 15 consecutive minutes; no new alerts in the feed.
