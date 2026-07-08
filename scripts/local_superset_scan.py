#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.scanner import scan_superset


def main() -> int:
    repo_path = sys.argv[1] if len(sys.argv) > 1 else "superset-fork"
    repository = os.getenv("TARGET_REPOSITORY", "Ritwik-Gaur/superset")
    print(json.dumps(scan_superset(repo_path, repository), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
