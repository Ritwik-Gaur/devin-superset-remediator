from __future__ import annotations

import html
import json
import signal
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from app.config import Config
from app.github import finding_from_github_issue_event, verify_signature
from app.models import IssueFinding
from app.orchestrator import Orchestrator
from app.storage import Store


class AppContext:
    def __init__(self, config: Config) -> None:
        self.config = config
        self.store = Store(config.db_path)
        self.orchestrator = Orchestrator(config, self.store)


def make_handler(ctx: AppContext) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server_version = "DevinRemediator/1.0"

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path == "/":
                self._send_html(render_dashboard(ctx))
            elif parsed.path == "/healthz":
                self._send_json({"ok": True, "dry_run": ctx.config.devin_dry_run})
            elif parsed.path == "/metrics":
                self._send_text(render_prometheus(ctx.store.metrics()))
            elif parsed.path == "/api/jobs":
                self._send_json([item.to_dict() for item in ctx.store.list_items()])
            elif parsed.path.startswith("/api/jobs/"):
                self._handle_get_job(parsed.path)
            else:
                self._send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)

        def do_POST(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path == "/webhooks/github":
                self._handle_github_webhook()
            elif parsed.path == "/events/scan":
                self._handle_scan_event()
            elif parsed.path == "/simulate":
                self._handle_simulate()
            elif parsed.path == "/tick":
                self._send_json(ctx.orchestrator.tick())
            else:
                self._send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)

        def log_message(self, fmt: str, *args: Any) -> None:
            print(f"{self.address_string()} - {fmt % args}")

        def _handle_get_job(self, path: str) -> None:
            try:
                item_id = int(path.rstrip("/").split("/")[-1])
            except ValueError:
                self._send_json({"error": "invalid job id"}, HTTPStatus.BAD_REQUEST)
                return
            item = ctx.store.get(item_id)
            if item is None:
                self._send_json({"error": "job not found"}, HTTPStatus.NOT_FOUND)
                return
            self._send_json(
                {
                    "job": item.to_dict(),
                    "audit": ctx.store.list_audit(work_item_id=item.id, limit=100),
                }
            )

        def _handle_github_webhook(self) -> None:
            raw = self._read_body()
            signature = self.headers.get("X-Hub-Signature-256")
            if not verify_signature(ctx.config.github_webhook_secret, raw, signature):
                self._send_json({"error": "invalid signature"}, HTTPStatus.UNAUTHORIZED)
                return
            try:
                payload = json.loads(raw.decode("utf-8"))
            except json.JSONDecodeError:
                self._send_json({"error": "invalid json"}, HTTPStatus.BAD_REQUEST)
                return
            finding = finding_from_github_issue_event(payload, ctx.config.trigger_label)
            if finding is None:
                self._send_json({"accepted": False, "reason": "event ignored"}, HTTPStatus.ACCEPTED)
                return
            item = ctx.orchestrator.accept_finding(finding)
            self._send_json({"accepted": True, "job": item.to_dict()})

        def _handle_scan_event(self) -> None:
            payload = self._json_body()
            if payload is None:
                return
            findings = payload.get("findings", [])
            accepted = []
            for raw_finding in findings:
                finding = IssueFinding.from_dict(raw_finding)
                accepted.append(ctx.orchestrator.accept_finding(finding).to_dict())
            tick = ctx.orchestrator.tick()
            self._send_json({"accepted": accepted, "tick": tick})

        def _handle_simulate(self) -> None:
            root = Path(__file__).resolve().parents[1]
            plan = json.loads((root / "issues/superset-remediation-plan.json").read_text())
            accepted = []
            for raw_finding in plan["findings"]:
                raw = {**raw_finding, "repository": ctx.config.target_repository or plan["repository"]}
                accepted.append(ctx.orchestrator.accept_finding(IssueFinding.from_dict(raw)).to_dict())
            tick = ctx.orchestrator.tick()
            self._send_json({"accepted": accepted, "tick": tick, "dry_run": ctx.config.devin_dry_run})

        def _json_body(self) -> dict[str, Any] | None:
            raw = self._read_body()
            try:
                payload = json.loads(raw.decode("utf-8"))
            except json.JSONDecodeError:
                self._send_json({"error": "invalid json"}, HTTPStatus.BAD_REQUEST)
                return None
            return payload

        def _read_body(self) -> bytes:
            length = int(self.headers.get("Content-Length", "0"))
            return self.rfile.read(length)

        def _send_json(self, payload: Any, status: HTTPStatus = HTTPStatus.OK) -> None:
            body = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_html(self, payload: str, status: HTTPStatus = HTTPStatus.OK) -> None:
            body = payload.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_text(self, payload: str, status: HTTPStatus = HTTPStatus.OK) -> None:
            body = payload.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return Handler


