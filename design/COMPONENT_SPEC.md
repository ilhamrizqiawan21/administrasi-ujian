# Spesifikasi komponen dan mockup

Baseline desain Ocean Ledger. Seluruh tampilan menggunakan data sintetis untuk validasi visual, bukan data sekolah asli. `mockup.html` adalah prototype navigable; data tidak persisten, generator/solver/ekspor adalah simulasi visual. Tidak ada ketergantungan eksternal. Bukti screenshot bukan bukti aplikasi produksi. Standar upstream dan override desktop: [DESIGN_SYSTEM.md](DESIGN_SYSTEM.md).

## Cara review
Buka `mockup.html` melalui browser, pilih menu kiri, toggle light/dark, klik ikon bantuan untuk galeri, buka modal edit/hapus, coba pemilihan kursi dan filter tabel. Screenshot layar utama di `screenshots/`; potongan galeri di `components/`. Gunakan screenshot sebagai referensi hierarki, bukan copy-paste HTML inline. Setiap komponen di bawah memiliki kontrak, state/acceptance, dan aturan implementasi; subtask tercatat di `../backlog/UI_COMPONENT_TODO.md`.

## Komponen reusable dan domain

### UIX-01 · AppShell

- **Referensi visual:** [Screenshot](screenshots/01-dashboard.png) · backlog induk `UI-02` · P0.
- **Spesifikasi:** Shell desktop: sidebar 236/64 px, topbar 56 px, breadcrumb 32 px, workspace scroll dan statusbar.
- **States dan acceptance:** Sidebar open/collapsed/drawer, viewport 1366×768/1024/720, window resized; konten tidak hilang.
- **Kontrak implementasi:** Persist preferensi sidebar; scroll workspace independen; Escape menutup drawer, fokus kembali ke hamburger.

### UIX-02 · SidebarNav

- **Referensi visual:** [Screenshot](screenshots/01-dashboard.png) · backlog induk `UI-02` · P0.
- **Spesifikasi:** Kelompok Workspace, Persiapan, Pelaksanaan, Dokumen, Pelaporan, Sistem; Lucide 18 px dan label singkat.
- **States dan acceptance:** Aktif terlihat pada semua mode; focus-visible, tooltip pada rail, navigasi keyboard, scroll ke item aktif.
- **Kontrak implementasi:** Route yang belum siap tidak dirender saat release; akses mengikuti workspace scope.

### UIX-03 · Topbar & EventSelector

- **Referensi visual:** [Screenshot](screenshots/01-dashboard.png) · backlog induk `UI-03` · P0.
- **Spesifikasi:** Hamburger, konteks kegiatan, theme switch, profil lokal; context switch punya guard.
- **States dan acceptance:** Pindah kegiatan memperbarui breadcrumb dan data; dirty form minta konfirmasi; tidak bocor data antar-event.
- **Kontrak implementasi:** Event aktif berasal dari application state, bukan string hardcoded.

### UIX-04 · Breadcrumb

- **Referensi visual:** [Screenshot](screenshots/08-seating.png) · backlog induk `UI-03` · P0.
- **Spesifikasi:** Navigasi hierarkis berdasarkan route dengan current page dan judul aksesibel.
- **States dan acceptance:** Tidak berulang; halaman detail dapat kembali ke parent; keyboard dan screen reader dapat membaca struktur.
- **Kontrak implementasi:** Gunakan nav aria-label dan aria-current=page; breadcrumb tidak mengeksekusi operasi mutasi.

### UIX-05 · PageHeader

- **Referensi visual:** [Screenshot](screenshots/07-schedule.png) · backlog induk `UI-02` · P0.
- **Spesifikasi:** Judul 26–28 px, konteks singkat 13 px, primary action dan secondary action.
- **States dan acceptance:** Pada viewport kecil tindakan wrap tanpa menimpa judul; primary action satu per workflow.
- **Kontrak implementasi:** Judul berasal dari route/context, tombol disabled hanya dengan alasan yang tersedia.

### UIX-06 · Button

- **Referensi visual:** [Screenshot](screenshots/20-components.png) · backlog induk `UI-04` · P0.
- **Spesifikasi:** Variant primary, secondary, neutral, destructive; tinggi 32/36/40 px; icon+text seperlunya.
- **States dan acceptance:** Hover, focus, active, disabled, pending dan keyboard; pending memblokir double submit.
- **Kontrak implementasi:** TypeScript discriminated props; native button type; destructive tidak otomatis melakukan aksi tanpa dialog.

