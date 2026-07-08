# 5-Minute Loom Script

## 0:00 - What

"This is a Devin remediation conveyor for Apache Superset. The workflow problem is maintenance drag: scanners and engineers can identify dozens of small security, dependency, and code-quality issues, but each still requires repo understanding, targeted tests, and a clean PR. Senior engineers become the queue manager. This system turns those findings into Devin work orders."

Show `issues/superset-remediation-plan.json` and the three seeded issues.

## 0:45 - How

"The trigger is a GitHub issue label or scanner event. The service dedupes it into SQLite, builds a scoped prompt, then calls the Devin v3 sessions API. Devin gets the repository, acceptance criteria, verification commands, and a structured output schema. The orchestrator polls session state, captures PR URLs, comments back on the issue, and updates the dashboard."

Show:

- `app/orchestrator.py`
- `app/devin.py`
- dashboard at `http://localhost:8080`
- `/metrics`

Run:

```bash
make simulate
curl -s http://localhost:8080/metrics
```

## 2:30 - Technical Depth

"I deliberately separated the control plane from Devin execution. The control plane handles idempotency, concurrency, lifecycle state, and observability. Devin handles the code work. That gives engineering leadership an operating model: we know what is queued, running, blocked, completed, and how many PRs were created."

Point to:

- dedupe key in `app/storage.py`
- structured output schema in `app/prompts.py`
- blocked quota/session states in `app/orchestrator.py`

## 3:40 - Why Devin

"A scanner can tell us shell=True exists. A dependency bot can bump a version. But neither can navigate Superset's Python and frontend conventions, decide the narrowest safe patch, update tests, run verification, and create a coherent PR. Devin is uniquely suited because the task requires autonomous repo investigation plus code execution."

## 4:25 - When / Next Steps

"In a customer engagement, I would wire this to the customer's GitHub org, tune the policy by finding class, start with low-risk issues under an ACU cap, and report weekly throughput: accepted findings, completed PRs, blocked sessions, merged PRs, and engineer review time saved. The first expansion would be Slack escalation for blocked sessions and GitHub Checks for PR-level visibility."

