# Solver specification — scheduling and seating
## Inputs, versions and feasibility
Semua input dibekukan sebagai revision: event, peserta dan group, ruang fisik/slot, sesi (tanggal + start/end + timezone lembaga), kebutuhan mapel per kelompok, availability guru, qualification dan locks. Normalisasi interval [start,end); sesi berbeda ID bisa overlap. Preflight: peserta eligible <= kapasitas total slot aktif per kelompok sesi; setiap kelompok mapel punya slot kandidat; kebutuhan pengawas vs kandidat per interval; fixed locks valid; tidak ada room/session duplikat; cek konfigurasi kelas/rombel. Tampilkan daftar konflik spesifik dan saran, tanpa diam-diam melonggarkan hard rules.

## Exam timetable
Decision `x[group,subject,session,room]` boolean hanya untuk kandidat layak. Alternatif MVP: operator input jadwal mapel per kelompok, validator + auto pengawas; P1 auto jadwal mapel. Hard: satu ujian untuk setiap kebutuhan; peserta tidak overlap; satu ruang tidak melayani dua paper terpisah pada interval yang sama kecuali explicit mixed group room yang memakai shared room-session; kapasitas dan mode ruang sesuai; waktu ujian cukup; kunci tidak berubah; libur/istirahat; ujian paralel lintas jenjang diperbolehkan jika tidak bentrok. Soft: batas ujian/hari, sebar mapel berat, preferensi jam, minim sesi kosong. Jangan menggabungkan kelas dengan mapel berbeda tanpa daftar paper per room-session.

## Invigilator solver
Setiap room-session punya required slots (utama, pendamping, proktor opsional). `x[t,k]` = 1 jika guru t ditugaskan slot k. Untuk tiap slot sum(x)=1; untuk pasangan interval overlap per guru sum<=1; unavailable/role incompatible/lock melarang kandidat; max per hari/total jika hard; avoid own class/subject configurable hard/soft, dengan data relasi guru-mapel-kelas. Soft: minim deviasi load dari target (gunakan integer scale; part-time target weighted), minim consecutive, preferensi, minim perubahan dari versi approved, distribusi pagi/siang. Cadangan bukan pengawas aktif dan tetap bebas bentrok jika ditetapkan per interval. Tampilkan workload min/max, daftar pelanggaran soft dan alasan. Solver time limit 60s configurable; status OPTIMAL/FEASIBLE/INFEASIBLE/UNKNOWN/MODEL_INVALID. FEASIBLE boleh draft dengan label belum optimal; UNKNOWN tanpa incumbent bukan hasil; jangan publish partial. Gunakan assumption literals untuk kelompok hard rules bila feasible di model; jika tidak, diagnosis melalui preflight dan rerun terarah; jangan menyatakan unsat core pasti minimal. Save seed, solver version, weights, runtime, input hash, objective, status; reproduksi best effort dengan single worker mode, tidak jamin lintas versi.

## Seating & allocation
Room layout grid/coordinates: desk has row/col, 1..n seats, disabled seats, accessible seats; adjacency graph horizontal/vertical dan opsional diagonal, termasuk antar kursi satu meja. Scope allocation stable whole event default atau per session-group configurable; peserta hanya duduk sekali dalam scope; slot unik, capacity derived dari enabled seats dan limit; room eligibility, accessible accommodation, locks, wajib pemisahan jika selected hard. Allocate dan seat secara joint pada dataset kecil atau two-stage dengan repair/iterative retry (jangan klaim optimal jika heuristic). Soft: sebar tingkat dan rombel, seimbangkan occupancy, penalize adjacency same grade/class, minimize gaps dan pindah kursi; tie-break seeded. Mode campur tingkat, campur rombel, berurutan, custom. Jika tingkat sama semua, explain impossible untuk strict mixed; mode soft boleh menghasilkan pasangan sama dan tampilkan count. Jangan memaksa random jika kebutuhan aksesibilitas bertentangan.

### Pseudocode
```
validate_input(snapshot)
candidates = filter_eligible(snapshot)
model = build_hard_constraints(candidates, locks)
model.minimize(weighted_soft_penalties)
result = solve(model, limit, seed)
if feasible: independently_validate(result, snapshot); save_draft(result)
else: return diagnostics_without_publishing()
review_and_publish(draft_id, expected_revision)
```
Manual swap/drag: keyboard alternatif pilih asal/tujuan; check slot valid, group constraints, occupancy, accessibility, locked; show impact, atomic swap, undo/redo via commands with expected revision. Never allow hard conflict. Change input after publish → draft revision, old documents marked stale, audit. Preview room colors use labels not color only. Print denah orientasi papan tulis/pengawas, nomor meja, nomor peserta/nama sesuai privacy setting, legend, pagination.

## Operations
Presensi planned vs actual; replacement must be eligible and no overlap; attendance counts derived from per-person statuses, unrecorded distinguished. Susulan creates linked session+eligibility; original absent stays absent. Honor uses approved actual assignment count × rate snapshot; unique source line prevents double count, adjustment via reversal. Money integer IDR; sum volume × rate with explicit rounding for decimal quantity, policy recorded.
