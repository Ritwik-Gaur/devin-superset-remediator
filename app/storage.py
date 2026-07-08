from __future__ import annotations

import json
import os
import sqlite3
from collections import Counter
from pathlib import Path
from typing import Any

from app.models import IssueFinding, WorkItem, dumps, loads_list, utc_now


WORK_ITEM_COLUMNS = """
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dedupe_key TEXT NOT NULL UNIQUE,
    source TEXT NOT NULL,
    repository TEXT NOT NULL,
    issue_number INTEGER,
    issue_url TEXT,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    severity TEXT NOT NULL,
    labels TEXT NOT NULL,
    files TEXT NOT NULL,
    acceptance_criteria TEXT NOT NULL,
    verification_commands TEXT NOT NULL,
    status TEXT NOT NULL,
    devin_session_id TEXT,
    devin_url TEXT,
    status_detail TEXT,
    pr_urls TEXT NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    error TEXT,
    raw_event TEXT NOT NULL,
    raw_session TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    started_at TEXT,
    completed_at TEXT
"""


class Store:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        parent = Path(db_path).parent
        if str(parent):
            parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self.connect() as conn:
            conn.execute(f"CREATE TABLE IF NOT EXISTS work_items ({WORK_ITEM_COLUMNS})")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    work_item_id INTEGER,
                    event_type TEXT NOT NULL,
                    message TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_work_items_status ON work_items(status)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_audit_work_item ON audit_events(work_item_id)"
            )

    def upsert_finding(self, finding: IssueFinding) -> WorkItem:
        now = utc_now()
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO work_items (
                    dedupe_key, source, repository, issue_number, issue_url, title, body,
                    severity, labels, files, acceptance_criteria, verification_commands,
                    status, pr_urls, raw_event, raw_session, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'queued', '[]', ?, '{}', ?, ?)
                ON CONFLICT(dedupe_key) DO UPDATE SET
                    title=excluded.title,
                    body=excluded.body,
                    severity=excluded.severity,
                    labels=excluded.labels,
                    files=excluded.files,
                    acceptance_criteria=excluded.acceptance_criteria,
                    verification_commands=excluded.verification_commands,
                    raw_event=excluded.raw_event,
                    updated_at=excluded.updated_at
                """,
                (
                    finding.dedupe_key,
                    finding.source,
                    finding.repository,
                    finding.issue_number,
                    finding.issue_url,
                    finding.title,
                    finding.body,
                    finding.severity,
                    dumps(finding.labels),
                    dumps(finding.files),
                    dumps(finding.acceptance_criteria),
                    dumps(finding.verification_commands),
                    finding.as_raw_json(),
                    now,
                    now,
                ),
            )
            row = conn.execute(
                "SELECT * FROM work_items WHERE dedupe_key = ?", (finding.dedupe_key,)
            ).fetchone()
        item = self._row_to_work_item(row)
        self.add_audit(item.id, "finding_upserted", "Finding accepted into queue", finding.raw_event)
        return item

    def get(self, item_id: int) -> WorkItem | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM work_items WHERE id = ?", (item_id,)).fetchone()
        return self._row_to_work_item(row) if row else None

    def list_items(self, limit: int = 200) -> list[WorkItem]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM work_items ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [self._row_to_work_item(row) for row in rows]

    def list_by_status(self, statuses: list[str], limit: int = 100) -> list[WorkItem]:
        if not statuses:
            return []
        placeholders = ",".join("?" for _ in statuses)
        with self.connect() as conn:
            rows = conn.execute(
                f"SELECT * FROM work_items WHERE status IN ({placeholders}) ORDER BY id ASC LIMIT ?",
                (*statuses, limit),
            ).fetchall()
        return [self._row_to_work_item(row) for row in rows]

    def update_item(self, item_id: int, **fields: Any) -> WorkItem:
        if not fields:
            item = self.get(item_id)
            if item is None:
                raise KeyError(item_id)
            return item
        fields["updated_at"] = utc_now()
        encoded: dict[str, Any] = {}
        for key, value in fields.items():
            if key in {"labels", "files", "acceptance_criteria", "verification_commands", "pr_urls"}:
                encoded[key] = dumps(value)
            elif key in {"raw_event", "raw_session"}:
                encoded[key] = dumps(value)
            else:
                encoded[key] = value
        assignments = ", ".join(f"{key} = ?" for key in encoded)
        values = list(encoded.values())
        with self.connect() as conn:
            conn.execute(
                f"UPDATE work_items SET {assignments} WHERE id = ?",
                (*values, item_id),
            )
            row = conn.execute("SELECT * FROM work_items WHERE id = ?", (item_id,)).fetchone()
        if row is None:
            raise KeyError(item_id)
        return self._row_to_work_item(row)

    def increment_attempts(self, item_id: int) -> WorkItem:
        with self.connect() as conn:
            conn.execute(
                "UPDATE work_items SET attempts = attempts + 1, updated_at = ? WHERE id = ?",
                (utc_now(), item_id),
            )
            row = conn.execute("SELECT * FROM work_items WHERE id = ?", (item_id,)).fetchone()
        if row is None:
            raise KeyError(item_id)
        return self._row_to_work_item(row)

    def add_audit(
        self,
        work_item_id: int | None,
        event_type: str,
        message: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO audit_events (work_item_id, event_type, message, payload, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (work_item_id, event_type, message, dumps(payload or {}), utc_now()),
            )

    def list_audit(self, work_item_id: int | None = None, limit: int = 100) -> list[dict[str, Any]]:
        where = ""
        params: tuple[Any, ...] = (limit,)
        if work_item_id is not None:
            where = "WHERE work_item_id = ?"
            params = (work_item_id, limit)
        with self.connect() as conn:
            rows = conn.execute(
                f"SELECT * FROM audit_events {where} ORDER BY id DESC LIMIT ?", params
            ).fetchall()
        return [
            {
                "id": row["id"],
                "work_item_id": row["work_item_id"],
                "event_type": row["event_type"],
                "message": row["message"],
                "payload": json.loads(row["payload"] or "{}"),
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def metrics(self) -> dict[str, Any]:
        items = self.list_items(limit=10000)
        counts = Counter(item.status for item in items)
        total = len(items)
        succeeded = counts.get("succeeded", 0)
        failed = counts.get("failed", 0)
        blocked = counts.get("blocked", 0)
        terminal = succeeded + failed + blocked
        pr_count = sum(len(item.pr_urls) for item in items)
        return {
            "total": total,
            "queued": counts.get("queued", 0),
            "running": counts.get("running", 0),
            "succeeded": succeeded,
            "failed": failed,
            "blocked": blocked,
            "terminal": terminal,
            "success_rate": round(succeeded / terminal, 4) if terminal else 0.0,
            "pr_count": pr_count,
            "by_status": dict(counts),
        }

    def _row_to_work_item(self, row: sqlite3.Row) -> WorkItem:
        return WorkItem(
            id=row["id"],
            dedupe_key=row["dedupe_key"],
            source=row["source"],
            repository=row["repository"],
            issue_number=row["issue_number"],
            issue_url=row["issue_url"],
            title=row["title"],
            body=row["body"],
            severity=row["severity"],
            labels=loads_list(row["labels"]),
            files=loads_list(row["files"]),
            acceptance_criteria=loads_list(row["acceptance_criteria"]),
            verification_commands=loads_list(row["verification_commands"]),
            status=row["status"],
            devin_session_id=row["devin_session_id"],
            devin_url=row["devin_url"],
            status_detail=row["status_detail"],
            pr_urls=loads_list(row["pr_urls"]),
            attempts=row["attempts"],
            error=row["error"],
            raw_event=json.loads(row["raw_event"] or "{}"),
            raw_session=json.loads(row["raw_session"] or "{}"),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            started_at=row["started_at"],
            completed_at=row["completed_at"],
        )

