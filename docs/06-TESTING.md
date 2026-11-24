# Quality strategy
## Gates
Every task: acceptance criteria, unit/integration tests where applicable, UI states, lint/typecheck, migration test if schema changes, PR review. Do not mark done on static mock or unrun tests. Release requires P0+P1 acceptance and human pilot sign-off, no P0 defects, no unresolved data-loss/security issue; P2 deferred explicitly. Record actual commands/results. No real student records in fixtures or agent prompts.

## Test layers
- Python pytest: validation, numbering, state transitions, repository transactions, audit, role/approval, finance rounding and totals, snapshot immutability, import failure rollback, file path safety, licence verification. Hypothesis optionally for solver invariant and money property tests.
- Solver: feasible tiny oracle, all same class impossible strict separation, unavailable staff, overlapping intervals with different IDs, own mapel hard vs soft, lock collision, undercapacity, accessible seats, timeouts, cancellation, published revision stale, seeded repeat best effort. Independently verify every output, not just solver status.
- UI Vitest/Testing Library: table filtering and row actions, forms validation, keyboard/modal focus trap, focus return, contrast and reduced motion, loading/cancel/error, no double-submit, dark+light branding, empty vs unavailable.
- E2E Playwright on browser mock adapter for flows only; native pywebview Windows integration tests for bridge readiness, file dialogs, threading, asset routes, clipboard, actual output. Browser tests not proof of native bridge.
- Document golden tests: long names, Arabic/Unicode where needed (embed licensed font; shaping/bidi tested), logo large/transparent, A4/F4/Letter, landscape, repeating table headers only where needed, no clipped row, signature keep together, batch print counts, optional photo, zero rows; inspect actual PDF pages and Word in Word/LibreOffice if available; validate DOCX ZIP integrity, no macro, no external links. Do not require PDF render identical to Word unless dedicated renderer verified.
- Security: path traversal, zip-slip, oversized archives, malformed XLSX/DOCX, formula injection on CSV/XLSX user-controlled text, script/XSS from names/template, blocked remote navigation, arbitrary bridge calls, tampered licence, backup corruption, no secrets/PII in logs, restore into isolated workspace.

## End-to-end UAT cases
| ID | Scenario | Pass condition |
|---|---|---|
| U01 | New profile SD/MI then custom event | No hardcoded jenjang; correct terminology |
| U02 | Import roster with leading-zero IDs and dupes | Preview exact identifiers; no silent merge |
| U03 | Mix VII/VIII/IX in 3 rooms, locked accessible seat | Unique seating, capacity/locks honored |
| U04 | Impossible schedule | No publish; diagnostics; fix and rerun |
| U05 | Generate cards, attendance and letters | Correct data scopes, headers, pagination, output openable |
| U06 | Replacement invigilator; absent then susulan | Planned preserved, actual captured, no double count |
| U07 | RAB, actual honor and reversal | Totals exact, audit history preserved |
| U08 | LPJ + archives | Data reconciles, attachments and manifest intact |
| U09 | Edit master after archive | Historical document unchanged |
| U10 | Backup/restore + upgrade | DB + files restored; rollback on failure |
| U11 | Clean offline Windows machine | Install, run, export, restart, uninstall retains data |
| U12 | 1366×768 at 100/125/150% DPI | No hidden critical controls; keyboard complete |
| U13 | Brand with low contrast | Reject/adjust tokens; both themes readable |
| U14 | License invalid | Read/export/backup remains; no data lost |

## Performance targets to benchmark
500 students/25 rooms/40 staff/30 sessions; larger stress 2000/80/100/60. Startup <=5s on reference Windows SSD i5/8GB target, list initial <=1s, bridge CRUD <=300ms typical, large tasks background, 200 cards <=60s target. Record hardware, fixture, p50/p95, memory, time and limits; adjust targets if measured. Run offline network disabled. Accessibility WCAG 2.2 AA design target, manual keyboard and contrast audit.
