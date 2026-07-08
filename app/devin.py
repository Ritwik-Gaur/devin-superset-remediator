from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any
from uuid import uuid4

from app.config import Config
from app.models import WorkItem
from app.prompts import STRUCTURED_OUTPUT_SCHEMA, build_remediation_prompt


class DevinAPIError(RuntimeError):
    pass


class DevinClient:
    def __init__(self, config: Config) -> None:
        self.config = config

    @property
    def dry_run(self) -> bool:
        return self.config.devin_dry_run

    def create_session(self, item: WorkItem) -> dict[str, Any]:
        if self.dry_run:
            session_id = f"devin-dry-{uuid4().hex[:12]}"
            return {
                "session_id": session_id,
                "url": f"https://app.devin.ai/sessions/{session_id}",
                "status": "running",
                "status_detail": "working",
                "pull_requests": [],
                "created_at": int(time.time()),
                "dry_run": True,
            }

        if not self.config.devin_api_key or not self.config.devin_org_id:
            raise DevinAPIError("DEVIN_API_KEY and DEVIN_ORG_ID are required for live mode")

        payload: dict[str, Any] = {
            "prompt": build_remediation_prompt(item),
            "title": f"Superset remediation: {item.title}"[:120],
            "tags": ["superset-remediation", item.severity, f"work-item-{item.id}"],
            "structured_output_required": True,
            "structured_output_schema": STRUCTURED_OUTPUT_SCHEMA,
        }
        if self.config.devin_repo:
            payload["repos"] = [self.config.devin_repo]
        if self.config.devin_max_acu_limit:
            payload["max_acu_limit"] = self.config.devin_max_acu_limit

        return self._request(
            "POST",
            f"/organizations/{self.config.devin_org_id}/sessions",
            payload=payload,
        )

    def get_session(self, session_id: str) -> dict[str, Any]:
        if self.dry_run:
            return {
                "session_id": session_id,
                "url": f"https://app.devin.ai/sessions/{session_id}",
                "status": "running",
                "status_detail": "working",
                "pull_requests": [],
                "dry_run": True,
            }
        return self._request(
            "GET",
            f"/organizations/{self.config.devin_org_id}/sessions/{session_id}",
        )

    def list_messages(self, session_id: str, first: int = 100) -> dict[str, Any]:
        if self.dry_run:
            return {
                "items": [
                    {
                        "event_id": "dry-run-1",
                        "created_at": int(time.time()),
                        "message": "Dry-run Devin session is simulating code investigation.",
                    }
                ],
                "has_next_page": False,
                "end_cursor": None,
                "total": 1,
            }
        query = urllib.parse.urlencode({"first": first})
        return self._request(
            "GET",
            f"/organizations/{self.config.devin_org_id}/sessions/{session_id}/messages?{query}",
        )

    def org_session_metrics(self, time_after: int, time_before: int) -> dict[str, Any]:
        if self.dry_run:
            return {}
        query = urllib.parse.urlencode(
            {"time_after": time_after, "time_before": time_before}
        )
        return self._request(
            "GET",
            f"/organizations/{self.config.devin_org_id}/metrics/sessions?{query}",
        )

    def org_consumption_daily(self, time_after: int | None = None) -> dict[str, Any]:
        if self.dry_run:
            return {}
        query = ""
        if time_after:
            query = "?" + urllib.parse.urlencode({"time_after": time_after})
        return self._request(
            "GET",
            f"/organizations/{self.config.devin_org_id}/consumption/daily{query}",
        )

    def _request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        headers = {
            "Authorization": f"Bearer {self.config.devin_api_key}",
            "Accept": "application/json",
        }
        if payload is not None:
            headers["Content-Type"] = "application/json"
        url = f"{self.config.devin_base_url.rstrip('/')}{path}"
        request = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                raw = response.read().decode("utf-8")
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise DevinAPIError(f"Devin API {method} {path} failed: {exc.code} {detail}") from exc
        except urllib.error.URLError as exc:
            raise DevinAPIError(f"Devin API {method} {path} failed: {exc}") from exc

