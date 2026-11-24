# UI component TODO — 38 subtasks

Subtask turunan dari backlog utama; jangan dihitung sebagai fitur independen. Semua unchecked. Definisi selesai tetap mengacu `TODO.md`. Setiap acceptance harus diuji pada state yang relevan, light/dark, keyboard, responsive, dan data asli dari bridge pada aplikasi produksi.

## UIX-01 [P0] AppShell — induk UI-02
- [ ] Implementasi: Shell desktop: sidebar 236/64 px, topbar 56 px, breadcrumb 32 px, workspace scroll dan statusbar.
- [ ] Integrasi: Persist preferensi sidebar; scroll workspace independen; Escape menutup drawer, fokus kembali ke hamburger.
- [ ] Acceptance test: Sidebar open/collapsed/drawer, viewport 1366×768/1024/720, window resized; konten tidak hilang.
- [ ] Review visual dan keyboard menggunakan [referensi](../design/screenshots/01-dashboard.png); lampirkan screenshot hasil implementasi pada PR.

## UIX-02 [P0] SidebarNav — induk UI-02
- [ ] Implementasi: Kelompok Workspace, Persiapan, Pelaksanaan, Dokumen, Pelaporan, Sistem; Lucide 18 px dan label singkat.
- [ ] Integrasi: Route yang belum siap tidak dirender saat release; akses mengikuti workspace scope.
- [ ] Acceptance test: Aktif terlihat pada semua mode; focus-visible, tooltip pada rail, navigasi keyboard, scroll ke item aktif.
- [ ] Review visual dan keyboard menggunakan [referensi](../design/screenshots/01-dashboard.png); lampirkan screenshot hasil implementasi pada PR.

## UIX-03 [P0] Topbar & EventSelector — induk UI-03
- [ ] Implementasi: Hamburger, konteks kegiatan, theme switch, profil lokal; context switch punya guard.
- [ ] Integrasi: Event aktif berasal dari application state, bukan string hardcoded.
- [ ] Acceptance test: Pindah kegiatan memperbarui breadcrumb dan data; dirty form minta konfirmasi; tidak bocor data antar-event.
- [ ] Review visual dan keyboard menggunakan [referensi](../design/screenshots/01-dashboard.png); lampirkan screenshot hasil implementasi pada PR.

## UIX-04 [P0] Breadcrumb — induk UI-03
- [ ] Implementasi: Navigasi hierarkis berdasarkan route dengan current page dan judul aksesibel.
- [ ] Integrasi: Gunakan nav aria-label dan aria-current=page; breadcrumb tidak mengeksekusi operasi mutasi.
- [ ] Acceptance test: Tidak berulang; halaman detail dapat kembali ke parent; keyboard dan screen reader dapat membaca struktur.
- [ ] Review visual dan keyboard menggunakan [referensi](../design/screenshots/08-seating.png); lampirkan screenshot hasil implementasi pada PR.

## UIX-05 [P0] PageHeader — induk UI-02
- [ ] Implementasi: Judul 26–28 px, konteks singkat 13 px, primary action dan secondary action.
- [ ] Integrasi: Judul berasal dari route/context, tombol disabled hanya dengan alasan yang tersedia.
- [ ] Acceptance test: Pada viewport kecil tindakan wrap tanpa menimpa judul; primary action satu per workflow.
- [ ] Review visual dan keyboard menggunakan [referensi](../design/screenshots/07-schedule.png); lampirkan screenshot hasil implementasi pada PR.

## UIX-06 [P0] Button — induk UI-04
- [ ] Implementasi: Variant primary, secondary, neutral, destructive; tinggi 32/36/40 px; icon+text seperlunya.
- [ ] Integrasi: TypeScript discriminated props; native button type; destructive tidak otomatis melakukan aksi tanpa dialog.
- [ ] Acceptance test: Hover, focus, active, disabled, pending dan keyboard; pending memblokir double submit.
- [ ] Review visual dan keyboard menggunakan [referensi](../design/screenshots/20-components.png); lampirkan screenshot hasil implementasi pada PR.

