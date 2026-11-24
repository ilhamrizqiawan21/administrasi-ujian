# Product requirements document
## Masalah dan pengguna
Panitia mengulang rekap peserta, pembagian ruang, jadwal pengawas, presensi, dokumen, pengumpulan soal, RAB dan LPJ pada setiap ujian. File Word/Excel terpisah menyebabkan salah salin dan dokumen tidak konsisten. Operator utama bekerja pada satu PC; ketua, sekretaris, bendahara dan kurikulum memberi data/validasi. Pengawas tidak wajib menginstal aplikasi. Versi awal satu pengguna aktif per database, bukan kolaborasi realtime. Bisa menyimpan beberapa profil lembaga terisolasi, tetapi lisensi dijual per lembaga; konfirmasi kebijakan sebelum release.

## Sasaran terukur (target uji, bukan klaim penjualan)
- Pilot 3 sekolah berbeda jenjang; 1 siklus ujian lengkap, dokumen diterima panitia tanpa edit struktural mayor.
- 100% peserta teralokasi tepat sekali per scope; tidak ada bentrok pengawas dan kapasitas terlampaui.
- Untuk dataset 500 peserta, 25 ruang, 40 pengawas, 30 sesi: optimasi maksimal 60 detik default, dengan status jelas jika belum optimal; 200 kartu peserta maksimal 60 detik pada mesin target setelah benchmark.
- Bandingkan waktu kerja manual vs aplikasi pada pilot (termasuk input, revisi dan pengecekan). Tidak ada klaim penghematan sebelum pengukuran.

## Ruang lingkup
P0: setup, master data/import, event, jadwal ujian & pengawas, pembagian ruang/denah, dokumen utama, template Word + kop, backup, installer pilot. P1: kepanitiaan, program kerja, task list, ekspedisi, presensi semua pihak, berita acara, susulan, RAB/realisasi/honor, LPJ, pengarsipan, branding, template kustom tanpa kode. P2: designer visual bebas untuk kartu/form, ekspor/merge lanjutan dan analitik tambahan. P0 sudah mencakup editor kop dan pemetaan placeholder; visual canvas lanjutan tidak wajib P0. Tidak membangun bank soal, CBT, koreksi LJK, LMS, Dapodik/EMIS sync, pengiriman WA, payroll, akuntansi BOS resmi, multi-PC sinkronisasi, tanda tangan elektronik tersertifikasi.

## Alur end-to-end
1. First run: pilih direktori data, profil dan jenjang; buat event dari preset atau custom; pilih mode kertas/CBT/praktik/hybrid; pilih tahun ajaran, semester, tanggal dan peserta.
2. Impor siswa, guru, kelas, mapel, ruang dari XLSX; mapping kolom, preview valid/invalid, deteksi duplikat, konfirmasi transaksi, unduh laporan baris gagal. NIS/NISN/NIP string; tidak mengubah leading zero; jika Excel sudah menghilangkan nol, tandai bukan menebak.
3. Bekukan snapshot peserta/guru/kelas/ruang/kop dan aturan. Nomor peserta unik per event; generator format configurable prefix/sequence/padding; reassign nomor setelah cetak harus memperingatkan dokumen basi.
4. Atur sesi, kelompok mapel, kalender, kapasitas, pengawas tersedia. Generate pembagian ruang dan denah; review, drag/swap, lock; generate pengawas; review dan publish lokal. Jadwal manual boleh, validator sama.
5. Atur panitia, timeline, jobdesc, program kerja, tugas PIC/deadline, ekspedisi perangkat ujian per mapel dan rombel, revisi, validasi, cetak naskah.
6. Document Center: pilih jenis, scope (event/tanggal/sesi/ruang/kelas/orang), template versi, data, kop, margin, preview, cetak/ekspor. Dokumen yang sudah diterbitkan disimpan snapshot/hash; perubahan sumber menandai stale.
7. Saat ujian: presensi peserta per sesi dan ruang, presensi pengawas aktual (pengganti), panitia per hari/shift, berita acara, kejadian, serah terima naskah/lembar jawaban, ujian susulan, ekspedisi nilai. Tidak hadir tidak disamakan dengan belum dicatat.
8. RAB, revisi, realisasi transaksi, kuitansi dan lampiran, perhitungan honor dari tugas aktual yang disetujui, kontrol pagu; evaluasi, LPJ Word/PDF; finalisasi dan arsip ZIP. Salin event lama hanya konfigurasi yang dipilih.

