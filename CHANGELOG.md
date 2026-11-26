# Changelog
## 0.1.0-bak — 2026-11-26
- **BAK-01..BAK-04**: Implemented Backup & Recovery vertical slice:
  - Alembic migration `0017_bak_tables` (`backup_records`, `backup_schedule_settings`).
  - `backend/modules/bak/{models,schemas,repository,service}.py` and bridge methods `bak.*`.
  - `frontend/src/features/bak/{types.ts,BackupPage.tsx}` wired into `App.tsx` (`/backup`).
  - Verified with `ruff`, `mypy --strict`, `pytest` (68/68), `eslint`, `tsc`, `vitest` (`bak.test.tsx`), and `vite build`.

## 0.1.0-arc — 2026-11-26
- **ARC-01..ARC-04**: Implemented Archive, Package, Duplicate & Retention vertical slice:
  - Alembic migration `0016_arc_tables` (`archive_packages`, `retention_backups`).
  - `backend/modules/arc/{models,schemas,repository,service}.py` and bridge methods `arc.*`.
  - `frontend/src/features/arc/{types.ts,ArchivePage.tsx}` wired into `App.tsx` (`/archive`).
  - Verified with `ruff`, `mypy --strict`, `pytest` (64/64), `eslint`, `tsc`, `vitest` (`arc.test.tsx`), and `vite build`.

## 0.1.0-lpj — 2026-11-25
- **LPJ-01..LPJ-05**: Implemented Reporting & LPJ vertical slice:
  - Alembic migration `0015_lpj_tables` (`lpj_versions`, `lpj_evaluations`, `lpj_attachments`).
  - `backend/modules/lpj/{models,schemas,repository,service}.py` and bridge methods `lpj.*`.
  - `frontend/src/features/lpj/{types.ts,LpjPage.tsx}` wired into `App.tsx` (`/lpj`).
  - Verified with `ruff`, `mypy --strict`, `pytest`, `eslint`, `tsc`, `vitest` (`lpj.test.tsx`), and `vite build`.

## 0.1.0-fin — 2026-11-25
- **FIN-01..FIN-08**: Implemented Budget, Finance & Honorarium vertical slice:
  - Alembic migration `0014_fin_tables` (`budget_categories`, `budget_versions`, `budget_lines`, `ledger_entries`, `honor_rules`, `honor_lines`).
  - `backend/modules/fin/{models,schemas,repository,service}.py` and bridge methods `fin.*`.
  - `frontend/src/features/fin/{types.ts,FinancePage.tsx}` wired into `App.tsx` (`/finance`).
  - Verified with `ruff`, `mypy --strict`, `pytest` (57/57), `eslint`, `tsc`, `vitest` (`fin.test.tsx`), and `vite build`.

## 0.1.0-doc — 2026-11-25
- **DOC-01..DOC-09**: Implemented Document Engine vertical slice:
  - Alembic migration `0013_doc_tables` (`document_runs`, `document_numbers`).
  - `backend/modules/doc/{models,schemas,repository,renderers,service}.py` and bridge methods `doc.*`.
  - `frontend/src/features/doc/{types.ts,DocumentCenterPage.tsx}` wired into `App.tsx` (`/documents`).
  - Verified with `ruff`, `mypy --strict`, `pytest` (53/53), `eslint`, `tsc`, `vitest` (`doc.test.tsx`), and `vite build`.

## 0.1.0-tpl — 2026-11-25
- **TPL-01..TPL-06**: Implemented Template & Branding vertical slice:
  - Alembic migration `0012_tpl_tables` (`letterheads`, `templates`, `theme_profiles`).
  - `backend/modules/tpl/{models,schemas,repository,service}.py` and bridge methods `tpl.*`.
  - `frontend/src/features/tpl/{types.ts,TemplatesPage.tsx}` wired into `App.tsx` (`/templates`).
  - Verified with `ruff`, `mypy --strict`, `pytest` (50/50), `eslint`, `tsc`, `vitest` (`tpl.test.tsx`), and `vite build`.

## 0.1.0-ops — 2026-11-25
- **OPS-01..OPS-08 (Gate G3 Operations & Admin complete)**: Implemented Exam Execution vertical slice:
  - Alembic migration `0011_ops_tables` (`room_session_states`, `participant_attendance`, `staff_attendance`, `committee_attendance`, `session_reports`, `incidents`, `makeup_links`).
  - `backend/modules/ops/{models,schemas,repository,service}.py` and bridge methods `ops.*`.
  - `frontend/src/features/ops/{types.ts,ExecutionPage.tsx}` wired into `App.tsx` (`/execution`).
  - Verified with `ruff`, `mypy --strict`, `pytest` (46/46), `eslint`, `tsc`, `vitest` (`ops.test.tsx`), and `vite build`.

