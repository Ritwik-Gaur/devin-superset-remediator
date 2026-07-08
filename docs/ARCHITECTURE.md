# Architecture

## System Shape

The service has four responsibilities:

1. Intake: accept GitHub issue webhooks or scan-result events.
2. Control plane: dedupe findings, persist work items, and enforce concurrency.
3. Devin lifecycle: create sessions, poll status, collect PR URLs, and record structured output.
4. Observability: expose a dashboard, JSON job API, audit trail, and Prometheus-style metrics.

The current implementation intentionally uses Python standard library only. That keeps the demo easy to run inside Docker and avoids dependency churn during an interview evaluation.

## Event Model

The primary production event is a GitHub issue with the `devin-remediate` label. This gives humans a clean control point:

- scanners or engineers can create issues freely;
- staff engineers decide which issues are safe for autonomous remediation by labeling them;
- the automation owns the rest of the workflow.

The secondary event is `POST /events/scan`, which accepts a batch of scanner findings. This simulates a CodeQL, Semgrep, Dependabot, or internal quality scanner integration.

## Devin API Usage

For every accepted work item, the orchestrator calls:

- `POST /v3/organizations/{org_id}/sessions` with a scoped prompt, repo context, tags, optional ACU limit, and a structured output schema.
- `GET /v3/organizations/{org_id}/sessions/{devin_id}` while the task is active.
- `GET /v3/organizations/{org_id}/sessions/{devin_id}/messages` when deeper session traceability is needed.

The session prompt tells Devin to inspect the repo, make the smallest safe fix, run targeted verification, open a PR, and produce structured output.

## Failure Modes

- Missing Devin credentials: deterministic dry-run mode.
- Invalid Devin credentials or permissions: work item becomes `failed` with the API error captured.
- Quota or payment suspension: work item becomes `blocked`.
- Session waits for user approval: status detail is visible on the dashboard for intervention.
- Duplicate events: deduped by source, repository, and issue/finding id.

## Production Extensions

- Add GitHub Checks output for each work item.
- Promote `/metrics` to a managed Prometheus scrape target.
- Add Slack summaries for blocked and completed sessions.
- Split policy from execution with a rules file that maps scanner classes to ACU limits and review requirements.
- Add a nightly scheduler that reads open security/dependency issues and labels safe candidates.