## UIX-07 [P0] IconButton & Tooltip — induk UI-06
- [ ] Implementasi: Icon-only 32/36 px, visual netral view/edit dan merah delete; aria-label serta tooltip.
- [ ] Integrasi: Tidak menjadikan title browser satu-satunya aksesibilitas; row action berdasarkan policy.
- [ ] Acceptance test: Accessible name sama dengan tujuan; tooltip saat focus/hover, Escape dismiss, area klik konsisten.
- [ ] Review visual dan keyboard menggunakan [referensi](../design/screenshots/20-components.png); lampirkan screenshot hasil implementasi pada PR.

## UIX-08 [P0] ExportActionGroup — induk UI-06
- [ ] Implementasi: Word/PDF/Excel berupa ikon warna format; tampilkan label bila beberapa opsi format sama.
- [ ] Integrasi: Gunakan native save dialog/opaque handle; proses besar melalui job runner.
- [ ] Acceptance test: Format tidak tersedia hidden/disabled dengan alasan; output mengambil scope yang dipilih; file gagal tidak mengklaim sukses.
- [ ] Review visual dan keyboard menggunakan [referensi](../design/screenshots/13-documents.png); lampirkan screenshot hasil implementasi pada PR.

## UIX-09 [P0] DataTable — induk UI-05
- [ ] Implementasi: Header rata tengah, isi kiri/kanan/tengah menurut tipe, aksi kanan; sticky header, scroll area sendiri.
- [ ] Integrasi: Kontrol sort/filter/page tersinkron dengan query typed; tidak pakai index sebagai row key.
- [ ] Acceptance test: Sorting stabil; paging/filter lintas halaman; empty/error/selection; 1000 data tidak freeze.
- [ ] Review visual dan keyboard menggunakan [referensi](../design/screenshots/03-master.png); lampirkan screenshot hasil implementasi pada PR.

## UIX-10 [P0] TableToolbar — induk UI-05
- [ ] Implementasi: Search, filter jenjang/kelas/status, ekspor, bulk action bila ada pilihan.
- [ ] Integrasi: Query validation server-side; pilih lintas halaman hanya setelah user mengonfirmasi scope.
- [ ] Acceptance test: Debounced search; reset filter; jumlah pilihan akurat; scope ekspor eksplisit.
- [ ] Review visual dan keyboard menggunakan [referensi](../design/screenshots/06-expedition.png); lampirkan screenshot hasil implementasi pada PR.

## UIX-11 [P0] Pagination & Selection — induk UI-05
- [ ] Implementasi: Page size 25/50/100, next/prev, selected count, checkbox header tri-state.
- [ ] Integrasi: Server count otoritatif; filter menghapus pilihan tersembunyi atau menampilkan scope jelas.
- [ ] Acceptance test: First/last disabled; perubahan page size reset dengan benar; hapus baris terakhir tidak membuat halaman invalid.
- [ ] Review visual dan keyboard menggunakan [referensi](../design/screenshots/03-master.png); lampirkan screenshot hasil implementasi pada PR.

## UIX-12 [P0] TextField & IdentifierField — induk UI-07
- [ ] Implementasi: Label, input, required marker bila perlu, hint minimal, inline error. NIS/NISN/NIP berupa text.
- [ ] Integrasi: RHF/Zod di UI dan Pydantic di backend; tidak menebak leading zero hilang.
- [ ] Acceptance test: Leading zero tetap; invalid state terhubung aria-describedby; panjang dan trimming tervalidasi.
- [ ] Review visual dan keyboard menggunakan [referensi](../design/screenshots/20-components.png); lampirkan screenshot hasil implementasi pada PR.