### UIX-07 · IconButton & Tooltip

- **Referensi visual:** [Screenshot](screenshots/20-components.png) · backlog induk `UI-06` · P0.
- **Spesifikasi:** Icon-only 32/36 px, visual netral view/edit dan merah delete; aria-label serta tooltip.
- **States dan acceptance:** Accessible name sama dengan tujuan; tooltip saat focus/hover, Escape dismiss, area klik konsisten.
- **Kontrak implementasi:** Tidak menjadikan title browser satu-satunya aksesibilitas; row action berdasarkan policy.

### UIX-08 · ExportActionGroup

- **Referensi visual:** [Screenshot](screenshots/13-documents.png) · backlog induk `UI-06` · P0.
- **Spesifikasi:** Word/PDF/Excel berupa ikon warna format; tampilkan label bila beberapa opsi format sama.
- **States dan acceptance:** Format tidak tersedia hidden/disabled dengan alasan; output mengambil scope yang dipilih; file gagal tidak mengklaim sukses.
- **Kontrak implementasi:** Gunakan native save dialog/opaque handle; proses besar melalui job runner.

### UIX-09 · DataTable

- **Referensi visual:** [Screenshot](screenshots/03-master.png) · backlog induk `UI-05` · P0.
- **Spesifikasi:** Header rata tengah, isi kiri/kanan/tengah menurut tipe, aksi kanan; sticky header, scroll area sendiri.
- **States dan acceptance:** Sorting stabil; paging/filter lintas halaman; empty/error/selection; 1000 data tidak freeze.
- **Kontrak implementasi:** Kontrol sort/filter/page tersinkron dengan query typed; tidak pakai index sebagai row key.

### UIX-10 · TableToolbar

- **Referensi visual:** [Screenshot](screenshots/06-expedition.png) · backlog induk `UI-05` · P0.
- **Spesifikasi:** Search, filter jenjang/kelas/status, ekspor, bulk action bila ada pilihan.
- **States dan acceptance:** Debounced search; reset filter; jumlah pilihan akurat; scope ekspor eksplisit.
- **Kontrak implementasi:** Query validation server-side; pilih lintas halaman hanya setelah user mengonfirmasi scope.

### UIX-11 · Pagination & Selection

- **Referensi visual:** [Screenshot](screenshots/03-master.png) · backlog induk `UI-05` · P0.
- **Spesifikasi:** Page size 25/50/100, next/prev, selected count, checkbox header tri-state.
- **States dan acceptance:** First/last disabled; perubahan page size reset dengan benar; hapus baris terakhir tidak membuat halaman invalid.
- **Kontrak implementasi:** Server count otoritatif; filter menghapus pilihan tersembunyi atau menampilkan scope jelas.

### UIX-12 · TextField & IdentifierField

- **Referensi visual:** [Screenshot](screenshots/20-components.png) · backlog induk `UI-07` · P0.
- **Spesifikasi:** Label, input, required marker bila perlu, hint minimal, inline error. NIS/NISN/NIP berupa text.
- **States dan acceptance:** Leading zero tetap; invalid state terhubung aria-describedby; panjang dan trimming tervalidasi.
- **Kontrak implementasi:** RHF/Zod di UI dan Pydantic di backend; tidak menebak leading zero hilang.

### UIX-13 · Select & Combobox

- **Referensi visual:** [Screenshot](screenshots/02-events.png) · backlog induk `UI-07` · P0.
- **Spesifikasi:** Select sederhana atau combobox searchable untuk peserta/guru/ruang yang banyak.
- **States dan acceptance:** Keyboard arrows, Enter, Escape; empty option dan loading; nilai tidak valid ditolak.
- **Kontrak implementasi:** Value menggunakan ID stabil; label display berasal dari snapshot/master sesuai konteks.

### UIX-14 · DateTimeField & CurrencyField

- **Referensi visual:** [Screenshot](screenshots/15-finance.png) · backlog induk `UI-07` · P0.
- **Spesifikasi:** Tanggal dan jam sesuai zona lembaga; mata uang format IDR saat display.
- **States dan acceptance:** Tanggal akhir sebelum awal ditolak; nominal negatif/tidak integer ditolak sesuai tipe transaksi.
- **Kontrak implementasi:** Bridge ISO date/time, integer rupiah, bukan float atau formatted string.

