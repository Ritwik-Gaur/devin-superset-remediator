# Submission Checklist

## Done

- [x] Solution repository published: <https://github.com/Ritwik-Gaur/devin-superset-remediator>
- [x] Superset fork created with Issues enabled: <https://github.com/Ritwik-Gaur/superset>
- [x] Seeded remediation issues published, each labeled `devin-remediate`:
  - [#1 Replace shell=True in BashMock release test helper](https://github.com/Ritwik-Gaur/superset/issues/1)
  - [#2 Remove deprecated datetime.utcnow from report scheduling hot paths](https://github.com/Ritwik-Gaur/superset/issues/2)
  - [#3 Implement q filtering for ExtensionsRestApi.get_list](https://github.com/Ritwik-Gaur/superset/issues/3)
- [x] Tests pass, Docker image builds, dry-run demo verified end to end.

## Remaining

### 1. Get Devin credentials

In the Devin app, create a service-user API key (`cog_...`) and copy your org ID
(`org-...`). Put both in `.env` (already scaffolded at the repo root).

### 2. Give Devin access to the fork

In Devin's GitHub integration settings, grant access to `Ritwik-Gaur/superset`.
Devin cannot open PRs against a repo it cannot see — verify this before the live run.

### 3. Run live mode

```bash
docker compose up --build
```

Then either rely on the already-labeled issues via `POST /simulate`, or exercise the
webhook path by re-labeling an issue (requires a public URL for the webhook), and watch:

- Dashboard: <http://localhost:8080>
- Metrics: <http://localhost:8080/metrics>
- Devin session URLs appear per work item; PR URLs attach when Devin finishes.

Real sessions take 10–30+ minutes each. If a session shows `waiting_for_approval`,
open its session URL and approve the plan.

### 4. Record the Loom

Follow [docs/LOOM_SCRIPT.md](LOOM_SCRIPT.md). Punchline sequence:

1. Show the three Superset issues.
2. Trigger the event.
3. Show a live Devin session.
4. Show the PR(s) Devin opened.
5. Show the dashboard and `/metrics`.
6. Explain how this scales to security, dependency, and quality backlogs.

### 5. Submit

- Solution repo: <https://github.com/Ritwik-Gaur/devin-superset-remediator>
- Superset fork: <https://github.com/Ritwik-Gaur/superset>
- Loom URL.
- Note that the service supports both dry-run (no credentials) and live Devin mode.