## UIX-13 [P0] Select & Combobox — induk UI-07
- [ ] Implementasi: Select sederhana atau combobox searchable untuk peserta/guru/ruang yang banyak.
- [ ] Integrasi: Value menggunakan ID stabil; label display berasal dari snapshot/master sesuai konteks.
- [ ] Acceptance test: Keyboard arrows, Enter, Escape; empty option dan loading; nilai tidak valid ditolak.
- [ ] Review visual dan keyboard menggunakan [referensi](../design/screenshots/02-events.png); lampirkan screenshot hasil implementasi pada PR.

## UIX-14 [P0] DateTimeField & CurrencyField — induk UI-07
- [ ] Implementasi: Tanggal dan jam sesuai zona lembaga; mata uang format IDR saat display.
- [ ] Integrasi: Bridge ISO date/time, integer rupiah, bukan float atau formatted string.
- [ ] Acceptance test: Tanggal akhir sebelum awal ditolak; nominal negatif/tidak integer ditolak sesuai tipe transaksi.
- [ ] Review visual dan keyboard menggunakan [referensi](../design/screenshots/15-finance.png); lampirkan screenshot hasil implementasi pada PR.

## UIX-15 [P0] FilePicker & ImportWizard — induk UI-07
- [ ] Implementasi: Dialog native, mapping kolom, preview valid/invalid, policy duplikat, commit.
- [ ] Integrasi: Opaque file handle; MIME/size/extension validation; tidak menerima raw path dari JS.
- [ ] Acceptance test: Cancel tidak menulis; file besar/malformed ditolak; baris gagal dilaporkan; transaksi atomik.
- [ ] Review visual dan keyboard menggunakan [referensi](../design/screenshots/03-master.png); lampirkan screenshot hasil implementasi pada PR.

## UIX-16 [P0] CRUDModal — induk UI-08
- [ ] Implementasi: Dialog terpusat, title, form, footer Batal/Simpan, close, scroll body internal.
- [ ] Integrasi: Native dialog atau Radix Dialog dengan controlled open state; background inert.
- [ ] Acceptance test: Focus trap, Escape, focus return; dirty dialog minta konfirmasi; field errors tidak menutup modal.
- [ ] Review visual dan keyboard menggunakan [referensi](../design/screenshots/22-modal.png); lampirkan screenshot hasil implementasi pada PR.

## UIX-17 [P0] ConfirmDialog — induk UI-08
- [ ] Implementasi: Overlay terpusat khusus hapus/reset/void, jelaskan dampak dan tombol Batal/Hapus.
- [ ] Integrasi: Hanya dispatch setelah konfirmasi eksplisit; server memvalidasi revisi/policy.
- [ ] Acceptance test: Default focus pada cancel bila risiko tinggi; no accidental Enter; tidak menaruh confirm di header tabel.
- [ ] Review visual dan keyboard menggunakan [referensi](../design/screenshots/23-confirm.png); lampirkan screenshot hasil implementasi pada PR.

## UIX-18 [P0] ToastRegion — induk UI-09
- [ ] Implementasi: Pesan singkat sukses/gagal, dismiss, aria-live, posisi tidak menutup kontrol utama.
- [ ] Integrasi: Pesan dari result nyata, bukan dari click event; jangan menaruh informasi rahasia.
- [ ] Acceptance test: Stack konsisten; error yang butuh perbaikan juga inline; toast tidak menutup modal.
- [ ] Review visual dan keyboard menggunakan [referensi](../design/screenshots/20-components.png); lampirkan screenshot hasil implementasi pada PR.

## UIX-19 [P0] LoadingSkeleton & JobProgress — induk UI-10
- [ ] Implementasi: Skeleton untuk loading singkat; progress phase/count/cancel untuk import/solver/export.
- [ ] Integrasi: Job ID, status polling adaptif dan cancellation cooperative; jangan menganggap timeout sukses.
- [ ] Acceptance test: UI tetap responsif; retry/cancel tepat; progress tidak mengarang persen; state interrupted ditangani.
- [ ] Review visual dan keyboard menggunakan [referensi](../design/screenshots/20-components.png); lampirkan screenshot hasil implementasi pada PR.

