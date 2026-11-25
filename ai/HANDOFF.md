# Agent handoff
Status: FND-02..09, UI-01..12, CFG-01..06, MST-01..08, EVT-01..07, SES-01..07, ROM-01..08, SCH-01..08, COM-01..06, TSK-01..05, EXP-01..06, OPS-01..08, TPL-01..06, DOC-01..09, FIN-01..08, and LPJ-01..05 completed; FND-01 Windows x64 native WebView2 + PyInstaller smoke and TPL-07 (P2 Visual canvas) pending.
- Current gate: G5 Finance & Reporting (LPJ complete); next: `ARC-01`..`ARC-04` (Archive).
- Owner decisions: price Rp150.000; offline desktop; Python backend + React/TS with PyWebView; no plain-white-dominant UI; modern and anti-slop UI direction.
- Technical decisions:
  - Alembic migration `0015_lpj_tables`: `lpj_versions`, `lpj_evaluations`, `lpj_attachments`.
  - `LpjService`: 15 structured narrative sections separated from readonly `snapshot_json` derived totals, evaluation links to `incidents`, attachment existence & explicit exclusion gate, finalization policy blockers + auto-forked draft revision on editing `final` versions, and multi-page PDF/DOCX export via `DocumentRun`.
  - Frontend: `LpjPage` (`frontend/src/features/lpj/`) wired into `AppShell` (`/lpj`).
- Tests run:
  - `uv run ruff check .` & `uv run ruff format --check .`
  - `uv run mypy app backend tests`
  - `uv run pytest -v`
  - `uv run python -m app.main --self-test`
  - `cd frontend && npm run lint && npm run typecheck && npx vitest run src/lpj.test.tsx && npm run build`
- Known gaps:
  - Native Windows x64 `pywebview` (EdgeChromium/WebView2) window launch and `PyInstaller --onedir` remain to be executed on Windows x64.
- Next task: `ARC-01`..`ARC-04` (Archive).
