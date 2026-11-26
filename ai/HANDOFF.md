# Agent handoff
Status: FND-02..09, UI-01..12, CFG-01..06, MST-01..08, EVT-01..07, SES-01..07, ROM-01..08, SCH-01..08, COM-01..06, TSK-01..05, EXP-01..06, OPS-01..08, TPL-01..06, DOC-01..09, FIN-01..08, LPJ-01..05, ARC-01..04, and BAK-01..04 completed; FND-01 Windows x64 native WebView2 + PyInstaller smoke and TPL-07 (P2 Visual canvas) pending.
- Current gate: G6 Backup & Recovery complete; next: `LIC-01`..`LIC-03` (Commercial licensing).
- Owner decisions: price Rp150.000; offline desktop; Python backend + React/TS with PyWebView; no plain-white-dominant UI; modern and anti-slop UI direction.
- Technical decisions:
  - Alembic migration `0017_bak_tables`: `backup_records`, `backup_schedule_settings`.
  - `BakService`: SQLite backup API + asset manifest atomic ZIP (`bak.create`, `bak.verify`), scheduled startup/close backup with visible failures and safe retention that never deletes the last good backup (`bak.schedule.*`), staged restore wizard with pre-restore backup and corrupt-ZIP rejection (`bak.restore.*`), and crash recovery diagnostics/cleanup for interrupted jobs and `.tmp_*` files (`bak.recovery.*`).
  - Frontend: `BackupPage` (`frontend/src/features/bak/`) wired into `AppShell` (`/backup`).
- Tests run:
  - `uv run ruff check .` & `uv run ruff format --check .`
  - `uv run mypy app backend tests`
  - `uv run pytest -q` (68 passed)
  - `XDG_DATA_HOME=/tmp/ujian-cerdas-selftest uv run python -m app.main --self-test`
  - `npm --prefix frontend run lint`, `npm --prefix frontend run typecheck`, `npm --prefix frontend run test -- src/bak.test.tsx`, `npm --prefix frontend run build`
- Known gaps:
  - Native Windows x64 `pywebview` (EdgeChromium/WebView2) window launch and `PyInstaller --onedir` remain to be executed on Windows x64.
- Next task: `LIC-01`..`LIC-03` (Commercial licensing).