## UIX-20 [P0] EmptyErrorPermissionState — induk UI-09
- [ ] Implementasi: Empty dengan satu langkah relevan, error dengan jalan keluar, permission/locked informatif.
- [ ] Integrasi: Map kode domain ke pesan Indonesia; retry hanya pada error retryable.
- [ ] Acceptance test: Kosong ≠ gagal fetch ≠ terkunci; offline normal; tidak bocorkan debug trace.
- [ ] Review visual dan keyboard menggunakan [referensi](../design/screenshots/20-components.png); lampirkan screenshot hasil implementasi pada PR.

## UIX-21 [P0] StatusIndicator & ProgressBar — induk UI-09
- [ ] Implementasi: Status berupa dot+teks; progress berasal dari numerator/denominator; tidak menumpuk badge.
- [ ] Integrasi: Gunakan state domain dan selector; tidak simpan duplicate derived values.
- [ ] Acceptance test: Kontras dua tema; warna tidak satu-satunya isyarat; denominator nol menghasilkan N/A.
- [ ] Review visual dan keyboard menggunakan [referensi](../design/screenshots/01-dashboard.png); lampirkan screenshot hasil implementasi pada PR.

## UIX-22 [P0] Metric & ReadinessPanel — induk UI-09
- [ ] Implementasi: Metrik padat dengan satuan dan sumber; checklist readiness actionable; agenda berikutnya.
- [ ] Integrasi: Read model agregat backend, no fabricated stats; refresh setelah mutasi.
- [ ] Acceptance test: Metrik rekonsiliasi dengan jumlah data; blocker terlihat; klik membuka filter terkait.
- [ ] Review visual dan keyboard menggunakan [referensi](../design/screenshots/01-dashboard.png); lampirkan screenshot hasil implementasi pada PR.

## UIX-23 [P0] ThemeSwitcher — induk UI-11
- [ ] Implementasi: Mode terang/gelap/sistem; token semantic diterapkan ke seluruh UI dan grafik.
- [ ] Integrasi: Token CSS vars, preferensi lokal; system media query listener dibersihkan.
- [ ] Acceptance test: Persist per user; reduced motion; contrast valid; tidak ada flash putih saat start.
- [ ] Review visual dan keyboard menggunakan [referensi](../design/screenshots/21-dashboard-dark.png); lampirkan screenshot hasil implementasi pada PR.

## UIX-24 [P1] BrandingEditor — induk UI-11
- [ ] Implementasi: Preset, logo, base/accent/semantic, density, typography, radius, preview/reset.
- [ ] Integrasi: Derive color states; whitelist font/radius; simpan per institution; audit revisi.
- [ ] Acceptance test: Invalid contrast ditolak atau diperbaiki; draft terpisah sampai apply; reset melalui dialog.
- [ ] Review visual dan keyboard menggunakan [referensi](../design/screenshots/18-settings.png); lampirkan screenshot hasil implementasi pada PR.

## UIX-25 [P0] ScheduleGrid — induk SCH-01
- [ ] Implementasi: Ruang sebagai baris dan slot waktu sebagai kolom, nama pengawas/mapel, indikator konflik/lock.
- [ ] Integrasi: Plan draft versioned, cell action calls validator; tidak menimpa published.
- [ ] Acceptance test: Overlap interval terdeteksi; slot kosong berbeda dari valid; scroll header/kolom; keyboard edit.
- [ ] Review visual dan keyboard menggunakan [referensi](../design/screenshots/07-schedule.png); lampirkan screenshot hasil implementasi pada PR.

