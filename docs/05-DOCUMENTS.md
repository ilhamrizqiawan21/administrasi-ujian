# Document factory and template specification
Single canonical context builder per document type, derived from chosen event/plan/version, explicit scope and snapshot. All templates have stable ID, version, supported output engines, required fields, optional fields/defaults, repeat sections, page settings, signatory policy and validation. Never fill missing critical data with guessed values; preview reports missing/invalid fields. Optional blank forms vs actual results explicitly selected. Batch shows count and estimated pages, preview first/last, cancel and atomic writes, individual or combined PDF, ZIP for DOCX, safe unique filename. Scope mapping prevents cards for nonparticipants or attendance wrong room/session.

## Template modes
1. Built-in Word using docxtpl/python-docx; whitelist variables, loops/filters, sandbox Jinja environment; reject unsupported tags, macro, external refs. Upload existing `.docx`, discover placeholders and map in UI; test preview before publish. Raw Word layouts need separate PDF template or explicit optional locally installed renderer; never promise automatic identical conversion. DOCX remains editable.
2. Native PDF using ReportLab flowables, custom page size (A4, Letter, F4 in mm explicitly configurable), margins, table repeatRows, signatures grouped, page numbers, embed licensed Unicode fonts; RTL/Arabic shaping tested if needed. Native PDF is canonical print preview; built-in Word counterpart separate; no Office required.
3. P0/P1 no-code document settings: letterhead manual fields/logo alignment/border, uploaded image fit/crop, DOCX embedded kop, select one or two signers/labels, paper, margin, font, table columns, field toggles, editable clauses/body (plain or restricted rich text), copy/version template, reset. P2 visual canvas with snap/grid, text/table/logo/QR/data-binding blocks, safe schema with absolute coordinates for cards and flow layout for long documents; no arbitrary HTML/JS. Print millimeter coordinates validated against page bounds. Designer and renderer use same normalized schema; drag alternate keyboard.

## Variable contract
`school.name`, `school.address`, `school.logo`, `exam.title`, `exam.type_label`, `exam.year`, `exam.semester`, `exam.date_range`, `participant.number`, `participant.name`, `participant.class`, `participant.photo`, `room.code`, `session.start`, `session.end`, `session.subjects`, `staff.name`, `committee.chair`, `attendance.present`, `attendance.absent`, `attendance.unrecorded`, `finance.budget_total`, `finance.actual_total`, `signatures[]`, `rows[]`. Word uses e.g. `{{ school.name }}` and approved repeating syntax; mapping UI explains field types. Typed dates/currency localized at rendering, underlying values preserved. Template file never evaluated as Python. Version context hash, renderer version, source revision, template version and output checksum persisted. Reprint archived output byte-for-byte from stored asset. Number reservation atomic; preview not reserve; failed generation may record voided reservation, never silently reuse.

