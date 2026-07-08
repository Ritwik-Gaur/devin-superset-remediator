from __future__ import annotations

from app.models import WorkItem


STRUCTURED_OUTPUT_SCHEMA = {
    "type": "object",
    "required": ["summary", "changed_files", "verification", "pull_requests", "risk_notes"],
    "properties": {
        "summary": {"type": "string"},
        "changed_files": {"type": "array", "items": {"type": "string"}},
        "verification": {
            "type": "object",
            "required": ["commands_run", "result"],
            "properties": {
                "commands_run": {"type": "array", "items": {"type": "string"}},
                "result": {"type": "string"},
            },
        },
        "pull_requests": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["url", "state"],
                "properties": {
                    "url": {"type": "string"},
                    "state": {"type": "string"},
                },
            },
        },
        "risk_notes": {"type": "array", "items": {"type": "string"}},
    },
}


def build_remediation_prompt(item: WorkItem) -> str:
    files = "\n".join(f"- {path}" for path in item.files) or "- Discover relevant files"
    acceptance = "\n".join(f"- {criterion}" for criterion in item.acceptance_criteria)
    commands = "\n".join(f"- `{cmd}`" for cmd in item.verification_commands)
    issue_ref = item.issue_url or (
        f"{item.repository} issue #{item.issue_number}" if item.issue_number else item.dedupe_key
    )

    return f"""You are acting as an autonomous coding agent for an engineering maintenance workflow.

Repository: {item.repository}
Work item: {issue_ref}
Severity: {item.severity}
Title: {item.title}

Problem context:
{item.body}

Likely files:
{files}

Acceptance criteria:
{acceptance or "- Preserve existing behavior and keep the remediation narrowly scoped."}

Verification commands to prioritize:
{commands or "- Run the narrowest relevant unit or lint command you can identify."}

Instructions:
- Inspect the repository before editing.
- Create a focused branch for this work item.
- Make the smallest production-quality change that fully remediates the issue.
- Add or update tests where the behavior is not already covered.
- Run targeted verification and summarize exact commands and outcomes.
- Open a pull request back to the repository default branch.
- Mention the original issue in the PR description.
- If the issue is unsafe or too broad, stop and explain what is blocking it instead of guessing.
- Provide final structured output matching the requested schema.
"""