## UIX-26 [P0] WorkloadPanel & RuleEditor — induk SCH-01
- [ ] Implementasi: Rekap sesi per guru, hard/soft rules, bobot dan availability; konflik dapat dibuka.
- [ ] Integrasi: Input solver serializable; diagnostic list independen; locked slot tervalidasi.
- [ ] Acceptance test: Jumlah sesi sesuai assignment; aturan wajib tidak dilonggarkan diam-diam; status feasible/optimal jelas.
- [ ] Review visual dan keyboard menggunakan [referensi](../design/screenshots/07-schedule.png); lampirkan screenshot hasil implementasi pada PR.

## UIX-27 [P0] RoomList — induk ROM-01
- [ ] Implementasi: Daftar ruang, kapasitas terisi/tersedia, status konflik dan pemilihan ruang.
- [ ] Integrasi: Scope plan + room session; data tidak dihitung hanya dari seat yang sedang tampak.
- [ ] Acceptance test: Room aktif terlihat; kapasitas fisik dan kursi nonaktif terhitung; search untuk banyak ruang.
- [ ] Review visual dan keyboard menggunakan [referensi](../design/screenshots/08-seating.png); lampirkan screenshot hasil implementasi pada PR.

## UIX-28 [P0] SeatCanvas & SeatTile — induk ROM-01
- [ ] Implementasi: Kanvas orientasi papan tulis, nomor meja, label tingkat/rombel, warna kelas, swap/lock.
- [ ] Integrasi: Konva visual only; domain validator authoritative; alternatif tabel keyboard; ID kursi stabil.
- [ ] Acceptance test: Drag/keyboard swap, undo/redo draft, kursi accessible, adjacency hard rule dan kapasitas; manual edit ditolak jika invalid.
- [ ] Review visual dan keyboard menggunakan [referensi](../design/screenshots/08-seating.png); lampirkan screenshot hasil implementasi pada PR.

## UIX-29 [P0] DocumentCatalog — induk DOC-01
- [ ] Implementasi: Kategori, tipe, scope, template version, availability, status stale; batch selection.
- [ ] Integrasi: Catalog definition server-side; scope & snapshot wajib.
- [ ] Acceptance test: Dokumen final/draf dibedakan; missing required fields mencegah generate; output format hanya yang didukung.
- [ ] Review visual dan keyboard menggunakan [referensi](../design/screenshots/13-documents.png); lampirkan screenshot hasil implementasi pada PR.

## UIX-30 [P0] DocumentPreview — induk DOC-01
- [ ] Implementasi: Preview PDF canonical, zoom/halaman, ukuran kertas dan tanda tangan; export actions.
- [ ] Integrasi: Asset preview opaque; bukan iframe remote; tidak menjanjikan DOCX pixel-identik.
- [ ] Acceptance test: Kop/tabel tidak terpotong; halaman pertama/terakhir diperiksa; render gagal memberi retry.
- [ ] Review visual dan keyboard menggunakan [referensi](../design/screenshots/13-documents.png); lampirkan screenshot hasil implementasi pada PR.

## UIX-31 [P0] TemplatePropertyPanel & Letterhead — induk TPL-01
- [ ] Implementasi: Ukuran kertas, orientasi, margin, font, kop manual/gambar/Word, signature block dan mapping variabel.
- [ ] Integrasi: docx placeholder mapping dan native PDF schema berbeda; import asset sanitized.
- [ ] Acceptance test: Preview sebelum publish; format valid, field mandatory, no external links; version immutable.
- [ ] Review visual dan keyboard menggunakan [referensi](../design/screenshots/14-studio.png); lampirkan screenshot hasil implementasi pada PR.

## UIX-32 [P2] VisualTemplateCanvas — induk TPL-01
- [ ] Implementasi: Palette teks/tabel/gambar/QR/variable; snap grid, properties, selection, undo/redo.
- [ ] Integrasi: Canvas absolute untuk kartu; flow layout untuk dokumen panjang; tidak menjanjikan drag-and-drop full editor di P0.
- [ ] Acceptance test: Elemen tidak keluar halaman; keyboard alternatives; output renderer sama schema; no arbitrary JS.
- [ ] Review visual dan keyboard menggunakan [referensi](../design/screenshots/14-studio.png); lampirkan screenshot hasil implementasi pada PR.

