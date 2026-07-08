from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


TERMINAL_STATUSES = {"succeeded", "failed", "blocked"}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def dumps(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def loads_list(value: str | None) -> list[str]:
    if not value:
        return []
    loaded = json.loads(value)
    return list(loaded) if isinstance(loaded, list) else []


@dataclass
class IssueFinding:
    dedupe_key: str
    source: str
    repository: str
    title: str
    body: str
    issue_number: int | None = None
    issue_url: str | None = None
    severity: str = "medium"
    labels: list[str] = field(default_factory=list)
    files: list[str] = field(default_factory=list)
    acceptance_criteria: list[str] = field(default_factory=list)
    verification_commands: list[str] = field(default_factory=list)
    raw_event: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "IssueFinding":
        repository = data.get("repository") or data.get("repo") or ""
        issue_number = data.get("issue_number")
        if issue_number is not None:
            issue_number = int(issue_number)
        dedupe_key = data.get("dedupe_key")
        if not dedupe_key:
            external_id = data.get("id") or issue_number or data.get("title")
            dedupe_key = f"{data.get('source', 'scan')}:{repository}:{external_id}"
        return cls(
            dedupe_key=dedupe_key,
            source=data.get("source", "scan"),
            repository=repository,
            title=data["title"],
            body=data.get("body", ""),
            issue_number=issue_number,
            issue_url=data.get("issue_url"),
            severity=data.get("severity", "medium"),
            labels=list(data.get("labels", [])),
            files=list(data.get("files", [])),
            acceptance_criteria=list(data.get("acceptance_criteria", [])),
            verification_commands=list(data.get("verification_commands", [])),
            raw_event=dict(data.get("raw_event", data)),
        )

    def as_raw_json(self) -> str:
        return dumps(asdict(self))


@dataclass
class WorkItem:
    id: int
    dedupe_key: str
    source: str
    repository: str
    title: str
    body: str
    status: str
    issue_number: int | None = None
    issue_url: str | None = None
    severity: str = "medium"
    labels: list[str] = field(default_factory=list)
    files: list[str] = field(default_factory=list)
    acceptance_criteria: list[str] = field(default_factory=list)
    verification_commands: list[str] = field(default_factory=list)
    devin_session_id: str | None = None
    devin_url: str | None = None
    status_detail: str | None = None
    pr_urls: list[str] = field(default_factory=list)
    attempts: int = 0
    error: str | None = None
    raw_event: dict[str, Any] = field(default_factory=dict)
    raw_session: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)
    started_at: str | None = None
    completed_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

