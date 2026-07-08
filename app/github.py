from __future__ import annotations

import hashlib
import hmac
import json
import urllib.error
import urllib.request
from typing import Any

from app.config import Config
from app.models import IssueFinding, WorkItem


class GitHubAPIError(RuntimeError):
    pass


def verify_signature(secret: str | None, payload: bytes, signature_header: str | None) -> bool:
    if not secret:
        return True
    if not signature_header:
        return False
    expected = "sha256=" + hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header)


def finding_from_github_issue_event(
    payload: dict[str, Any],
    trigger_label: str,
) -> IssueFinding | None:
    action = payload.get("action")
    if action not in {"opened", "edited", "reopened", "labeled"}:
        return None

    issue = payload.get("issue") or {}
    if issue.get("pull_request"):
        return None

    repo = payload.get("repository") or {}
    repository = repo.get("full_name", "")
    labels = [label.get("name", "") for label in issue.get("labels", [])]
    if trigger_label not in labels:
        return None

    issue_number = int(issue["number"])
    return IssueFinding(
        dedupe_key=f"github_issue:{repository}:{issue_number}",
        source="github_issue",
        repository=repository,
        issue_number=issue_number,
        issue_url=issue.get("html_url"),
        title=issue.get("title", ""),
        body=issue.get("body") or "",
        labels=labels,
        severity=_severity_from_labels(labels),
        raw_event=payload,
    )


def _severity_from_labels(labels: list[str]) -> str:
    for label in labels:
        normalized = label.lower()
        if normalized in {"critical", "high", "medium", "low"}:
            return normalized
        if normalized.startswith("severity:"):
            return normalized.split(":", 1)[1]
    return "medium"


class GitHubClient:
    def __init__(self, config: Config) -> None:
        self.config = config

    @property
    def dry_run(self) -> bool:
        return not bool(self.config.github_token)

    def comment_on_issue(self, item: WorkItem, body: str) -> dict[str, Any]:
        if self.dry_run or not item.issue_number:
            return {"dry_run": True, "body": body}
        return self._request(
            "POST",
            f"/repos/{item.repository}/issues/{item.issue_number}/comments",
            {"body": body},
        )

    def create_issue(
        self,
        repository: str,
        title: str,
        body: str,
        labels: list[str],
    ) -> dict[str, Any]:
        if self.dry_run:
            return {
                "dry_run": True,
                "repository": repository,
                "title": title,
                "body": body,
                "labels": labels,
            }
        return self._request(
            "POST",
            f"/repos/{repository}/issues",
            {"title": title, "body": body, "labels": labels},
        )

    def _request(self, method: str, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            f"https://api.github.com{path}",
            data=body,
            method=method,
            headers={
                "Authorization": f"Bearer {self.config.github_token}",
                "Accept": "application/vnd.github+json",
                "Content-Type": "application/json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "devin-superset-remediator",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise GitHubAPIError(f"GitHub API {method} {path} failed: {exc.code} {detail}") from exc