## UIX-33 [P1] ExpeditionMatrix — induk EXP-01
- [ ] Implementasi: Baris per mapel dan requirement; status kisi-kisi, soal, kunci, versi dan revisi.
- [ ] Integrasi: Submission version immutable, status derived dari current version.
- [ ] Acceptance test: Revisi invalidasi validasi lama; scope kelas tepat; file hanya dibuka pengguna berwenang.
- [ ] Review visual dan keyboard menggunakan [referensi](../design/screenshots/06-expedition.png); lampirkan screenshot hasil implementasi pada PR.

## UIX-34 [P1] AttendanceEditor & RoomStatus — induk OPS-01
- [ ] Implementasi: Status belum dicatat/hadir/sakit/izin/alpa/terlambat, catatan, actual pengawas, room readiness.
- [ ] Integrasi: Actual vs planned dipisah; derive jumlah peserta/hadir dari records.
- [ ] Acceptance test: Presensi belum dicatat tidak dianggap absen; pergantian pengawas cek overlap; dirty warning.
- [ ] Review visual dan keyboard menggunakan [referensi](../design/screenshots/10-attendance.png); lampirkan screenshot hasil implementasi pada PR.

## UIX-35 [P1] FinanceLedger & BudgetSummary — induk FIN-01
- [ ] Implementasi: RAB versus realisasi, integer IDR, kategori, posting/void, kuitansi dan honor.
- [ ] Integrasi: Idempotency key, transaction reversal, audit, scope dan integer rupiah.
- [ ] Acceptance test: Total ledger dan LPJ sama; posted tidak dapat dihapus; perhitungan honor hanya actual approved.
- [ ] Review visual dan keyboard menggunakan [referensi](../design/screenshots/15-finance.png); lampirkan screenshot hasil implementasi pada PR.

## UIX-36 [P1] LPJOutline & NarrativeEditor — induk LPJ-01
- [ ] Implementasi: Outline bagian LPJ, narasi editable, derived readonly statistics dan manifest lampiran.
- [ ] Integrasi: Narrative tidak overwrite field derived; generated docs immutable.
- [ ] Acceptance test: Draft bisa disimpan; finalisasi memvalidasi angka/kelengkapan; output mencantumkan snapshot versi.
- [ ] Review visual dan keyboard menggunakan [referensi](../design/screenshots/16-lpj.png); lampirkan screenshot hasil implementasi pada PR.

## UIX-37 [P0] ArchiveBrowser & BackupWizard — induk BAK-01
- [ ] Implementasi: Arsip read-only, backup integrity, restore staged, overwrite confirmation.
- [ ] Integrasi: SQLite backup API, checksum manifest, path validation, atomic replace after confirmation.
- [ ] Acceptance test: Restore korup gagal tanpa data loss; backup mencakup DB+assets; open/export tetap tersedia saat lisensi invalid.
- [ ] Review visual dan keyboard menggunakan [referensi](../design/screenshots/19-backup.png); lampirkan screenshot hasil implementasi pada PR.

## UIX-38 [P1] LocalLicenseDialog — induk LIC-01
- [ ] Implementasi: Impor file lisensi offline, lembaga, versi hak pakai, penjelasan expired/invalid.
- [ ] Integrasi: Public key embedded; private key tidak masuk repo/bundle; no hard hardware binding.
- [ ] Acceptance test: Invalid signature tidak memberi akses write; read/export/backup tetap berjalan; tidak ada telemetry.
- [ ] Review visual dan keyboard menggunakan [referensi](../design/screenshots/19-backup.png); lampirkan screenshot hasil implementasi pada PR.
