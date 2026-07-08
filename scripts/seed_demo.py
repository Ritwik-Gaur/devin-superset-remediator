#!/usr/bin/env python3
from __future__ import annotations

import json
import urllib.request


def main() -> int:
    request = urllib.request.Request(
        "http://127.0.0.1:8080/simulate",
        data=b"{}",
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        print(json.dumps(json.loads(response.read().decode("utf-8")), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

