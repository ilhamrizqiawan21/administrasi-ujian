# Ujian Cerdas | Project inception kit
**Baseline 0.1 — 24 November 2026** · Status: rancangan, belum merupakan aplikasi produksi.

Aplikasi desktop administrasi ujian offline untuk SD/MI, SMP/MTs, SMA/MA, SMK, PKBM, pesantren dan lembaga lain. Harga target Rp150.000 per sekolah, sekali bayar untuk versi yang dibeli. Tidak ada kuota siswa, kegiatan atau cetak. Tidak membutuhkan akun cloud, API AI, ataupun koneksi internet. Source code proprietary/private. Kebijakan masa dukungan dan upgrade harus disepakati sebelum penjualan; usulan 12 bulan perbaikan versi, upgrade mayor terpisah.

## Mulai di sini
1. `docs/01-PRD.md` — tujuan, scope, alur, aturan dan kriteria rilis.
2. `docs/02-ARCHITECTURE.md`, `03-DATABASE.md`, `04-ALGORITHMS.md`, `05-DOCUMENTS.md` — desain teknis.
3. `design/DESIGN_SYSTEM.md` — turunan standar UI pengguna, `design/mockup.html` — prototipe offline yang dapat dibuka di browser (data sintetis; bukan aplikasi kerja).
   - `design/COMPONENT_SPEC.md` — 38 kontrak komponen, states, dan referensi layar; `design/visual-index.html` — galeri screenshot layar dan potongan komponen.
4. `backlog/TODO.md` — daftar tugas granular per komponen; `backlog/tasks.csv` — backlog yang sama untuk spreadsheet/issue tracker, ID stabil, prioritas, dependency, acceptance criteria. 206 issue utama, termasuk 60 dokumen; tambahan 38 subtask UI di `backlog/UI_COMPONENT_TODO.md` dan `backlog/ui-components.csv`.
5. `docs/10-BLUEPRINT.md` — visual maps (Mermaid); `docs/06-TESTING.md`, `07-RELEASE.md`, `08-ROADMAP.md`, `09-SECURITY.md` — quality gate, build dan distribusi.
6. `AGENTS.md`, `CLAUDE.md`, `GEMINI.md` dan `ai/` — instruksi agen, prompt kickoff, review, handoff.
7. `contracts/bridge.md`, `contracts/bridge.schema.json`, `fixtures/` — kontrak awal dan data sintetis untuk pengujian.

## Cara memulai repo
Ekstrak ZIP ke direktori kerja baru `ujian-cerdas`; git init; commit dokumen baseline; jadikan repo private. Jangan memulai semua modul bersamaan. Baca AGENTS.md, review keputusan produk, mulai spike FND-01. Implementasi dan versi dependency belum ditetapkan; validasi kompatibilitas Windows, pywebview, OR-Tools dan build sebelum mengunci versi.

## Prioritas
P0 = pilot wajib; P1 = rilis komersial v1 (termasuk semua kebutuhan operasional utama); P2 = pasca v1/lanjutan yang tidak memblokir pilot. Harga Rp150.000 tidak berarti semua P2 dijanjikan saat rilis. Jangan menjual fitur yang belum teruji.

## Sumber desain
Standar internal: https://github.com/ilhamrizqiawan21/standar-ui-project (main, tree SHA `87490c183b9d57b2600e3daa986171e84df4ab5c`, dibaca 24 Nov 2026). Paket ini menyimpan link dan keputusan turunan, bukan menduplikasi seluruh aturan global. Jika akses repo belum tersedia untuk agen, gunakan dokumen design system ini sebagai baseline sementara dan minta akses sebelum review UI akhir.

Referensi teknis: https://pyinstaller.org/en/stable/ ; https://github.com/r0x0r/pywebview/tree/master/docs/guide ; https://developers.google.com/optimization/scheduling/employee_scheduling ; https://developer.microsoft.com/microsoft-edge/webview2/ ; https://www.sqlite.org/backup.html . Verifikasi versi, lisensi dan platform ketika spike. Semua keputusan di paket ini adalah usulan desain untuk disetujui pemilik produk.
