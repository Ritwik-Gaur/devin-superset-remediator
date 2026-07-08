#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.config import Config
from app.github import GitHubClient


def main() -> int:
    plan_path = sys.argv[1] if len(sys.argv) > 1 else "issues/superset-remediation-plan.json"
    plan = json.load(open(plan_path, encoding="utf-8"))
    repository = os.getenv("TARGET_REPOSITORY") or plan["repository"]
    if not repository or "/" not in repository:
        print("Set TARGET_REPOSITORY=owner/superset before publishing issues.", file=sys.stderr)
        return 2

    config = Config.from_env()
    github = GitHubClient(config)
    if github.dry_run:
        print("GITHUB_TOKEN is not set. Printing issues without creating them.")

    for finding in plan["findings"]:
        body = render_issue_body(finding, plan)
        labels = list(dict.fromkeys(finding.get("labels", []) + [config.trigger_label]))
        result = github.create_issue(repository, finding["title"], body, labels)
        if result.get("dry_run"):
            print(json.dumps(result, indent=2))
        else:
            print(f"Created issue: {result.get('html_url')}")
    return 0


def render_issue_body(finding: dict, plan: dict) -> str:
    files = "\n".join(f"- `{path}`" for path in finding.get("files", []))
    criteria = "\n".join(f"- {item}" for item in finding.get("acceptance_criteria", []))
    commands = "\n".join(f"- `{cmd}`" for cmd in finding.get("verification_commands", []))
    return f"""## Context

{finding["body"]}

## Scope

{files}

## Acceptance criteria

{criteria}

## Suggested verification

{commands}

## Automation

This issue is part of the Devin Superset Remediation Conveyor demo. Adding the `{os.getenv("TRIGGER_LABEL", "devin-remediate")}` label allows the orchestrator to create and monitor a Devin session for this work.

Source Superset commit observed during planning: `{plan.get("source_commit", "unknown")}`.
"""


if __name__ == "__main__":
    raise SystemExit(main())
