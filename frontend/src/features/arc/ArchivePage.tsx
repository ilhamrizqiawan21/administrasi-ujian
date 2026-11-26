import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Archive,
  Copy,
  Eye,
  PackageCheck,
  ShieldCheck,
  Trash2,
} from "lucide-react";
import type { ColumnDef } from "@tanstack/react-table";
import { DataTable } from "../../components/shared/DataTable";
import { Button, IconButton } from "../../components/ui/Button";
import { StatusIndicator, useToast } from "../../components/ui/Feedback";
import { CRUDModal } from "../../components/ui/Modal";
import { invokeBridge } from "../../lib/bridge";
import type {
  ArcEventDetailResponse,
  ArcEventItem,
  ArcFilterOption,
  ArcListResponse,
  ArcRetentionEvent,
  ArcRetentionPreviewResponse,
  ArcRetentionReviewResponse,
} from "./types";

interface ArchivePageProps {
  institutionId: string;
  onEventsChanged?: () => void;
}

function getErrMsg(err: unknown, fallback: string): string {
  return err instanceof Error ? err.message : fallback;
}

export function ArchivePage({ institutionId, onEventsChanged }: ArchivePageProps) {
  const { pushToast } = useToast();
  const [tab, setTab] = useState<"browser" | "retention">("browser");
  const [loading, setLoading] = useState(false);

  // Browser filters & data
  const [items, setItems] = useState<ArcEventItem[]>([]);
  const [years, setYears] = useState<ArcFilterOption[]>([]);
  const [examTypes, setExamTypes] = useState<ArcFilterOption[]>([]);
  const [yearFilter, setYearFilter] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [stateFilter, setStateFilter] = useState("");

  // Read-only detail & package export
  const [detail, setDetail] = useState<ArcEventDetailResponse | null>(null);
  const [showDetailModal, setShowDetailModal] = useState(false);
  const [showPackageModal, setShowPackageModal] = useState(false);
  const [pkgTarget, setPkgTarget] = useState<ArcEventItem | null>(null);
  const [includePii, setIncludePii] = useState(false);
  const [includeDocs, setIncludeDocs] = useState(true);

  // Duplicate modal
  const [dupTarget, setDupTarget] = useState<ArcEventItem | null>(null);
  const [dupTitle, setDupTitle] = useState("");
  const [dupYearId, setDupYearId] = useState("");
  const [dupSemester, setDupSemester] = useState("Ganjil");
  const [dupStartsOn, setDupStartsOn] = useState("2026-12-01");
  const [dupEndsOn, setDupEndsOn] = useState("2026-12-06");

  // Retention state
  const [minAgeDays, setMinAgeDays] = useState(365);
  const [retention, setRetention] = useState<ArcRetentionReviewResponse | null>(null);
  const [purgePreview, setPurgePreview] = useState<ArcRetentionPreviewResponse | null>(
    null,
  );
  const [purgeAuthBy, setPurgeAuthBy] = useState("");
  const [purgeConfirmTitle, setPurgeConfirmTitle] = useState("");

  const loadBrowser = useCallback(async () => {
    setLoading(true);
    try {
      const res = await invokeBridge<ArcListResponse>("arc.events.list", {
        institution_id: institutionId,
        year_id: yearFilter || null,
        exam_type_id: typeFilter || null,
        state: stateFilter || null,
      });
      setItems(res.items);
      setYears(res.years);
      setExamTypes(res.exam_types);
    } catch (err) {
      pushToast(getErrMsg(err, "Gagal memuat arsip kegiatan."), "error");
    } finally {
      setLoading(false);
    }
  }, [institutionId, yearFilter, typeFilter, stateFilter, pushToast]);

  const loadRetention = useCallback(async () => {
    setLoading(true);
    try {
      const res = await invokeBridge<ArcRetentionReviewResponse>(
        "arc.retention.review",
        {
          institution_id: institutionId,
          min_age_days: minAgeDays,
        },
      );
      setRetention(res);
    } catch (err) {
      pushToast(getErrMsg(err, "Gagal memuat tinjauan retensi."), "error");
    } finally {
      setLoading(false);
    }
  }, [institutionId, minAgeDays, pushToast]);

  useEffect(() => {
    if (tab === "browser") {
      void loadBrowser();
    } else {
      void loadRetention();
    }
  }, [tab, loadBrowser, loadRetention]);

  const openDetail = useCallback(
    async (examId: string) => {
      try {
        const res = await invokeBridge<ArcEventDetailResponse>("arc.events.detail", {
          institution_id: institutionId,
          exam_id: examId,
        });
        setDetail(res);
        setShowDetailModal(true);
      } catch (err) {
        pushToast(getErrMsg(err, "Gagal memuat detail arsip."), "error");
      }
    },
    [institutionId, pushToast],
  );

  const handleArchiveEvent = useCallback(
    async (row: ArcEventItem) => {
      try {
        await invokeBridge("arc.events.archive", {
          institution_id: institutionId,
          exam_id: row.id,
        });
        pushToast(`Kegiatan "${row.title}" diarsipkan (read-only).`, "success");
        await loadBrowser();
        onEventsChanged?.();
      } catch (err) {
        pushToast(getErrMsg(err, "Gagal mengarsipkan kegiatan."), "error");
      }
    },
    [institutionId, loadBrowser, onEventsChanged, pushToast],
  );

  const handleExportPackage = async () => {
    if (!pkgTarget) return;
    try {
      const res = await invokeBridge<{ file_path: string; file_count: number }>(
        "arc.package.export",
        {
          institution_id: institutionId,
          exam_id: pkgTarget.id,
          include_personal_info: includePii,
          include_documents: includeDocs,
        },
      );
      pushToast(
        `Paket arsip ZIP dibuat (${res.file_count} file): ${res.file_path}`,
        "success",
      );
      setShowPackageModal(false);
      await loadBrowser();
    } catch (err) {
      pushToast(getErrMsg(err, "Gagal membuat paket arsip ZIP."), "error");
    }
  };

  const handleVerifyPackage = async (packageId: string) => {
    try {
      const res = await invokeBridge<{ valid: boolean; checked_files: number }>(
        "arc.package.verify",
        {
          institution_id: institutionId,
          package_id: packageId,
        },
      );
      pushToast(
        res.valid
          ? `Manifest valid (${res.checked_files} file terverifikasi).`
          : "Verifikasi ZIP menemukan ketidakcocokan hash.",
        res.valid ? "success" : "error",
      );
    } catch (err) {
      pushToast(getErrMsg(err, "Gagal memverifikasi paket arsip."), "error");
    }
  };

  const handleDuplicate = async () => {
    if (!dupTarget) return;
    try {
      const res = await invokeBridge<{ title: string }>("arc.events.duplicate", {
        institution_id: institutionId,
        source_exam_id: dupTarget.id,
        target_year_id: dupYearId || dupTarget.year_id,
        title: dupTitle.trim(),
        semester_label: dupSemester.trim(),
        starts_on: dupStartsOn,
        ends_on: dupEndsOn,
      });
      pushToast(
        `Kegiatan "${res.title}" diduplikasi sebagai DRAFT baru.`,
        "success",
      );
      setDupTarget(null);
      await loadBrowser();
      onEventsChanged?.();
    } catch (err) {
      pushToast(getErrMsg(err, "Gagal menduplikasi kegiatan."), "error");
    }
  };

  const openRetentionPreview = useCallback(
    async (examId: string) => {
      try {
        const res = await invokeBridge<ArcRetentionPreviewResponse>(
          "arc.retention.preview",
          {
            institution_id: institutionId,
            exam_id: examId,
          },
        );
        setPurgePreview(res);
        setPurgeAuthBy("");
        setPurgeConfirmTitle("");
      } catch (err) {
        pushToast(getErrMsg(err, "Gagal memuat pratinjau dampak."), "error");
      }
    },
    [institutionId, pushToast],
  );

  const handlePurge = async () => {
    if (!purgePreview) return;
    try {
      const res = await invokeBridge<{
        purged_title: string;
        backup: { file_path: string };
      }>("arc.retention.purge", {
        institution_id: institutionId,
        exam_id: purgePreview.exam_id,
        authorized_by: purgeAuthBy.trim(),
        confirm_title: purgeConfirmTitle.trim(),
      });
      pushToast(
        `Kegiatan "${res.purged_title}" dihapus setelah backup (${res.backup.file_path}).`,
        "success",
      );
      setPurgePreview(null);
      await loadRetention();
      onEventsChanged?.();
    } catch (err) {
      pushToast(getErrMsg(err, "Gagal menghapus kegiatan."), "error");
    }
  };

  const browserColumns = useMemo<ColumnDef<ArcEventItem>[]>(
    () => [
      { accessorKey: "title", header: "Kegiatan" },
      { accessorKey: "year_label", header: "Tahun Ajaran" },
      { accessorKey: "exam_type_label", header: "Jenis" },
      { accessorKey: "state", header: "Status" },
      {
        accessorKey: "package_count",
        header: "Paket ZIP",
        cell: ({ row }) => <span>{row.original.package_count}</span>,
      },
      {
        id: "actions",
        header: "Aksi",
        cell: ({ row }) => {
          const item = row.original;
          return (
            <div className="row-actions-group">
              <IconButton
                label="Lihat detail read-only"
                icon={<Eye size={16} aria-hidden="true" />}
                onClick={() => void openDetail(item.id)}
              />
              {item.state === "COMPLETED" && (
                <IconButton
                  label="Arsipkan kegiatan"
                  icon={<Archive size={16} aria-hidden="true" />}
                  onClick={() => void handleArchiveEvent(item)}
                />
              )}
              <IconButton
                label="Ekspor paket arsip ZIP"
                icon={<PackageCheck size={16} aria-hidden="true" />}
                onClick={() => {
                  setPkgTarget(item);
                  setIncludePii(false);
                  setIncludeDocs(true);
                  setShowPackageModal(true);
                }}
              />
              <IconButton
                label="Duplikasi kebijakan ke draf baru"
                icon={<Copy size={16} aria-hidden="true" />}
                onClick={() => {
                  setDupTarget(item);
                  setDupTitle(`${item.title} (Salinan)`);
                  setDupYearId(years[0]?.id ?? item.year_id);
                  setDupSemester(item.semester_label);
                }}
              />
            </div>
          );
        },
      },
    ],
    [handleArchiveEvent, openDetail, years],
  );

  const retentionColumns = useMemo<ColumnDef<ArcRetentionEvent>[]>(
    () => [
      { accessorKey: "title", header: "Kegiatan" },
      { accessorKey: "year_label", header: "Tahun" },
      { accessorKey: "state", header: "Status" },
      { accessorKey: "ends_on", header: "Tanggal Selesai" },
      {
        accessorKey: "age_days",
        header: "Umur (Hari)",
        cell: ({ row }) => <span>{row.original.age_days} hari</span>,
      },
      {
        id: "eligible",
        header: "Kelayakan",
        cell: ({ row }) => (
          <StatusIndicator
            tone={row.original.eligible_for_purge ? "warning" : "neutral"}
            label={row.original.eligible_for_purge ? "Siap Retensi" : "Aktif/Baru"}
          />
        ),
      },
      {
        id: "actions",
        header: "Aksi",
        cell: ({ row }) => (
          <div className="row-actions-group">
            <IconButton
              label="Pratinjau dampak & hapus"
              variant="destructive"
              icon={<Trash2 size={16} aria-hidden="true" />}
              onClick={() => void openRetentionPreview(row.original.id)}
            />
          </div>
        ),
      },
    ],
    [openRetentionPreview],
  );

  return (
    <div className="page-stack">
      <div className="card-surface toolbar-row">
        <div className="tab-group">
          <Button
            variant={tab === "browser" ? "primary" : "secondary"}
            size="sm"
            onClick={() => setTab("browser")}
          >
            1. Browser Arsip &amp; Paket
          </Button>
          <Button
            variant={tab === "retention" ? "primary" : "secondary"}
            size="sm"
            onClick={() => setTab("retention")}
          >
            2. Retensi &amp; Pembersihan
          </Button>
        </div>
        {loading && <StatusIndicator tone="neutral" label="Memuat data..." />}
      </div>

      {tab === "browser" ? (
        <div className="page-stack">
          <div className="card-surface filter-grid">
            <label className="field-block">
              <span>Tahun Ajaran</span>
              <select
                value={yearFilter}
                onChange={(e) => setYearFilter(e.target.value)}
              >
                <option value="">Semua Tahun</option>
                {years.map((y) => (
                  <option key={y.id} value={y.id}>
                    {y.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="field-block">
              <span>Jenis Ujian</span>
              <select
                value={typeFilter}
                onChange={(e) => setTypeFilter(e.target.value)}
              >
                <option value="">Semua Jenis</option>
                {examTypes.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="field-block">
              <span>Status Kegiatan</span>
              <select
                value={stateFilter}
                onChange={(e) => setStateFilter(e.target.value)}
              >
                <option value="">Semua Status</option>
                <option value="ARCHIVED">ARCHIVED</option>
                <option value="COMPLETED">COMPLETED</option>
                <option value="DRAFT">DRAFT</option>
              </select>
            </label>
          </div>

          <DataTable
            data={items}
            columns={browserColumns}
            searchPlaceholder="Cari judul atau semester..."
            getCellAlign={(id) =>
              id === "package_count" || id === "state" ? "center" : "left"
            }
          />
        </div>
      ) : (
        <div className="page-stack">
          <div className="card-surface toolbar-row">
            <label className="field-inline">
              <span>Batas Umur Minimum (hari)</span>
              <input
                type="number"
                min={0}
                value={minAgeDays}
                onChange={(e) =>
                  setMinAgeDays(Math.max(0, Number(e.target.value) || 0))
                }
              />
            </label>
            {retention?.last_good_backup ? (
              <StatusIndicator
                tone="success"
                label={`Backup Terakhir Terjaga: ${retention.last_good_backup.file_path}`}
              />
            ) : (
              <StatusIndicator
                tone="warning"
                label="Belum ada backup retensi; backup otomatis dibuat sebelum penghapusan."
              />
            )}
          </div>

          <DataTable
            data={retention?.events ?? []}
            columns={retentionColumns}
            searchPlaceholder="Cari kegiatan retensi..."
            getCellAlign={(id) =>
              id === "age_days" || id === "state" ? "center" : "left"
            }
          />
        </div>
      )}

      <CRUDModal
        open={showDetailModal && detail !== null}
        title={detail ? `Detail Arsip: ${detail.exam.title}` : "Detail Arsip"}
        onClose={() => setShowDetailModal(false)}
        cancelLabel="Tutup"
      >
        {detail && (
          <div className="page-stack">
            <p>
              <strong>Status:</strong> {detail.exam.state}{" "}
              {detail.exam.is_archived ? "(Read-only terkunci)" : ""}
            </p>
            <p>
              <strong>Periode:</strong> {detail.exam.starts_on} s.d.{" "}
              {detail.exam.ends_on} ({detail.exam.year_label})
            </p>
            <div className="summary-grid">
              <span>Peserta: {detail.counts.participants}</span>
              <span>Ruang: {detail.counts.rooms}</span>
              <span>Mapel: {detail.counts.subjects}</span>
              <span>Dokumen: {detail.counts.documents}</span>
              <span>LPJ: {detail.counts.lpj_versions}</span>
              <span>Jurnal Keuangan: {detail.counts.ledger_entries}</span>
            </div>
            <div>
              <h4>Paket ZIP Terdaftar ({detail.packages.length})</h4>
              {detail.packages.length === 0 ? (
                <p>Belum ada paket arsip ZIP.</p>
              ) : (
                detail.packages.map((p) => (
                  <div key={p.id} className="toolbar-row">
                    <span>
                      {p.file_path} ({p.file_count} file)
                    </span>
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={() => void handleVerifyPackage(p.id)}
                    >
                      <ShieldCheck size={14} aria-hidden="true" />
                      Verifikasi Hash
                    </Button>
                  </div>
                ))
              )}
            </div>
          </div>
        )}
      </CRUDModal>

      <CRUDModal
        open={showPackageModal && pkgTarget !== null}
        title="Ekspor Paket Arsip ZIP"
        onClose={() => setShowPackageModal(false)}
        onSubmit={() => void handleExportPackage()}
        submitLabel="Buat Paket ZIP"
      >
        <div className="page-stack">
          <p>
            Kegiatan: <strong>{pkgTarget?.title}</strong>
          </p>
          <label className="checkbox-row">
            <input
              type="checkbox"
              checked={includeDocs}
              onChange={(e) => setIncludeDocs(e.target.checked)}
            />
            <span>Sertakan file dokumen hasil generate</span>
          </label>
          <label className="checkbox-row">
            <input
              type="checkbox"
              checked={includePii}
              onChange={(e) => setIncludePii(e.target.checked)}
            />
            <span>Sertakan daftar identitas peserta/petugas (opsional)</span>
          </label>
        </div>
      </CRUDModal>

      <CRUDModal
        open={dupTarget !== null}
        title="Duplikasi Kebijakan ke Kegiatan Baru"
        onClose={() => setDupTarget(null)}
        onSubmit={() => void handleDuplicate()}
        submitLabel="Duplikasi sebagai Draf"
      >
        <div className="page-stack">
          <p>
            Menyalin kebijakan, ruang, mapel, struktur panitia, kategori anggaran, dan
            aturan honor tanpa menyalin data aktual/riwayat peserta.
          </p>
          <label className="field-block">
            <span>Judul Kegiatan Baru</span>
            <input
              value={dupTitle}
              onChange={(e) => setDupTitle(e.target.value)}
            />
          </label>
          <label className="field-block">
            <span>Tahun Ajaran Tujuan</span>
            <select
              value={dupYearId}
              onChange={(e) => setDupYearId(e.target.value)}
            >
              {years.map((y) => (
                <option key={y.id} value={y.id}>
                  {y.label}
                </option>
              ))}
            </select>
          </label>
          <label className="field-block">
            <span>Semester</span>
            <input
              value={dupSemester}
              onChange={(e) => setDupSemester(e.target.value)}
            />
          </label>
          <div className="filter-grid">
            <label className="field-block">
              <span>Tanggal Mulai</span>
              <input
                type="date"
                value={dupStartsOn}
                onChange={(e) => setDupStartsOn(e.target.value)}
              />
            </label>
            <label className="field-block">
              <span>Tanggal Selesai</span>
              <input
                type="date"
                value={dupEndsOn}
                onChange={(e) => setDupEndsOn(e.target.value)}
              />
            </label>
          </div>
        </div>
      </CRUDModal>

      <CRUDModal
        open={purgePreview !== null}
        title="Pratinjau Dampak &amp; Penghapusan Retensi"
        onClose={() => setPurgePreview(null)}
        onSubmit={purgePreview?.can_purge ? () => void handlePurge() : undefined}
        submitLabel="Backup & Hapus Permanen"
      >
        {purgePreview && (
          <div className="page-stack">
            <p>
              Kegiatan: <strong>{purgePreview.exam_title}</strong> (Total{" "}
              {purgePreview.total_affected_rows} baris terdampak).
            </p>
            {purgePreview.blockers.length > 0 && (
              <StatusIndicator
                tone="destructive"
                label={purgePreview.blockers.join(" ")}
              />
            )}
            <label className="field-block">
              <span>Pejabat / Operator Otorisasi</span>
              <input
                value={purgeAuthBy}
                onChange={(e) => setPurgeAuthBy(e.target.value)}
                placeholder="Nama pejabat yang mengotorisasi"
              />
            </label>
            <label className="field-block">
              <span>Ketik ulang judul kegiatan untuk konfirmasi</span>
              <input
                value={purgeConfirmTitle}
                onChange={(e) => setPurgeConfirmTitle(e.target.value)}
                placeholder={purgePreview.exam_title}
              />
            </label>
          </div>
        )}
      </CRUDModal>
    </div>
  );
}