### UIX-15 · FilePicker & ImportWizard

- **Referensi visual:** [Screenshot](screenshots/03-master.png) · backlog induk `UI-07` · P0.
- **Spesifikasi:** Dialog native, mapping kolom, preview valid/invalid, policy duplikat, commit.
- **States dan acceptance:** Cancel tidak menulis; file besar/malformed ditolak; baris gagal dilaporkan; transaksi atomik.
- **Kontrak implementasi:** Opaque file handle; MIME/size/extension validation; tidak menerima raw path dari JS.

### UIX-16 · CRUDModal

- **Referensi visual:** [Screenshot](screenshots/22-modal.png) · backlog induk `UI-08` · P0.
- **Spesifikasi:** Dialog terpusat, title, form, footer Batal/Simpan, close, scroll body internal.
- **States dan acceptance:** Focus trap, Escape, focus return; dirty dialog minta konfirmasi; field errors tidak menutup modal.
- **Kontrak implementasi:** Native dialog atau Radix Dialog dengan controlled open state; background inert.

### UIX-17 · ConfirmDialog

- **Referensi visual:** [Screenshot](screenshots/23-confirm.png) · backlog induk `UI-08` · P0.
- **Spesifikasi:** Overlay terpusat khusus hapus/reset/void, jelaskan dampak dan tombol Batal/Hapus.
- **States dan acceptance:** Default focus pada cancel bila risiko tinggi; no accidental Enter; tidak menaruh confirm di header tabel.
- **Kontrak implementasi:** Hanya dispatch setelah konfirmasi eksplisit; server memvalidasi revisi/policy.

### UIX-18 · ToastRegion

- **Referensi visual:** [Screenshot](screenshots/20-components.png) · backlog induk `UI-09` · P0.
- **Spesifikasi:** Pesan singkat sukses/gagal, dismiss, aria-live, posisi tidak menutup kontrol utama.
- **States dan acceptance:** Stack konsisten; error yang butuh perbaikan juga inline; toast tidak menutup modal.
- **Kontrak implementasi:** Pesan dari result nyata, bukan dari click event; jangan menaruh informasi rahasia.

### UIX-19 · LoadingSkeleton & JobProgress

- **Referensi visual:** [Screenshot](screenshots/20-components.png) · backlog induk `UI-10` · P0.
- **Spesifikasi:** Skeleton untuk loading singkat; progress phase/count/cancel untuk import/solver/export.
- **States dan acceptance:** UI tetap responsif; retry/cancel tepat; progress tidak mengarang persen; state interrupted ditangani.
- **Kontrak implementasi:** Job ID, status polling adaptif dan cancellation cooperative; jangan menganggap timeout sukses.

### UIX-20 · EmptyErrorPermissionState

- **Referensi visual:** [Screenshot](screenshots/20-components.png) · backlog induk `UI-09` · P0.
- **Spesifikasi:** Empty dengan satu langkah relevan, error dengan jalan keluar, permission/locked informatif.
- **States dan acceptance:** Kosong ≠ gagal fetch ≠ terkunci; offline normal; tidak bocorkan debug trace.
- **Kontrak implementasi:** Map kode domain ke pesan Indonesia; retry hanya pada error retryable.

### UIX-21 · StatusIndicator & ProgressBar

- **Referensi visual:** [Screenshot](screenshots/01-dashboard.png) · backlog induk `UI-09` · P0.
- **Spesifikasi:** Status berupa dot+teks; progress berasal dari numerator/denominator; tidak menumpuk badge.
- **States dan acceptance:** Kontras dua tema; warna tidak satu-satunya isyarat; denominator nol menghasilkan N/A.
- **Kontrak implementasi:** Gunakan state domain dan selector; tidak simpan duplicate derived values.

### UIX-22 · Metric & ReadinessPanel

- **Referensi visual:** [Screenshot](screenshots/01-dashboard.png) · backlog induk `UI-09` · P0.
- **Spesifikasi:** Metrik padat dengan satuan dan sumber; checklist readiness actionable; agenda berikutnya.
- **States dan acceptance:** Metrik rekonsiliasi dengan jumlah data; blocker terlihat; klik membuka filter terkait.
- **Kontrak implementasi:** Read model agregat backend, no fabricated stats; refresh setelah mutasi.