## 0.1.0-exp — 2026-11-25
- **EXP-01..EXP-06**: Implemented Ekspedisi & Bahan vertical slice:
  - Alembic migration `0010_exp_tables` (`submission_items`, `submission_versions`, `print_quantities`, `handovers`).
  - `backend/modules/exp/{models,schemas,repository,service}.py` and bridge methods `exp.*`.
  - `frontend/src/features/exp/{types.ts,ExpeditionPage.tsx}` wired into `App.tsx` (`/expedition`).
  - Verified with `ruff`, `mypy --strict`, `pytest` (44/44), `eslint`, `tsc`, `vitest` (`exp.test.tsx`), and `vite build`.

## 0.1.0-tsk — 2026-11-25
- **TSK-01..TSK-05**: Implemented Tasks & Timeline vertical slice:
  - Alembic migration `0009_tsk_tables` (`tasks`, `task_dependencies`).
  - `backend/modules/tsk/{models,schemas,repository,service}.py` and bridge methods `tsk.*`.
  - `frontend/src/features/tsk/{types.ts,TasksPage.tsx}` wired into `App.tsx` (`/tasks`).
  - Verified with `ruff`, `mypy --strict`, `pytest` (41/41), `eslint`, `tsc`, `vitest` (`tsk.test.tsx`), and `vite build`.

## 0.1.0-com — 2026-11-25
- **COM-01..COM-06**: Implemented Committee & Meetings vertical slice:
  - Alembic migration `0008_com_tables` (`committee_roles`, `committee_members`, `program_kerja`, `meetings`, `meeting_attendance`, `exam_signatories`).
  - `backend/modules/com/{models,schemas,repository,service}.py` and bridge methods `com.*`.
  - `frontend/src/features/com/{types.ts,CommitteePage.tsx}` wired into `App.tsx` (`/committee`).
  - Verified with `ruff`, `mypy --strict`, `pytest` (38/38), `eslint`, `tsc`, `vitest` (`com.test.tsx`), and `vite build`.

## 0.1.0-sch — 2026-11-25
- **SCH-01..SCH-08 (Gate G2 Automation complete)**: Implemented Invigilation Scheduling vertical slice:
  - Alembic migration `0007_sch_tables` (`staff_availability`, `staff_profiles`, `invigilation_slots`, `invigilations`, `invigilation_reserves`, `solver_runs`).
  - `backend/modules/sch/{models,schemas,repository,validator,solver,service}.py` and bridge methods `sch.*`.
  - `frontend/src/features/sch/{types.ts,InvigilationPage.tsx}` (schedule grid, rule editor, workload panel, reserve stand-by) wired into `App.tsx` (`/invigilation`).
  - Verified with `ruff`, `mypy --strict`, `pytest` (35/35), `eslint`, `tsc`, `vitest` (`sch.test.tsx`), and `vite build`.

## 0.1.0-rom — 2026-11-25
- **ROM-01..ROM-08**: Implemented Room Allocation & Denah vertical slice:
  - Alembic migration `0006_rom_tables` (`seats`, `plan_seat_assignments`, `participant_sittings`).
  - `backend/modules/rom/{models,schemas,repository,validator,solver,service}.py` and bridge methods `rom.*`.
  - `frontend/src/features/rom/{types.ts,SeatingPage.tsx}` (`konva` + `react-konva` canvas, accessible table swap, layout editor, diagnostics, print context) wired into `App.tsx` (`/seating`).
  - Verified with `ruff`, `mypy --strict`, `pytest` (32/32), `eslint`, `tsc`, `vitest` (20/20), and `vite build`.

## 0.1.0-ses — 2026-11-25
- **SES-01..SES-07**: Implemented Exam Timetable vertical slice:
  - Alembic migration `0005_ses_tables` (`plans`, `sessions`, `room_sessions`, `room_papers`).
  - `backend/modules/ses/{models,schemas,repository,validator,solver,service}.py` and bridge methods `ses.*`.
  - `frontend/src/features/ses/{types.ts,TimetablePage.tsx}` wired into `App.tsx`.
  - Verified with `ruff`, `mypy --strict`, `pytest` (27/27), `eslint`, `tsc`, `vitest` (18/18), and `vite build`.

## 0.1.0-evt — 2026-11-25
- **EVT-01..EVT-07 (Gate G1 Core complete)**: Implemented Exam Workspace vertical slice.

## 0.1.0-mst — 2026-11-25
- **MST-01..MST-08**: Implemented Master Data vertical slice.

## 0.1.0-cfg — 2026-11-25
- **CFG-01..CFG-06**: Implemented Configuration & Onboarding vertical slice.

## 0.1.0-ui — 2026-11-25
- **UI-01..UI-12**: Implemented Ocean Ledger modern anti-slop design system and shared components.

## 0.1.0-fnd — 2026-11-24
- **FND-03..FND-09**: Completed Foundation layer.

## 0.1.0-fnd02 — 2026-11-24
- **FND-02**: Added modular backend package layout, `ruff` + `mypy --strict`, `eslint`, and CI.

## 0.1.0-spike (FND-01, in progress) — 2026-11-24
- Initialized Git repository on branch `feat/FND-01-stack-spike` with `.gitignore` and locked dependencies.

## 0.1 inception — 2026-11-24
Initial product design, UI direction, logical schema, backlog, AI instructions, contracts, fixtures and standalone mockup.