## Status & aturan
- Event: DRAFT → PREPARATION → READY → RUNNING → COMPLETED → ARCHIVED. READY memerlukan peserta, ruang, sesi, validasi tanpa konflik keras; checklist tambahan ditentukan pengguna. Mundur status dengan alasan, audit, invalidasi dokumen; ARCHIVED read-only, duplikasi atau reopen terotorisasi.
- Roster/schedule/seating: draft → validated → published → superseded; hasil generate selalu draft terpisah; publish atomik, cek revisi input; perubahan terhadap versi published membuat revisi baru, bukan overwrite.
- Ekspedisi: belum diterima → diterima → perlu revisi → valid → digandakan/siap (sesuai mode). Catat tanggal, petugas, versi dan berkas; invalidasi validasi ketika file diganti.
- Tasks: todo/in_progress/blocked/done; dependensi tanpa siklus; done memerlukan bukti bila dikonfigurasi. Status event tidak otomatis selesai hanya karena semua tugas done.
- Presensi peserta: unrecorded/hadir/sakit/izin/alpa/terlambat (terlambat dihitung hadir). Pengawas/panitia: hadir/tidak hadir/pengganti/izin sesuai konfigurasi; actual assignment dipisahkan dari rencana.
- Keuangan: draft → approved → posted → void (reversal, tidak hapus transaksi posted). Pagu warning atau blok sesuai aturan; tidak menganggap belanja otomatis sah menurut regulasi. Nilai rupiah integer, bukan float.

## Adaptabilitas tanpa kode
Nama lembaga, jenis ujian, label jenjang/tingkatan/rombel, semester, format nomor surat dan peserta, kolom ekstra, tata tertib, tanda tangan, kategori anggaran, role panitia, jenis dokumen, kop, preset layout, aturan solver (hard/soft yang diizinkan), toleransi, tugas dan ekspedisi configurable melalui form. Hindari hardcode kelas VII–IX. Preset bukan regulasi resmi; pengguna boleh mengganti. Extra fields bertipe string/date/int/enum dengan scope dan validation; tidak menjalankan script buatan pengguna.

## Lisensi dan dukungan
Rp150.000 per sekolah, sekali bayar. Pilot gratis sementara dinyatakan sejak awal. Default usulan: lisensi file ditandatangani asimetris offline, tidak mengikat hardware secara agresif, nama/id lembaga, edisi dan versi mayor; private key tidak pernah ikut installer/repo. Public key embedded. Jika lisensi hilang, data tetap dapat dibuka read-only/backup/export; tidak ada penghapusan data. Tidak menjanjikan anti-pembajakan absolut; tidak mengumpulkan identitas siswa untuk aktivasi. Putuskan grace period/dukungan/pemindahan sebelum rilis.

## Keputusan terbuka sebelum implementasi
Nama/brand final; OS minimum (Windows 11 x64 baseline, Windows 10 x64 best effort hanya jika versi masih kompatibel dan security support disadari); kebijakan satu/lebih profil per lisensi; approval peran lokal vs operator tunggal; format LPJ masing-masing pilot; batas data maksimum; apakah PDF Word harus pixel-identical (jika ya perlu renderer Word yang sah/teruji); aturan ekspor data pribadi. Catat di ADR, bukan asumsi tersembunyi.