## Catalog (60 document types; verify actual local school formats in pilot)
| Category | Document | Scope | Outputs | Required context |
|---|---|---|---|---|
| Planning | Program kerja | event | DOCX PDF | tujuan, dasar, jadwal, kepanitiaan, RAB |
| Planning | Proposal kegiatan | event | DOCX PDF | tujuan, target, anggaran |
| Planning | Timeline kegiatan | event | PDF XLSX | tasks, deadline, PIC |
| Planning | RAB | event | DOCX PDF XLSX | budget version, line totals |
| Committee | SK panitia | event | DOCX PDF | roles, members, signatory |
| Committee | SK pengawas | event | DOCX PDF | staff, planned assignments |
| Committee | SK penyusun soal | event | DOCX PDF | subject, class, staff |
| Committee | Struktur panitia | event | PDF | role tree, names |
| Committee | Uraian tugas | role | DOCX PDF | jobdesc, member |
| Committee | Pakta integritas | person | DOCX PDF | name, role, editable clauses |
| Letters | Surat tugas mengawas | person | DOCX PDF | person, sessions, rooms, number |
| Letters | Undangan rapat | meeting | DOCX PDF | agenda, date, recipients |
| Letters | Pemberitahuan orang tua | class/event | DOCX PDF | event, dates, editable notes |
| Letters | Pemberitahuan guru | event | DOCX PDF | schedule, rules |
| Letters | Permohonan pengawas silang | event | DOCX PDF | recipient, dates, need |
| Letters | Surat dispensasi | person | DOCX PDF | participant, reason, approval |
| Letters | Surat izin ujian susulan | person | DOCX PDF | original, makeup, date |
| Letters | Surat keterangan mengikuti ujian | person | DOCX PDF | participant, attendance |
| Letters | Surat kustom | scope | DOCX PDF | number, recipient, body, signatures |
| Participants | Daftar nominasi peserta | event/class | PDF XLSX | participant snapshot |
| Participants | Kartu peserta STS/SAS/SAT/kustom | person | PDF | number, name, class, photo optional, period |
| Participants | Daftar ruang dan peserta | room | PDF XLSX | room, ordered roster |
| Participants | Nomor meja | seat | PDF | participant number, desk, room |
| Participants | Daftar hadir peserta | room/session | PDF DOCX XLSX | planned participants, blank/actual marks |
| Participants | Daftar peserta susulan | session | PDF XLSX | absence, makeup eligibility |
| Rooms | Denah duduk | room/session | PDF | seat coordinates, legend, board orientation |
| Rooms | Denah lokasi ruang | event | PDF | room layout manual |
| Rooms | Label ruangan | room | PDF | room code, capacity |
| Rooms | Tata tertib ruang | room/event | DOCX PDF | editable clauses |
| Scheduling | Jadwal ujian | event | PDF XLSX | session, date, groups, mapel |
| Scheduling | Jadwal pengawas | event | PDF XLSX | planned slots |
| Scheduling | Jadwal per kelas | class | PDF XLSX | group requirements |
| Scheduling | Jadwal per ruang | room | PDF XLSX | room sessions |
| Scheduling | Jadwal individu pengawas | person | PDF | assignments, time |
| Operations | Berita acara | room/session | DOCX PDF | planned, actual counts, incidents, signatures |
| Operations | Daftar hadir pengawas | day/session | PDF XLSX | planned and actual staff |
| Operations | Daftar hadir panitia | day/shift | PDF XLSX | committee roles, actual |
| Operations | Daftar hadir rapat | meeting | PDF XLSX | attendees |
| Operations | Notulen rapat | meeting | DOCX PDF | minutes, decisions, PIC |
| Operations | Jurnal pelaksanaan | day/event | DOCX PDF | sessions, notes |
| Operations | Catatan pelanggaran | room/session | DOCX PDF | incidents, resolution |
| Operations | Laporan kendala teknis | room/session | DOCX PDF | mode CBT, issue, resolution |
| Expedition | Ekspedisi kisi-kisi | event | PDF XLSX | due, received, validation |
| Expedition | Ekspedisi naskah soal | event | PDF XLSX | version, received, status |
| Expedition | Ekspedisi kunci/kartu soal | event | PDF XLSX | requirement, version, status |
| Expedition | Serah terima naskah | room/session | DOCX PDF | qty, sender, receiver |
| Expedition | Serah terima lembar jawaban | room/session | DOCX PDF | qty, sender, receiver |
| Expedition | Sampul amplop soal | room/session/paper | PDF | mapel, group, quantities |
| Expedition | Rekap penggandaan | event | PDF XLSX | paper qty + configurable reserve |
| Expedition | Ekspedisi pengumpulan nilai | event | PDF XLSX | mapel/class, receipt status |
| Finance | Buku kas | event | PDF XLSX | posted entries, running balance |
| Finance | Kuitansi | entry | DOCX PDF | amount, terbilang, payee |
| Finance | Daftar honor panitia | event | PDF XLSX | approved lines, signatures |
| Finance | Daftar honor pengawas | event | PDF XLSX | approved actual sessions, rate |
| Finance | Realisasi anggaran | event | PDF XLSX | RAB vs posted totals |
| Reporting | LPJ kegiatan | event | DOCX PDF | snapshot, narrative, operations, evaluation |
| Reporting | LPJ keuangan | event | DOCX PDF XLSX | ledger, reconciliation, attachments |
| Reporting | Evaluasi pelaksanaan | event | DOCX PDF | issues, actions, outcomes |
| Reporting | Daftar lampiran LPJ | event | PDF | numbered manifest, documents |
| Reporting | Rekap presensi dan susulan | event | PDF XLSX | attendance, linked makeup |

## LPJ
Editable structured sections (cover, approval, intro, basis entered by user, purpose, program, committee, participants, schedule, realization, incident/solutions, finance reconciliation, evaluation, closing, appendices). Assemble from frozen snapshots; if accounting incomplete, block finalization or mark draft clearly. User edits narrative without changing derived totals. Attachments indexed; combine PDF only after checking ordering/page size and supported files; optionally package all DOCX/XLSX originals in ZIP. No fabricated legal references or signatures. Signature image optional with authorization, not digital signature certification.
