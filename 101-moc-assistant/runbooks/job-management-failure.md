# Runbook: Job Management Failure (job/line)

**Alert type:** `JOB_MANAGEMENT_FAILURE` · **Typical severity:** MAJOR

Job release or change failures between the job orchestration layer and the
line. The job layer shows job_release_rate or job_completion_success_rate
dropping with program_download_rate or line_command_rate anomalies; the line
side shows lot_start_rate sagging while spec_compliance_rate degrades.

## Triage

1. Determine the failing leg: job-side (line command or program download
   anomalies) or line-side (lot start failures).
2. Check recipe_apply_rate on the job layer; recipe-server latency can
   masquerade as job management failure.
3. Correlate the alert window with any line resource exhaustion alert;
   job failures are often a downstream symptom.

## Remediation

1. Command path issues: verify the job-to-line controller link and reset
   the command channel if heartbeats are missing.
2. Recipe-driven: clear the recipe apply backlog or fail over to the
   secondary recipe server.
3. Line capacity: follow the resource-exhaustion runbook first, then retry
   failed jobs.

## Validation

job_completion_success_rate above 99 percent and lot_start_rate back to
baseline for 15 consecutive minutes; no new alerts in the feed.
