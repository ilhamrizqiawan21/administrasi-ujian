# Technical blueprint
## Keputusan stack
Python versi stabil yang kompatibel dengan pywebview, OR-Tools, PyInstaller (spike 3.12/3.13, jangan pin tanpa test); React + TypeScript strict + Vite; Tailwind/shadcn/ui + Lucide, TanStack Table/Router (hash atau memory routing sesuai aset lokal), React Hook Form/Zod, Zustand untuk UI state saja, Konva untuk denah, Recharts untuk grafik. SQLite + SQLAlchemy 2 + Alembic; Pydantic; OR-Tools CP-SAT lokal, docxtpl/python-docx, ReportLab, openpyxl, Pillow, Segno; platformdirs; pytest, Vitest, Testing Library, Playwright web adapter dan native Windows smoke. Node hanya dev/build; tidak diperlukan pengguna. Pilih versi lockfile setelah kompatibilitas dan audit lisensi.

## Struktur direktori target (belum dibuat)
```
app/main.py
backend/core/{config,errors,db,paths,logging,jobs,security,licensing}.py
backend/bridge/{api,schemas,registry}.py
backend/modules/<domain>/{models,schemas,repository,service,policies}.py
backend/engines/{scheduler,seating,documents,finance,reports}/
backend/migrations/
frontend/src/{app,components/ui,components/shared,features,lib/bridge,styles,types}/
resources/{templates,fonts,icons,presets}/
tests/{unit,integration,fixtures,golden,e2e}/
installer/ujian-cerdas.iss
scripts/{build.ps1,verify_release.ps1}/
```
Domains: institution, roster, exam, committee, tasks, submission, sessions, allocation, invigilation, operations, finance, documents, archive, branding. UI tidak akses DB atau filesystem langsung. Domain rules tidak bergantung pada pywebview. SQLAlchemy session per request/job; transactional service; repositories tidak commit sendiri. Dependency direction UI → typed bridge → application services → domain/repositories → adapters. Composition root menginisialisasi dependencies, migration, jobs dan window.

## Runtime
PyWebView memakai EdgeChromium/WebView2 pada Windows. Bundle frontend Vite dengan base relatif, route hash/memory; origin lokal trusted, tidak mengizinkan navigasi remote. Bridge menunggu `pywebviewready` atau mengecek ketersediaan API, timeout + error recovery. Gunakan local assets/file serving yang dibatasi root; bila runtime memerlukan HTTP lokal, bind loopback saja, token/origin check, jangan membuka LAN. Development Vite hanya localhost; mock adapter eksplisit dev/test dan tidak dibundel ke production. Tidak ada CDN, telemetry, auto network, remote HTML, eval, arbitrary command atau arbitrary file read/write.

## Data path
`%LOCALAPPDATA%/UjianCerdas/` (atau pilihan folder lokal yang lolos pemeriksaan; bukan network share): config, db/<institution>.sqlite, assets/<uuid>, backups, exports, logs, temp. Jangan menulis ke Program Files, direktori bundle onefile atau direktori repo. Aset immutable by id/hash, validasi MIME/ukuran, metadata DB. Single instance per workspace dengan lock OS; tidak menaruh DB aktif di folder sync cloud. Foreign keys ON per connection, WAL jika lokal, busy_timeout, transaction writes; jangan share session antar thread. Backup pakai SQLite backup API, bukan copy file db aktif saja.

## Jobs
Solver, import besar, ekspor, backup di worker; UI hanya start/status/cancel. Bounded queue; satu mutating job per scope; progress phase + count, cancel cooperatively, cleanup temp; no half-publish. Status queued/running/succeeded/failed/cancelled; persist metadata, saat crash tandai interrupted; retry eksplisit idempotent. Revision check sebelum commit. UI polling adaptif atau push event minimal; jangan block main loop. Logging redacted correlation ID, rotation; error domain yang dapat ditindaklanjuti.

## Build/release decisions
Build Windows di Windows VM/CI runner; PyInstaller one-folder + Inno Setup agar startup cepat dan mudah debug; installer .exe offline, WebView2 Evergreen Standalone Installer resmi sesuai arsitektur bila diperlukan. Jangan download saat instalasi offline. Linux untuk dev dengan GTK/Qt sesuai dukungan. Gunakan fresh virtualenv Windows agar tidak menarik Qt tidak perlu. Sign jika sertifikat tersedia; jangan menyatakan SmartScreen bebas warning. Uninstall tidak menghapus data default; update in-place backup dan migration. Verify SHA256 dan notices dependency. Detail di 07-RELEASE.

## ADR awal
ADR-001 local-first single writer, bukan SaaS. ADR-002 bridge allowlist, bukan REST umum. ADR-003 snapshot & revision per event. ADR-004 CP-SAT hard vs soft dengan validator independen. ADR-005 docx dan PDF native terpisah; tidak mengklaim pixel-identik. ADR-006 proprietary licensing offline, non-destructive. ADR-007 desktop sidebar override dari standar web topbar, lihat design system. Semua perubahan ADR perlu alasan, alternatif, risiko, approval.
