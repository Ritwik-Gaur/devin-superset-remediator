from __future__ import annotations

import tempfile
import time
import unittest

from app.config import Config
from app.models import IssueFinding
from app.orchestrator import Orchestrator
from app.storage import Store


def test_config(db_path: str) -> Config:
    return Config(
        app_host="127.0.0.1",
        app_port=8080,
        db_path=db_path,
        trigger_label="devin-remediate",
        max_parallel_sessions=2,
        devin_api_key=None,
        devin_org_id=None,
        devin_base_url="https://api.devin.ai/v3",
        devin_repo="Ritwik-Gaur/superset",
        devin_dry_run=True,
        devin_poll_seconds=1,
        devin_max_acu_limit=8,
        github_token=None,
        github_webhook_secret=None,
        target_repository="Ritwik-Gaur/superset",
    )


class OrchestratorTests(unittest.TestCase):
    def test_dry_run_lifecycle_links_pr(self) -> None:
        with tempfile.NamedTemporaryFile() as db:
            config = test_config(db.name)
            store = Store(config.db_path)
            orchestrator = Orchestrator(config, store)
            item = orchestrator.accept_finding(
                IssueFinding(
                    dedupe_key="test:1",
                    source="unit",
                    repository="Ritwik-Gaur/superset",
                    title="Fix thing",
                    body="Body",
                    labels=["devin-remediate"],
                    files=["file.py"],
                    verification_commands=["pytest file.py"],
                )
            )
            self.assertEqual(item.status, "queued")
            first_tick = orchestrator.tick()
            self.assertEqual(first_tick["started"], [item.id])
            running = store.get(item.id)
            self.assertIsNotNone(running)
            self.assertEqual(running.status, "running")
            time.sleep(2.1)
            orchestrator.tick()
            done = store.get(item.id)
            self.assertIsNotNone(done)
            self.assertEqual(done.status, "succeeded")
            self.assertEqual(len(done.pr_urls), 1)


if __name__ == "__main__":
    unittest.main()

