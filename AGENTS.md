# Ujian Cerdas — common agent instructions
Read README, PRD, relevant architecture/database/algorithm/document spec, design system, TODO and testing strategy before editing. For UI read `design/COMPONENT_SPEC.md`, `backlog/UI_COMPONENT_TODO.md` and inspect `design/mockup.html` / `design/visual-index.html`. For UI read upstream [standar-ui-project](https://github.com/ilhamrizqiawan21/standar-ui-project/tree/main/admin-panel-standards) rules 01–07 and `.agents/skills/admin-panel-ui/SKILL.md`; project override is documented in design/DESIGN_SYSTEM.md. Do not silently rewrite product requirements or global standards.

## Workflow
1. Select one issue ID, identify dependencies, inspect current code and tests; report gaps and plan before implementation. Ask owner only for consequential unresolved decisions; state assumptions otherwise.
2. Implement smallest complete vertical slice with typed contract, transaction, validation, UI where applicable and tests. Do not add dependencies without reason and compatibility/license check. Use existing shared UI. Avoid generated boilerplate, speculative abstractions and arbitrary CSS. No internet/CDN/AI runtime dependencies.
3. Validate: run relevant pytest, frontend lint/typecheck/Vitest/build, browser and native Windows test where applicable. Inspect actual PDFs and screenshots. Report exact commands and failures, never claim unrun tests passed. Do not mark issue complete if acceptance not met. Update TODO and CSV consistently, CHANGELOG, decision log, migration notes and risk log.
4. Use branch `feat/<issue>-short-name`, small commits, PR summary with ID, tests, screenshots, rollback notes. Do not push to main or merge without owner approval. Do not force-push, delete data, change pricing/licence policy or migrate production without approval. No real student records, keys, secrets or production db in prompts/repo.

## Invariants
Single local writer, institution/event scope, immutable published versions, independent solver validation, ID strings, integer IDR, explicit approval, no fake data in prod, no silent hard-rule relaxation, atomic outputs and backups. Design standard: semantic tokens, 6–8 radius, 32/36/40 buttons, centered header, icon-only actions, centered CRUD and confirm dialogs, dark/light, breadcrumb, responsive hamburger, no decorative gradients/glass/emoji, minimal guidance.

## Handoff template
Issue / scope / changed files / decisions / migration & compatibility / test commands & results / manual review evidence / known gaps / next issue. Keep `ai/HANDOFF.md` updated. If agent disagrees with architecture, propose an ADR, do not implement it covertly.
