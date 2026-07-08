from __future__ import annotations

import threading
import time
from datetime import datetime, timezone
from typing import Any

from app.config import Config
from app.devin import DevinClient
from app.github import GitHubClient
from app.models import IssueFinding, WorkItem, utc_now
from app.storage import Store


class Orchestrator:
    def __init__(
        self,
        config: Config,
        store: Store,
        devin: DevinClient | None = None,
        github: GitHubClient | None = None,
    ) -> None:
        self.config = config
        self.store = store
        self.devin = devin or DevinClient(config)
        self.github = github or GitHubClient(config)
        self._lock = threading.Lock()

    def accept_finding(self, finding: IssueFinding) -> WorkItem:
        item = self.store.upsert_finding(finding)
        return item

    def tick(self) -> dict[str, Any]:
        with self._lock:
            started = []
            polled = []
            running = self.store.list_by_status(["running"], limit=1000)
            capacity = max(self.config.max_parallel_sessions - len(running), 0)
            if capacity:
                for item in self.store.list_by_status(["queued"], limit=capacity):
                    started.append(self._start_item(item).id)
            for item in self.store.list_by_status(["running"], limit=1000):
                polled.append(self._poll_item(item).id)
            return {"started": started, "polled": polled}

    def _start_item(self, item: WorkItem) -> WorkItem:
        item = self.store.increment_attempts(item.id)
        try:
            session = self.devin.create_session(item)
            updated = self.store.update_item(
                item.id,
                status="running",
                devin_session_id=session.get("session_id"),
                devin_url=session.get("url"),
                status_detail=session.get("status_detail") or session.get("status"),
                raw_session=session,
                started_at=utc_now(),
                error=None,
            )
            self.store.add_audit(
                item.id,
                "devin_session_started",
                f"Started Devin session {updated.devin_session_id}",
                session,
            )
            self.github.comment_on_issue(
                updated,
                (
                    "Devin remediation started.\n\n"
                    f"- Session: {updated.devin_url}\n"
                    f"- Work item: `{updated.dedupe_key}`\n"
                    f"- Automation status: `{updated.status}`"
                ),
            )
            return updated
        except Exception as exc:
            failed = self.store.update_item(
                item.id,
                status="failed",
                error=str(exc),
                completed_at=utc_now(),
            )
            self.store.add_audit(item.id, "devin_session_failed", str(exc), {})
            return failed

    def _poll_item(self, item: WorkItem) -> WorkItem:
        if not item.devin_session_id:
            return self.store.update_item(
                item.id,
                status="failed",
                error="Running item has no Devin session ID",
                completed_at=utc_now(),
            )

        if self.devin.dry_run:
            return self._poll_dry_run(item)

        try:
            session = self.devin.get_session(item.devin_session_id)
            pr_urls = _extract_pr_urls(session)
            status = session.get("status")
            status_detail = session.get("status_detail") or status

            fields: dict[str, Any] = {
                "status_detail": status_detail,
                "raw_session": session,
                "pr_urls": pr_urls or item.pr_urls,
            }
            if status == "error":
                fields.update(status="failed", error="Devin session entered error state", completed_at=utc_now())
            elif status == "exit" or status_detail == "finished":
                fields.update(status="succeeded", completed_at=utc_now())
            elif status == "suspended":
                # Suspension is terminal for the conveyor: quota/billing suspensions are
                # blocked, and an idle/user suspension counts as success only if the
                # session already produced a PR. Humans can resume via the session URL.
                if status_detail in {"inactivity", "user_request"} and (pr_urls or item.pr_urls):
                    fields.update(status="succeeded", completed_at=utc_now())
                else:
                    fields.update(status="blocked", error=f"Session suspended: {status_detail}", completed_at=utc_now())

            updated = self.store.update_item(item.id, **fields)
            if updated.status == "succeeded":
                self._announce_completion(updated)
            return updated
        except Exception as exc:
            self.store.add_audit(item.id, "devin_poll_failed", str(exc), {})
            return self.store.update_item(item.id, status_detail="poll_failed", error=str(exc))

    def _poll_dry_run(self, item: WorkItem) -> WorkItem:
        age_seconds = _age_seconds(item.started_at)
        if age_seconds < 2:
            return self.store.update_item(
                item.id,
                status_detail="dry_run_investigating",
                raw_session={
                    **item.raw_session,
                    "status": "running",
                    "status_detail": "dry_run_investigating",
                },
            )

        pr_number = 9000 + item.id
        pr_url = f"https://github.com/{item.repository}/pull/{pr_number}"
        updated = self.store.update_item(
            item.id,
            status="succeeded",
            status_detail="dry_run_pr_ready",
            pr_urls=[pr_url],
            raw_session={
                **item.raw_session,
                "status": "exit",
                "status_detail": "finished",
                "pull_requests": [{"pr_state": "open", "pr_url": pr_url}],
                "structured_output": {
                    "summary": "Dry-run completed. Live mode will let Devin create this PR.",
                    "changed_files": item.files,
                    "verification": {
                        "commands_run": item.verification_commands,
                        "result": "simulated-pass",
                    },
                    "pull_requests": [{"url": pr_url, "state": "open"}],
                    "risk_notes": ["Dry-run output is deterministic demo evidence."],
                },
            },
            completed_at=utc_now(),
        )
        self.store.add_audit(
            item.id,
            "dry_run_completed",
            f"Simulated Devin remediation and PR {pr_url}",
            {"pr_url": pr_url},
        )
        self._announce_completion(updated)
        return updated

    def _announce_completion(self, item: WorkItem) -> None:
        prs = "\n".join(f"- {url}" for url in item.pr_urls) or "- No PR URL found"
        self.github.comment_on_issue(
            item,
            (
                "Devin remediation completed.\n\n"
                f"- Session: {item.devin_url}\n"
                f"- Status: `{item.status_detail}`\n"
                f"- Pull request(s):\n{prs}"
            ),
        )

    def run_forever(self, stop_event: threading.Event) -> None:
        while not stop_event.is_set():
            self.tick()
            stop_event.wait(self.config.devin_poll_seconds)


def _extract_pr_urls(session: dict[str, Any]) -> list[str]:
    urls = []
    for pr in session.get("pull_requests") or []:
        url = pr.get("pr_url") or pr.get("url")
        if url:
            urls.append(url)
    structured = session.get("structured_output") or {}
    for pr in structured.get("pull_requests") or []:
        url = pr.get("url")
        if url and url not in urls:
            urls.append(url)
    return urls


def _age_seconds(started_at: str | None) -> float:
    if not started_at:
        return 0.0
    try:
        started = datetime.fromisoformat(started_at)
    except ValueError:
        return 0.0
    return (datetime.now(timezone.utc) - started).total_seconds()

