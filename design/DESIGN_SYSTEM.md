# Visual system — Ujian Cerdas / Ocean Ledger
Source reviewed: [standar-ui-project](https://github.com/ilhamrizqiawan21/standar-ui-project/tree/main/admin-panel-standards), 24 Nov 2026, tree 87490c183b9d57b2600e3daa986171e84df4ab5c. Read global README + rules 01–07 and `.agents/skills/admin-panel-ui/SKILL.md` before UI work. Inventory recommends ShadCN Admin for React/TS; use component patterns not copy branding or paid assets. This project file is a link + override, not duplicate of global standards.

## Project override and intent
Desktop workspace, not SaaS web. Desktop persistent collapsible navy sidebar is intentional override of centered topbar main nav for medium/large web projects; narrow layout sidebar becomes drawer/hamburger, topbar contains context and settings; owner review required. Breadcrumb on every page. Primary visual direction: light ocean canvas and navy navigation, muted blue/teal surfaces, limited white only for paper or contrast-sensitive content; no gradient, glass, emoji, giant radius, meaningless KPI cards. Light and dark available. Dense data grids with calm accents; typography system fonts (Segoe UI on Windows), bundle licensed fonts if later needed. Indonesian formal concise UI; no `contoh`, `dummy`, `sample` in production UI. No external shortcuts, excessive onboarding or explanatory clutter.

| Token | Light | Dark |
|---|---|---|
| canvas | #E7EFF3 | #14232F |
| surface | #F1F6F7 | #1C2D3A |
| surface-raised | #F7FAFA | #253947 |
| surface-tint | #DCE9EE | #213D4A |
| nav | #183544 | #10232D |
| nav-text | #E6F1F4 | #E6F1F4 |
| primary | #22677B | #7EC9D5 |
| primary-on | #FFFFFF | #10232D |
| text | #193440 | #E6F1F4 |
| muted | #4D6570 | #A5BDC6 |
| border | #C5D7DE | #3B5563 |
| success | #236B54 | #8ED2AB |
| warning | #805311 | #E7BF78 |
| destructive | #A33D43 | #F4A5A9 |
| focus | #146B9A | #8DD9EF |
| export Word/PDF/Excel | #2856A0 / #A63D42 / #21714D | lighter contrast-aware variants |

Validate contrast programmatically for all pairs (text 4.5:1, large text and UI indicators 3:1 target); token pairs not automatically guaranteed. Derive hover/active/focus/disabled from semantic palette; accessible contrast constraints and reject invalid custom palettes. Presets Ocean Ledger, Slate Indigo, Forest Sage, Warm Sand. Theme persisted per institution/user; preview/reset/import/export JSON with schema/version, no arbitrary CSS. Allow logo/app name/favicon (window/taskbar icon separate platform capability), base/accent/semantic colors, typography allowlist, density, radius 6–8 default, layout visibility and theme.

## Dimensions & components
Spacing 4/8/12/16/20/24/32; radius 6–8px; single subtle border, minimal shadow for modal only. Desktop 1366×768 baseline; sidebar 236px collapsed 64px, topbar 56px, breadcrumb strip 32px; padding 20px, content max 1600px; at <=1024 compact rail; <=800 drawer. Tables own horizontal scroll, sticky header, min row 40px; header center, text left, numeric right, status/action center; Actions right, icon-only View/Edit/Delete with tooltips/aria-label, neutral edit/view red delete. Export Word/PDF/Excel icon-only differentiated by format color, labels if ambiguity. Buttons 32/36/40 high, 14px medium, square icon buttons, focus visible, loading disables duplicate submit. Forms centered modal backdrop, focus trap, Escape and focus return, dirty confirmation; large editors (denah, template) full workspace with explicit override, not CRUD forms. Responsive modal may fill narrow screen. Destructive confirm centered overlay never in table/header; explain impact. Toast top-right/bottom adaptive not cover modal, short, dismissible, aria-live; form errors inline. No split-screen login; if optional local lock, centered form/password visibility.

## Navigation/IA
Workspace: Dashboard, Kegiatan Ujian. Persiapan: Master Data (Siswa/Guru/Kelas/Mapel/Ruang), Kepanitiaan, Task list, Ekspedisi, Jadwal, Denah. Pelaksanaan: Monitoring, Presensi, Berita Acara, Susulan. Dokumen: Document Center, Template Studio. Pelaporan: Anggaran, LPJ, Arsip. Sistem: Pengaturan, Backup, Lisensi. Event context always visible, switching warns if unsaved. Breadcrumb includes event/feature/current page. Topbar only event selector/theme/help/profile and hamburger, no clutter. Preserve scroll/filter per route.

## UI screen blueprint
- Dashboard: readiness checklist with actionable exceptions, next session and deadline, compact participant/room/pengawas counts, no invented percentages.
- Master table: search/filter/selection/import preview/export/pagination; create/edit modal; no hidden critical actions.
- Schedule: date/session grid with room rows and mapel/pengawas; filters by grade/day/staff, workload sidebar, conflicts list, locks; generate draft then review/publish.
- Seating: room list/occupancy, canvas with board and desk labels, rule panel, conflicts/soft penalty, lock/swap, keyboard accessible table alternative, print preview.
- Expedition: matrix per class/mapel and item, status text, version attachment modal.
- Document center: categorized table, scope selector, paper template and output, PDF preview and missing field warnings; avoid render on every keystroke.
- Finance: summary & ledger, RAB version, totals; exact currency with numeric alignment, no decorative charts.
- LPJ: section outline + editable narrative + derived read-only summary, attachments and publish gate.
- Settings: branding live preview, contrast errors, restore default, backups and licensing. All async screens have loading/empty/error/success/permission/offline/disabled states; offline normal state not alarming. Reduced motion 0ms; normal 120–180ms easing, no animated KPI counters.

Mockup `mockup.html` is a standalone browser reference with clickable page navigation, theme toggle, sidebar and sample modal interaction; fixtures only, not connected to Python. See backlog for production requirements. Verify screenshots at 1366×768, 1440×900, 1024×768 and 125%/150% DPI; keyboard, focus, table header and contrast review. Do not copy mockup inline styles directly into production: extract tokens and components.
