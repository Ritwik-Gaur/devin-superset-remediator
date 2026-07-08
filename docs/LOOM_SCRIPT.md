# Loom Script — fully scripted, ~5 minutes

Every step is either **DO** (an action, don't narrate it) or **SAY** (read it word for word,
naturally). Practice the DO steps once before recording.

## Before you hit record

Open these tabs in order (Cmd+1 … Cmd+6 jumps between them in Chrome):

1. https://github.com/Ritwik-Gaur/superset/issues
2. http://localhost:8080 (dashboard — should show 2 succeeded, 100% success rate)
3. https://github.com/Ritwik-Gaur/devin-superset-remediator (solution repo README, scrolled to the architecture diagram)
4. https://github.com/Ritwik-Gaur/superset/pull/5 (the utcnow PR, on the "Files changed" view)
5. https://app.devin.ai/sessions/27f4665eb484489a8a72a819069333ea (Devin's work log for PR #5)
6. Terminal, `cd ~/cognition-test`, font size 16+

Mic check: record 10 seconds in Loom, play it back. The trigger step starts a real Devin
session — you only get one clean take of it, so do this check first.

---

## 0:00 — The problem  (Tab 1: issues list)

**DO:** Start on the issues tab. Move your cursor slowly over the three issue titles as you talk.

**SAY:**
> "Hi, I'm Ritwik. This is an event-driven automation I built on the Devin API, running
> against a fork of Apache Superset — a million-line Python and TypeScript codebase.
>
> The problem it solves is maintenance drag. Scanners and engineers constantly find small
> issues like these three: a `shell=True` subprocess call, twenty-two call sites of a
> deprecated datetime API, and an unimplemented API filter. Each one is too small to
> schedule and too nuanced for a codemod — so they pile up, and senior engineers become
> the cleanup queue. My system turns each finding into a work order that Devin executes
> autonomously, end to end."

## 0:45 — Live trigger  (Tab 6: terminal → Tab 2: dashboard → Tab 1: issue #3)

**SAY (while switching to the terminal):**
> "Let me trigger one live. The event source is a GitHub issue getting a
> `devin-remediate` label. In production that arrives as a GitHub webhook; locally I
> replay the exact same payload, since there's no public URL on my laptop."

**DO:** Type and run:

```bash
python3 scripts/trigger_issue.py 3
```

**DO:** Switch to Tab 2 (dashboard). Point at the new job 3 row — status `running`, with a
Devin session link.

**SAY:**
> "Within seconds the orchestrator has deduped the event, queued a work item, and started
> a real Devin session — there's the session link on the dashboard."

**DO:** Switch to Tab 1, open issue #3, scroll to the bottom comment.

**SAY:**
> "And it's posted a comment back on the GitHub issue with the session URL, so the audit
> trail lives where engineers already work."

## 1:45 — Architecture  (Tab 3: solution repo README)

**DO:** Switch to Tab 3, scrolled to the architecture diagram. Trace the flow with your cursor
as you talk: scanner/issue → webhook → queue → orchestrator → Devin → PRs.

**SAY:**
> "Here's the shape of the system. The key decision: Devin is the execution primitive, not
> a helper call. My service is a thin control plane — it owns intake, dedup, a SQLite work
> queue, a concurrency cap, and session lifecycle. Devin owns everything that needs
> engineering judgment: investigating the repo, writing the patch, running the tests,
> opening the PR.
>
> Each session gets a scoped prompt with the issue's acceptance criteria and verification
> commands, an ACU budget cap, and a structured output schema — so Devin reports back
> machine-readable results: what changed, what was verified, and the PR URL. The
> orchestrator polls session state and maps every terminal state, including quota
> suspensions, to a status a human can act on."

## 2:45 — The results  (Tab 5: Devin session → Tab 4: PR #5)

**DO:** Switch to Tab 5, scroll slowly through Devin's work log.

**SAY:**
> "Here's Devin actually doing the work on the datetime issue earlier — reading the scoped
> files, making the change, running the tests it was told to prioritize."

**DO:** Switch to Tab 4, the PR's "Files changed" view. Scroll through the diff.

**SAY:**
> "And here's the pull request it opened: fifty-nine additions across exactly the three
> files in scope, including updated tests. It stayed inside the acceptance criteria — no
> drive-by refactoring. Both completed issues got PRs like this, with completion comments
> linking everything together."

## 3:30 — Observability  (Tab 2: dashboard, then terminal)

**DO:** Switch to Tab 2. Point at the metric cards.

**SAY:**
> "For an engineering leader, the question is 'how do I know this is working?' The
> dashboard tracks queued, running, succeeded, failed, and blocked, plus every PR."

**DO:** Switch to Tab 6 and run:

```bash
curl -s http://localhost:8080/metrics
```

**SAY:**
> "The same numbers are exposed as Prometheus metrics — success rate, throughput, PR
> count — so this drops into existing monitoring, and you can put a number on remediated
> issues per week versus engineer-hours spent."

## 4:10 — Why Devin, and next steps  (stay wherever you are)

**SAY:**
> "Why is Devin the right primitive here? A scanner can find `shell=True`. Dependabot can
> bump a version. But neither can navigate a codebase this size, choose the narrowest safe
> patch, update the tests, verify, and open a coherent PR. That gap is exactly why this
> backlog exists — and Devin closes it. The label is the safety valve: humans decide what's
> safe to delegate, the system does the rest.
>
> In a real engagement I'd wire this to the customer's scanner and GitHub org, start with
> low-risk finding classes under a tight ACU cap, add Slack escalation for blocked
> sessions, and report weekly throughput against review time saved. Thanks for watching."

**DO:** Stop recording.

---

## If something goes wrong

- **Trigger command errors:** stay calm, cut, fix off-camera, re-record from the 0:45 beat.
- **Dashboard doesn't show job 3 yet:** it auto-refreshes every 10 seconds — just keep
  talking for one beat, it will appear.
- **Flubbed a line:** Loom lets you trim; or just restate the sentence and trim later.
