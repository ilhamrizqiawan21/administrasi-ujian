# Gemini — independent validation prompts
## QA review
> Review [ISSUE_ID] and current diff; read AGENTS and corresponding docs. Find concrete failures with file/line evidence and test reproduction. Focus on cross-jenjang, offline, corrupted imports/templates/backups, permissions, timezone intervals, keyboard/contrast and native Windows packaging. Do not implement fixes until scope assigned. Rank blocker/high/medium/low and state unknowns.

## Visual review
> Inspect actual screenshots for desktop 1366×768, narrow, dark/light; compare upstream standards and design system. Check sidebar precision, contrast, spacing, headers centered, action icons, centered modals and overflow. No decorative redesign unless requested. Supply concise defect list and suggested fix per component.

## Test coverage
> Write tests only for [ISSUE_ID] in separate branch, using synthetic fixtures and independent expected outputs. Check existing tests first. Verify failure on known defect and success after fix. Report command results and handoff.
