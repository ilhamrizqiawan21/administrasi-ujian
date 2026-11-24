# Codex — execution and reviewer prompts
## Kickoff
> Read AGENTS.md, docs/02-ARCHITECTURE.md, docs/03-DATABASE.md, docs/06-TESTING.md and backlog/TODO.md. Inspect branch status and handoff. Choose only [ISSUE_ID], do not implement other milestones. Confirm dependency readiness. Implement production code with tests, run available checks, show exact diff summary and unresolved risks; do not push main. If Windows unavailable, leave native tests pending explicitly.

## Hard logic
> Implement [ISSUE_ID] using documented invariants. Start by writing independent validator and failing boundary tests; then solver/service. Include infeasible/timeout/locked/stale revisions. Distinguish FEASIBLE from OPTIMAL. For financial logic use integer IDR and idempotency source keys. Avoid speculative abstractions. Report test results and audit impact.

## PR review
> Review diff against AGENTS, PRD, and issue acceptance. Prioritize data loss, security, incorrect scope, race conditions, incorrect solver constraints and migration failure. Provide file/line evidence, reproducible failing case and smallest fix; no style-only noise. Do not approve if core invariant fails.
