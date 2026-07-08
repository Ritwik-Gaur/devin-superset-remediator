from __future__ import annotations

from pathlib import Path
from typing import Any


def scan_superset(repo_path: str, repository: str) -> dict[str, Any]:
    root = Path(repo_path)
    findings: list[dict[str, Any]] = []

    bash_mock = root / "tests/unit_tests/fixtures/bash_mock.py"
    if bash_mock.exists() and "shell=True" in bash_mock.read_text(encoding="utf-8"):
        findings.append(
            {
                "id": "SEC-001-shell-true-bash-mock",
                "source": "local_scan",
                "repository": repository,
                "severity": "medium",
                "title": "Replace shell=True in BashMock release test helper",
                "body": (
                    "Static analysis flags the release test helper for invoking a "
                    "constructed shell command with shell=True. The helper can pass "
                    "argv directly to subprocess.run and preserve dry-run behavior."
                ),
                "labels": ["devin-remediate", "security", "python"],
                "files": ["tests/unit_tests/fixtures/bash_mock.py"],
                "acceptance_criteria": [
                    "Remove shell=True from BashMock.tag_latest_release.",
                    "Pass tag_latest_release.sh arguments as an argv list.",
                    "Keep TEST_ENV behavior and existing return semantics.",
                ],
                "verification_commands": [
                    "python -m pytest tests/unit_tests/fixtures -q",
                    "python -m pytest tests/unit_tests -k tag_latest_release -q",
                ],
            }
        )

    report_files = [
        root / "superset/commands/report/execute.py",
        root / "superset/commands/report/log_prune.py",
    ]
    utcnow_hits = [
        str(path.relative_to(root))
        for path in report_files
        if path.exists() and "datetime.utcnow" in path.read_text(encoding="utf-8")
    ]
    if utcnow_hits:
        findings.append(
            {
                "id": "PY312-001-report-utcnow",
                "source": "local_scan",
                "repository": repository,
                "severity": "medium",
                "title": "Remove deprecated datetime.utcnow from report scheduling hot paths",
                "body": (
                    "Superset declares Python 3.12 support. datetime.utcnow() is "
                    "deprecated and report scheduling has many direct call sites. "
                    "Introduce or reuse a UTC clock helper with naive-UTC compatibility "
                    "where database columns still expect naive DateTime values."
                ),
                "labels": ["devin-remediate", "python-3.12", "code-quality"],
                "files": utcnow_hits,
                "acceptance_criteria": [
                    "Replace direct datetime.utcnow calls in the scoped report command files.",
                    "Preserve naive UTC values where existing SQLAlchemy models expect them.",
                    "Add or update focused tests for the clock helper behavior.",
                ],
                "verification_commands": [
                    "python -m pytest tests/unit_tests/commands/report -q",
                    "python -m pytest tests/unit_tests/commands/logs -q",
                ],
            }
        )

    extensions_api = root / "superset/extensions/api.py"
    if extensions_api.exists() and "TODO: Support the q parameter" in extensions_api.read_text(encoding="utf-8"):
        findings.append(
            {
                "id": "API-001-extensions-q-filter",
                "source": "local_scan",
                "repository": repository,
                "severity": "low",
                "title": "Implement q filtering for ExtensionsRestApi.get_list",
                "body": (
                    "ExtensionsRestApi.get_list advertises a TODO for the FAB q "
                    "parameter but currently returns every extension. Implement a "
                    "minimal, documented filter path and tests so clients can query "
                    "by publisher/name without client-side scanning."
                ),
                "labels": ["devin-remediate", "api", "code-quality"],
                "files": ["superset/extensions/api.py"],
                "acceptance_criteria": [
                    "Parse q safely using Superset/FAB conventions already used by APIs.",
                    "Support filtering by extension publisher and name.",
                    "Add unit tests covering unfiltered, filtered, and invalid q behavior.",
                ],
                "verification_commands": [
                    "python -m pytest tests/unit_tests/extensions -q",
                ],
            }
        )

    return {"repository": repository, "findings": findings}