def render_dashboard(ctx: AppContext) -> str:
    metrics = ctx.store.metrics()
    jobs = ctx.store.list_items(limit=100)
    rows = "\n".join(render_job_row(job.to_dict()) for job in jobs)
    mode = "dry-run" if ctx.config.devin_dry_run else "live Devin API"
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Devin Superset Remediation Conveyor</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f7f8fb;
      --ink: #17202a;
      --muted: #5f6b7a;
      --line: #d9dee8;
      --panel: #ffffff;
      --accent: #0b6bcb;
      --ok: #127c43;
      --warn: #946200;
      --bad: #b42318;
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: var(--bg); color: var(--ink); }}
    header {{ padding: 28px 32px 18px; border-bottom: 1px solid var(--line); background: var(--panel); }}
    h1 {{ margin: 0 0 8px; font-size: 28px; line-height: 1.2; letter-spacing: 0; }}
    p {{ margin: 0; color: var(--muted); line-height: 1.5; }}
    main {{ padding: 24px 32px 40px; max-width: 1320px; margin: 0 auto; }}
    .metrics {{ display: grid; grid-template-columns: repeat(6, minmax(120px, 1fr)); gap: 12px; margin-bottom: 22px; }}
    .metric {{ background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 14px; }}
    .metric span {{ display: block; color: var(--muted); font-size: 12px; text-transform: uppercase; }}
    .metric strong {{ display: block; font-size: 26px; margin-top: 6px; }}
    table {{ width: 100%; border-collapse: collapse; background: var(--panel); border: 1px solid var(--line); border-radius: 8px; overflow: hidden; }}
    th, td {{ padding: 12px; border-bottom: 1px solid var(--line); text-align: left; vertical-align: top; font-size: 14px; }}
    th {{ color: var(--muted); font-size: 12px; text-transform: uppercase; background: #eef2f7; }}
    tr:last-child td {{ border-bottom: none; }}
    a {{ color: var(--accent); text-decoration: none; }}
    .badge {{ display: inline-block; border-radius: 999px; padding: 3px 8px; font-size: 12px; background: #e8edf5; color: var(--ink); }}
    .succeeded {{ background: #e7f6ec; color: var(--ok); }}
    .running {{ background: #e7f0ff; color: var(--accent); }}
    .queued {{ background: #fff7df; color: var(--warn); }}
    .failed, .blocked {{ background: #fff0ed; color: var(--bad); }}
    code {{ background: #eef2f7; border-radius: 4px; padding: 2px 5px; }}
    @media (max-width: 900px) {{ .metrics {{ grid-template-columns: repeat(2, 1fr); }} main, header {{ padding-left: 18px; padding-right: 18px; }} table {{ display: block; overflow-x: auto; }} }}
  </style>
</head>
<body>
  <header>
    <h1>Devin Superset Remediation Conveyor</h1>
    <p>Mode: <code>{html.escape(mode)}</code>. Event-driven queue for Superset issues, Devin sessions, PR links, and leadership metrics.</p>
  </header>
  <main>
    <section class="metrics">
      {metric_card("Total", metrics["total"])}
      {metric_card("Queued", metrics["queued"])}
      {metric_card("Running", metrics["running"])}
      {metric_card("Succeeded", metrics["succeeded"])}
      {metric_card("Failed", metrics["failed"])}
      {metric_card("PRs", metrics["pr_count"])}
    </section>
    <table>
      <thead><tr><th>ID</th><th>Status</th><th>Issue</th><th>Devin</th><th>Pull Requests</th><th>Updated</th></tr></thead>
      <tbody>{rows or '<tr><td colspan="6">No work items yet. POST /simulate to seed the Superset demo.</td></tr>'}</tbody>
    </table>
  </main>
</body>
</html>"""


def metric_card(label: str, value: Any) -> str:
    return f'<div class="metric"><span>{html.escape(label)}</span><strong>{html.escape(str(value))}</strong></div>'


def render_job_row(job: dict[str, Any]) -> str:
    status = html.escape(job["status"])
    issue = html.escape(job["title"])
    issue_link = job.get("issue_url")
    if issue_link:
        issue_html = f'<a href="{html.escape(issue_link)}">{issue}</a>'
    else:
        issue_html = issue
    devin = job.get("devin_url")
    devin_html = f'<a href="{html.escape(devin)}">{html.escape(job.get("devin_session_id") or "session")}</a>' if devin else ""
    prs = "<br>".join(
        f'<a href="{html.escape(url)}">{html.escape(url)}</a>' for url in job.get("pr_urls", [])
    )
    return (
        "<tr>"
        f"<td>{job['id']}</td>"
        f'<td><span class="badge {status}">{status}</span><br>{html.escape(str(job.get("status_detail") or ""))}</td>'
        f"<td>{issue_html}<br><code>{html.escape(job['repository'])}</code></td>"
        f"<td>{devin_html}</td>"
        f"<td>{prs}</td>"
        f"<td>{html.escape(job['updated_at'])}</td>"
        "</tr>"
    )


def render_prometheus(metrics: dict[str, Any]) -> str:
    lines = [
        "# HELP devin_remediator_work_items_total Total work items by status.",
        "# TYPE devin_remediator_work_items_total gauge",
    ]
    for status, count in metrics["by_status"].items():
        lines.append(f'devin_remediator_work_items_total{{status="{status}"}} {count}')
    lines.extend(
        [
            "# HELP devin_remediator_success_rate Terminal work-item success rate.",
            "# TYPE devin_remediator_success_rate gauge",
            f"devin_remediator_success_rate {metrics['success_rate']}",
            "# HELP devin_remediator_pull_requests_total Pull requests linked by Devin sessions.",
            "# TYPE devin_remediator_pull_requests_total gauge",
            f"devin_remediator_pull_requests_total {metrics['pr_count']}",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    config = Config.from_env()
    ctx = AppContext(config)
    stop_event = threading.Event()
    worker = threading.Thread(target=ctx.orchestrator.run_forever, args=(stop_event,), daemon=True)
    worker.start()

    server = ThreadingHTTPServer((config.app_host, config.app_port), make_handler(ctx))

    def shutdown(signum: int, frame: Any) -> None:
        stop_event.set()
        server.shutdown()

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)
    print(
        f"Devin remediator listening on http://{config.app_host}:{config.app_port} "
        f"(dry_run={config.devin_dry_run})"
    )
    server.serve_forever()