### UIX-23 · ThemeSwitcher

- **Referensi visual:** [Screenshot](screenshots/21-dashboard-dark.png) · backlog induk `UI-11` · P0.
- **Spesifikasi:** Mode terang/gelap/sistem; token semantic diterapkan ke seluruh UI dan grafik.
- **States dan acceptance:** Persist per user; reduced motion; contrast valid; tidak ada flash putih saat start.
- **Kontrak implementasi:** Token CSS vars, preferensi lokal; system media query listener dibersihkan.

### UIX-24 · BrandingEditor

- **Referensi visual:** [Screenshot](screenshots/18-settings.png) · backlog induk `UI-11` · P1.
- **Spesifikasi:** Preset, logo, base/accent/semantic, density, typography, radius, preview/reset.
- **States dan acceptance:** Invalid contrast ditolak atau diperbaiki; draft terpisah sampai apply; reset melalui dialog.
- **Kontrak implementasi:** Derive color states; whitelist font/radius; simpan per institution; audit revisi.

### UIX-25 · ScheduleGrid

- **Referensi visual:** [Screenshot](screenshots/07-schedule.png) · backlog induk `SCH-01` · P0.
- **Spesifikasi:** Ruang sebagai baris dan slot waktu sebagai kolom, nama pengawas/mapel, indikator konflik/lock.
- **States dan acceptance:** Overlap interval terdeteksi; slot kosong berbeda dari valid; scroll header/kolom; keyboard edit.
- **Kontrak implementasi:** Plan draft versioned, cell action calls validator; tidak menimpa published.

### UIX-26 · WorkloadPanel & RuleEditor

- **Referensi visual:** [Screenshot](screenshots/07-schedule.png) · backlog induk `SCH-01` · P0.
- **Spesifikasi:** Rekap sesi per guru, hard/soft rules, bobot dan availability; konflik dapat dibuka.
- **States dan acceptance:** Jumlah sesi sesuai assignment; aturan wajib tidak dilonggarkan diam-diam; status feasible/optimal jelas.
- **Kontrak implementasi:** Input solver serializable; diagnostic list independen; locked slot tervalidasi.

### UIX-27 · RoomList

- **Referensi visual:** [Screenshot](screenshots/08-seating.png) · backlog induk `ROM-01` · P0.
- **Spesifikasi:** Daftar ruang, kapasitas terisi/tersedia, status konflik dan pemilihan ruang.
- **States dan acceptance:** Room aktif terlihat; kapasitas fisik dan kursi nonaktif terhitung; search untuk banyak ruang.
- **Kontrak implementasi:** Scope plan + room session; data tidak dihitung hanya dari seat yang sedang tampak.

### UIX-28 · SeatCanvas & SeatTile

- **Referensi visual:** [Screenshot](screenshots/08-seating.png) · backlog induk `ROM-01` · P0.
- **Spesifikasi:** Kanvas orientasi papan tulis, nomor meja, label tingkat/rombel, warna kelas, swap/lock.
- **States dan acceptance:** Drag/keyboard swap, undo/redo draft, kursi accessible, adjacency hard rule dan kapasitas; manual edit ditolak jika invalid.
- **Kontrak implementasi:** Konva visual only; domain validator authoritative; alternatif tabel keyboard; ID kursi stabil.

### UIX-29 · DocumentCatalog

- **Referensi visual:** [Screenshot](screenshots/13-documents.png) · backlog induk `DOC-01` · P0.
- **Spesifikasi:** Kategori, tipe, scope, template version, availability, status stale; batch selection.
- **States dan acceptance:** Dokumen final/draf dibedakan; missing required fields mencegah generate; output format hanya yang didukung.
- **Kontrak implementasi:** Catalog definition server-side; scope & snapshot wajib.

### UIX-30 · DocumentPreview

- **Referensi visual:** [Screenshot](screenshots/13-documents.png) · backlog induk `DOC-01` · P0.
- **Spesifikasi:** Preview PDF canonical, zoom/halaman, ukuran kertas dan tanda tangan; export actions.
- **States dan acceptance:** Kop/tabel tidak terpotong; halaman pertama/terakhir diperiksa; render gagal memberi retry.
- **Kontrak implementasi:** Asset preview opaque; bukan iframe remote; tidak menjanjikan DOCX pixel-identik.

