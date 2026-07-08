from __future__ import annotations

import os
from dataclasses import dataclass


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return int(value)


@dataclass(frozen=True)
class Config:
    app_host: str
    app_port: int
    db_path: str
    trigger_label: str
    max_parallel_sessions: int
    devin_api_key: str | None
    devin_org_id: str | None
    devin_base_url: str
    devin_repo: str | None
    devin_dry_run: bool
    devin_poll_seconds: int
    devin_max_acu_limit: int | None
    github_token: str | None
    github_webhook_secret: str | None
    target_repository: str | None

    @classmethod
    def from_env(cls) -> "Config":
        devin_api_key = os.getenv("DEVIN_API_KEY") or None
        explicit_dry_run = os.getenv("DEVIN_DRY_RUN")
        dry_run_default = not bool(devin_api_key)
        max_acu = os.getenv("DEVIN_MAX_ACU_LIMIT")
        return cls(
            app_host=os.getenv("APP_HOST", "127.0.0.1"),
            app_port=_int_env("APP_PORT", 8080),
            db_path=os.getenv("DB_PATH", ".data/devin_remediator.db"),
            trigger_label=os.getenv("TRIGGER_LABEL", "devin-remediate"),
            max_parallel_sessions=_int_env("MAX_PARALLEL_SESSIONS", 2),
            devin_api_key=devin_api_key,
            devin_org_id=os.getenv("DEVIN_ORG_ID") or None,
            devin_base_url=os.getenv("DEVIN_BASE_URL", "https://api.devin.ai/v3"),
            devin_repo=os.getenv("DEVIN_REPO") or os.getenv("TARGET_REPOSITORY"),
            devin_dry_run=_bool_env("DEVIN_DRY_RUN", dry_run_default)
            if explicit_dry_run is not None
            else dry_run_default,
            devin_poll_seconds=_int_env("DEVIN_POLL_SECONDS", 20),
            devin_max_acu_limit=int(max_acu) if max_acu else None,
            github_token=os.getenv("GITHUB_TOKEN") or None,
            github_webhook_secret=os.getenv("GITHUB_WEBHOOK_SECRET") or None,
            target_repository=os.getenv("TARGET_REPOSITORY") or None,
        )

