#!/usr/bin/env python3
"""Replay a real GitHub issue as a `labeled` webhook event against the local service.

Usage: python3 scripts/trigger_issue.py <issue_number> [owner/repo]

Stand-in for a public webhook endpoint during local demos: it fetches the live
issue from GitHub (via `gh`) and delivers the same payload GitHub would send.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.request


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    number = int(sys.argv[1])
    repo = sys.argv[2] if len(sys.argv) > 2 else os.getenv("TARGET_REPOSITORY", "Ritwik-Gaur/superset")
    base = os.getenv("APP_URL", "http://localhost:8080")

    issue = json.loads(
        subprocess.run(
            ["gh", "api", f"repos/{repo}/issues/{number}"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    )
    event = {"action": "labeled", "issue": issue, "repository": {"full_name": repo}}
    request = urllib.request.Request(
        f"{base}/webhooks/github",
        data=json.dumps(event).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))
    job = payload.get("job", {})
    print(f"accepted={payload.get('accepted')} job={job.get('id')} status={job.get('status')}")

    request = urllib.request.Request(f"{base}/tick", data=b"{}", method="POST")
    with urllib.request.urlopen(request, timeout=120) as response:
        print("tick:", response.read().decode("utf-8").strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
