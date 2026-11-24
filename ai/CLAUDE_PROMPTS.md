# Claude — kickoff and implementation prompts
## Kickoff
> Read AGENTS.md, docs/01–09, design/DESIGN_SYSTEM.md, backlog/TODO.md and upstream UI standards. Do not implement the entire product. Review PRD for contradictions, identify G0 blockers and propose ADR refinements. Start only FND-01 after owner approves scope: prove Windows native pywebview+React bridge+SQLite+OR-Tools+export+offline package feasibility. Produce version lock decision, minimal testable spike and exact evidence. Never claim Windows tests ran if only on Linux.

## Feature
> Implement [ISSUE_ID] only. Inspect existing repo and prerequisite gates; give a short plan and edge cases. Use existing components/tokens and application services. Add tests for success, failure, stale revision and cancellation as relevant. Verify outputs, run checks, report exact results, update backlog and handoff. No broad refactor.

## UI specialist
> Review [SCREEN] against upstream rules 01–07 and Ocean Ledger. Use mockup as visual direction, not production code. Keep navy nav, tinted surfaces, density, 6–8px radius, centered headers, accessible icon-only actions. Validate modal/focus, dark/light and DPI. Deliver screenshot comparison and list of defects with severity and evidence.
