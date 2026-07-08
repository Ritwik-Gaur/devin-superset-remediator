# Submission Checklist

## 1. Repair GitHub Auth

`gh` is installed but the saved token is currently invalid. Re-authenticate before publishing:

```bash
gh auth login -h github.com
gh auth status
```

## 2. Publish The Solution Repository

From `/Users/ritwikgaur/cognition-test`:

```bash
gh repo create Ritwik-Gaur/devin-superset-remediator \
  --public \
  --source=. \
  --remote=origin \
  --push \
  --description "Event-driven Devin automation for Apache Superset remediation"
```

## 3. Fork Superset And Create Issues

```bash
gh repo fork apache/superset --org Ritwik-Gaur --remote=false
export TARGET_REPOSITORY=Ritwik-Gaur/superset
export GITHUB_TOKEN=ghp_...
make publish-issues
```

If the GitHub fork already exists, skip `gh repo fork` and only run `make publish-issues`.

## 4. Run Live Devin Mode

```bash
cp .env.example .env
```

Edit `.env`:

```bash
DEVIN_API_KEY=cog_...
DEVIN_ORG_ID=org-...
DEVIN_REPO=Ritwik-Gaur/superset
TARGET_REPOSITORY=Ritwik-Gaur/superset
GITHUB_TOKEN=ghp_...
DEVIN_DRY_RUN=false
```

Then:

```bash
docker compose up --build
```

Label one of the seeded Superset issues with `devin-remediate`, or run:

```bash
make simulate
```

## 5. Loom Flow

Use [docs/LOOM_SCRIPT.md](LOOM_SCRIPT.md). The punchline sequence:

1. Show the three Superset issues.
2. Trigger the event.
3. Show the Devin session URL.
4. Show the PR URL.
5. Show `/metrics` and dashboard success rate.
6. Explain how this scales to security, dependency, and quality backlogs.

## 6. Submit

Submit:

- Solution repo URL.
- Superset fork URL with seeded issues.
- Loom URL.
- Note that the service supports dry-run and live Devin mode.