### UIX-31 · TemplatePropertyPanel & Letterhead

- **Referensi visual:** [Screenshot](screenshots/14-studio.png) · backlog induk `TPL-01` · P0.
- **Spesifikasi:** Ukuran kertas, orientasi, margin, font, kop manual/gambar/Word, signature block dan mapping variabel.
- **States dan acceptance:** Preview sebelum publish; format valid, field mandatory, no external links; version immutable.
- **Kontrak implementasi:** docx placeholder mapping dan native PDF schema berbeda; import asset sanitized.

### UIX-32 · VisualTemplateCanvas

- **Referensi visual:** [Screenshot](screenshots/14-studio.png) · backlog induk `TPL-01` · P2.
- **Spesifikasi:** Palette teks/tabel/gambar/QR/variable; snap grid, properties, selection, undo/redo.
- **States dan acceptance:** Elemen tidak keluar halaman; keyboard alternatives; output renderer sama schema; no arbitrary JS.
- **Kontrak implementasi:** Canvas absolute untuk kartu; flow layout untuk dokumen panjang; tidak menjanjikan drag-and-drop full editor di P0.

### UIX-33 · ExpeditionMatrix

- **Referensi visual:** [Screenshot](screenshots/06-expedition.png) · backlog induk `EXP-01` · P1.
- **Spesifikasi:** Baris per mapel dan requirement; status kisi-kisi, soal, kunci, versi dan revisi.
- **States dan acceptance:** Revisi invalidasi validasi lama; scope kelas tepat; file hanya dibuka pengguna berwenang.
- **Kontrak implementasi:** Submission version immutable, status derived dari current version.

### UIX-34 · AttendanceEditor & RoomStatus

- **Referensi visual:** [Screenshot](screenshots/10-attendance.png) · backlog induk `OPS-01` · P1.
- **Spesifikasi:** Status belum dicatat/hadir/sakit/izin/alpa/terlambat, catatan, actual pengawas, room readiness.
- **States dan acceptance:** Presensi belum dicatat tidak dianggap absen; pergantian pengawas cek overlap; dirty warning.
- **Kontrak implementasi:** Actual vs planned dipisah; derive jumlah peserta/hadir dari records.

### UIX-35 · FinanceLedger & BudgetSummary

- **Referensi visual:** [Screenshot](screenshots/15-finance.png) · backlog induk `FIN-01` · P1.
- **Spesifikasi:** RAB versus realisasi, integer IDR, kategori, posting/void, kuitansi dan honor.
- **States dan acceptance:** Total ledger dan LPJ sama; posted tidak dapat dihapus; perhitungan honor hanya actual approved.
- **Kontrak implementasi:** Idempotency key, transaction reversal, audit, scope dan integer rupiah.

### UIX-36 · LPJOutline & NarrativeEditor

- **Referensi visual:** [Screenshot](screenshots/16-lpj.png) · backlog induk `LPJ-01` · P1.
- **Spesifikasi:** Outline bagian LPJ, narasi editable, derived readonly statistics dan manifest lampiran.
- **States dan acceptance:** Draft bisa disimpan; finalisasi memvalidasi angka/kelengkapan; output mencantumkan snapshot versi.
- **Kontrak implementasi:** Narrative tidak overwrite field derived; generated docs immutable.

### UIX-37 · ArchiveBrowser & BackupWizard

- **Referensi visual:** [Screenshot](screenshots/19-backup.png) · backlog induk `BAK-01` · P0.
- **Spesifikasi:** Arsip read-only, backup integrity, restore staged, overwrite confirmation.
- **States dan acceptance:** Restore korup gagal tanpa data loss; backup mencakup DB+assets; open/export tetap tersedia saat lisensi invalid.
- **Kontrak implementasi:** SQLite backup API, checksum manifest, path validation, atomic replace after confirmation.

### UIX-38 · LocalLicenseDialog

- **Referensi visual:** [Screenshot](screenshots/19-backup.png) · backlog induk `LIC-01` · P1.
- **Spesifikasi:** Impor file lisensi offline, lembaga, versi hak pakai, penjelasan expired/invalid.
- **States dan acceptance:** Invalid signature tidak memberi akses write; read/export/backup tetap berjalan; tidak ada telemetry.
- **Kontrak implementasi:** Public key embedded; private key tidak masuk repo/bundle; no hard hardware binding.
