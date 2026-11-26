import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ArchiveRestore,
  DatabaseBackup,
  RefreshCw,
  ShieldCheck,
  Wrench,
} from "lucide-react";
import type { ColumnDef } from "@tanstack/react-table";
import { DataTable } from "../../components/shared/DataTable";
import { Button, IconButton } from "../../components/ui/Button";
import { StatusIndicator, useToast } from "../../components/ui/Feedback";
import { CRUDModal } from "../../components/ui/Modal";
import { invokeBridge } from "../../lib/bridge";
import type {
  BackupRecordItem,
  BackupScheduleItem,
  RecoveryDiagnostics,
  RestorePreviewResult,
} from "./types";

interface BackupPageProps {
  institutionId: string;
  onRestored?: () => void;
}

function getErrMsg(err: unknown, fallback: string): string {
  return err instanceof Error ? err.message : fallback;
}

export function BackupPage({ institutionId, onRestored }: BackupPageProps) {
  const { pushToast } = useToast();
  const [tab, setTab] = useState<"backups" | "schedule" | "recovery">("backups");
  const [loading, setLoading] = useState(false);

  // Backups & Restore
  const [backups, setBackups] = useState<BackupRecordItem[]>([]);
  const [restorePreview, setRestorePreview] = useState<RestorePreviewResult | null>(
    null,
  );
  const [manualPath, setManualPath] = useState("");

  // Schedule
  const [schedule, setSchedule] = useState<BackupScheduleItem | null>(null);
  const [autoStartup, setAutoStartup] = useState(true);
  const [autoClose, setAutoClose] = useState(true);
  const [retentionCount, setRetentionCount] = useState(7);

  // Recovery
  const [diag, setDiag] = useState<RecoveryDiagnostics | null>(null);

  const loadBackups = useCallback(async () => {
    setLoading(true);
    try {
      const res = await invokeBridge<{ items: BackupRecordItem[] }>("bak.list", {
        institution_id: institutionId,
      });
      setBackups(res.items);
    } catch (err) {
      pushToast(getErrMsg(err, "Gagal memuat daftar backup."), "error");
    } finally {
      setLoading(false);
    }
  }, [institutionId, pushToast]);

  const loadSchedule = useCallback(async () => {
    setLoading(true);
    try {
      const res = await invokeBridge<BackupScheduleItem>("bak.schedule.get", {
        institution_id: institutionId,
      });
      setSchedule(res);
      setAutoStartup(res.auto_on_startup);
      setAutoClose(res.auto_on_close);
      setRetentionCount(res.retention_count);
    } catch (err) {
      pushToast(getErrMsg(err, "Gagal memuat jadwal backup."), "error");
    } finally {
      setLoading(false);
    }
  }, [institutionId, pushToast]);

  const loadRecovery = useCallback(async () => {
    setLoading(true);
    try {
      const res = await invokeBridge<RecoveryDiagnostics>(
        "bak.recovery.diagnose",
        { institution_id: institutionId },
      );
      setDiag(res);
    } catch (err) {
      pushToast(getErrMsg(err, "Gagal memuat diagnostik pemulihan."), "error");
    } finally {
      setLoading(false);
    }
  }, [institutionId, pushToast]);

  useEffect(() => {
    if (tab === "backups") void loadBackups();
    else if (tab === "schedule") void loadSchedule();
    else void loadRecovery();
  }, [tab, loadBackups, loadSchedule, loadRecovery]);

  const handleCreateBackup = async () => {
    try {
      const res = await invokeBridge<BackupRecordItem>("bak.create", {
        institution_id: institutionId,
        kind: "manual",
      });
      pushToast(`Backup ZIP berhasil dibuat: ${res.file_path}`, "success");
      await loadBackups();
    } catch (err) {
      pushToast(getErrMsg(err, "Gagal membuat backup."), "error");
    }
  };

  const handleVerify = useCallback(
    async (backupId: string) => {
      try {
        const res = await invokeBridge<{ valid: boolean; errors: string[] }>(
          "bak.verify",
          { institution_id: institutionId, backup_id: backupId },
        );
        pushToast(
          res.valid
            ? "Backup valid: checksum dan integritas SQLite terverifikasi."
            : `Backup bermasalah: ${res.errors.join("; ")}`,
          res.valid ? "success" : "error",
        );
      } catch (err) {
        pushToast(getErrMsg(err, "Gagal memverifikasi backup."), "error");
      }
    },
    [institutionId, pushToast],
  );

  const handlePreviewRestore = useCallback(
    async (filePath: string) => {
      try {
        const res = await invokeBridge<RestorePreviewResult>(
          "bak.restore.preview",
          { institution_id: institutionId, file_path: filePath },
        );
        setRestorePreview(res);
      } catch (err) {
        pushToast(getErrMsg(err, "Gagal memvalidasi file backup."), "error");
      }
    },
    [institutionId, pushToast],
  );

  const handleApplyRestore = async () => {
    if (!restorePreview) return;
    try {
      await invokeBridge("bak.restore.apply", {
        institution_id: institutionId,
        file_path: restorePreview.file_path,
      });
      pushToast(
        "Restore berhasil diterapkan dengan backup pra-restore otomatis.",
        "success",
      );
      setRestorePreview(null);
      await loadBackups();
      onRestored?.();
    } catch (err) {
      pushToast(getErrMsg(err, "Gagal menerapkan restore."), "error");
    }
  };

  const handleSaveSchedule = async () => {
    try {
      const res = await invokeBridge<BackupScheduleItem>("bak.schedule.save", {
        institution_id: institutionId,
        auto_on_startup: autoStartup,
        auto_on_close: autoClose,
        retention_count: retentionCount,
      });
      setSchedule(res);
      pushToast("Pengaturan jadwal backup disimpan.", "success");
    } catch (err) {
      pushToast(getErrMsg(err, "Gagal menyimpan jadwal backup."), "error");
    }
  };

  const handleRunScheduled = async () => {
    try {
      const res = await invokeBridge<{ status: string; pruned_count: number }>(
        "bak.schedule.run",
        { institution_id: institutionId, trigger: "startup" },
      );
      pushToast(
        `Backup terjadwal selesai (${res.status}), ${res.pruned_count} arsip lama dipangkas.`,
        res.status === "ok" ? "success" : "error",
      );
      await loadSchedule();
    } catch (err) {
      pushToast(getErrMsg(err, "Gagal menjalankan backup terjadwal."), "error");
    }
  };

  const handleRepair = async () => {
    try {
      const res = await invokeBridge<{
        cleaned_jobs: number;
        cleaned_temp_files: number;
        diagnostics: RecoveryDiagnostics;
      }>("bak.recovery.repair", {
        institution_id: institutionId,
        clean_temp_files: true,
        mark_interrupted_jobs: true,
      });
      setDiag(res.diagnostics);
      pushToast(
        `Pemulihan selesai: ${res.cleaned_jobs} job terhenti, ${res.cleaned_temp_files} file sementara dibersihkan.`,
        "success",
      );
    } catch (err) {
      pushToast(getErrMsg(err, "Gagal menjalankan pemulihan."), "error");
    }
  };

  const columns = useMemo<ColumnDef<BackupRecordItem>[]>(
    () => [
      { accessorKey: "file_path", header: "File Backup" },
      { accessorKey: "kind", header: "Jenis" },
      {
        accessorKey: "byte_size",
        header: "Ukuran",
        cell: ({ row }) => (
          <span>{Math.max(1, Math.round(row.original.byte_size / 1024))} KB</span>
        ),
      },
      {
        accessorKey: "status",
        header: "Status",
        cell: ({ row }) => (
          <StatusIndicator
            tone={row.original.status === "valid" ? "success" : "destructive"}
            label={row.original.status}
          />
        ),
      },
      {
        id: "actions",
        header: "Aksi",
        cell: ({ row }) => (
          <div className="row-actions-group">
            <IconButton
              label="Verifikasi checksum & integritas"
              icon={<ShieldCheck size={16} aria-hidden="true" />}
              onClick={() => void handleVerify(row.original.id)}
            />
            <IconButton
              label="Wizard Restore dari backup ini"
              icon={<ArchiveRestore size={16} aria-hidden="true" />}
              onClick={() => void handlePreviewRestore(row.original.file_path)}
            />
          </div>
        ),
      },
    ],
    [handlePreviewRestore, handleVerify],
  );

  return (
    <div className="page-stack">
      <div className="card-surface toolbar-row">
        <div className="tab-group">
          <Button
            variant={tab === "backups" ? "primary" : "secondary"}
            size="sm"
            onClick={() => setTab("backups")}
          >
            1. Backup &amp; Restore Wizard
          </Button>
          <Button
            variant={tab === "schedule" ? "primary" : "secondary"}
            size="sm"
            onClick={() => setTab("schedule")}
          >
            2. Jadwal &amp; Retensi
          </Button>
          <Button
            variant={tab === "recovery" ? "primary" : "secondary"}
            size="sm"
            onClick={() => setTab("recovery")}
          >
            3. Diagnostik &amp; Pemulihan
          </Button>
        </div>
        {loading && <StatusIndicator tone="neutral" label="Memuat data..." />}
      </div>

      {tab === "backups" && (
        <div className="page-stack">
          <div className="card-surface toolbar-row">
            <Button variant="primary" onClick={() => void handleCreateBackup()}>
              <DatabaseBackup size={16} aria-hidden="true" />
              Buat Backup Sekarang
            </Button>
            <div className="toolbar-row">
              <input
                value={manualPath}
                onChange={(e) => setManualPath(e.target.value)}
                placeholder="Path ZIP backup (mis. backups/...)"
              />
              <Button
                variant="secondary"
                disabled={!manualPath.trim()}
                onClick={() => void handlePreviewRestore(manualPath.trim())}
              >
                Pratinjau Restore
              </Button>
            </div>
          </div>

          <DataTable
            data={backups}
            columns={columns}
            searchPlaceholder="Cari file atau jenis backup..."
            getCellAlign={(id) =>
              id === "status" || id === "byte_size" ? "center" : "left"
            }
          />
        </div>
      )}

      {tab === "schedule" && (
        <div className="card-surface page-stack">
          <label className="checkbox-row">
            <input
              type="checkbox"
              checked={autoStartup}
              onChange={(e) => setAutoStartup(e.target.checked)}
            />
            <span>Backup otomatis saat aplikasi dibuka</span>
          </label>
          <label className="checkbox-row">
            <input
              type="checkbox"
              checked={autoClose}
              onChange={(e) => setAutoClose(e.target.checked)}
            />
            <span>Backup otomatis saat aplikasi ditutup</span>
          </label>
          <label className="field-block">
            <span>Jumlah salinan backup valid yang dipertahankan</span>
            <input
              type="number"
              min={1}
              max={365}
              value={retentionCount}
              onChange={(e) =>
                setRetentionCount(Math.max(1, Number(e.target.value) || 1))
              }
            />
          </label>
          {schedule?.last_status === "failed" && (
            <StatusIndicator
              tone="destructive"
              label={`Backup terakhir gagal: ${schedule.last_error}`}
            />
          )}
          <div className="toolbar-row">
            <Button variant="primary" onClick={() => void handleSaveSchedule()}>
              Simpan Jadwal
            </Button>
            <Button variant="secondary" onClick={() => void handleRunScheduled()}>
              <RefreshCw size={14} aria-hidden="true" />
              Jalankan Backup Terjadwal
            </Button>
          </div>
        </div>
      )}

      {tab === "recovery" && diag && (
        <div className="card-surface page-stack">
          <div className="toolbar-row">
            <StatusIndicator
              tone={diag.healthy ? "success" : "warning"}
              label={
                diag.healthy
                  ? "Workspace Sehat"
                  : "Perlu Pembersihan / Pemulihan"
              }
            />
            <Button variant="primary" onClick={() => void handleRepair()}>
              <Wrench size={14} aria-hidden="true" />
              Bersihkan Job Terhenti &amp; File Sementara
            </Button>
          </div>
          <div className="summary-grid">
            <span>Integritas SQLite: {diag.integrity_ok ? "OK" : "Gagal"}</span>
            <span>Foreign Keys: {diag.foreign_keys_ok ? "OK" : "Gagal"}</span>
            <span>Job Terhenti: {diag.interrupted_jobs.length}</span>
            <span>File Sementara: {diag.temp_files.length}</span>
          </div>
          <div>
            <h4>Panduan Pemulihan</h4>
            <ul>
              {diag.guidance.map((g, idx) => (
                <li key={idx}>{g}</li>
              ))}
            </ul>
          </div>
        </div>
      )}

      <CRUDModal
        open={restorePreview !== null}
        title="Wizard Restore Backup"
        onClose={() => setRestorePreview(null)}
        onSubmit={
          restorePreview?.can_restore ? () => void handleApplyRestore() : undefined
        }
        submitLabel="Backup Saat Ini &amp; Terapkan Restore"
      >
        {restorePreview && (
          <div className="page-stack">
            <p>
              File: <strong>{restorePreview.file_path}</strong>
            </p>
            <StatusIndicator
              tone={restorePreview.can_restore ? "success" : "destructive"}
              label={
                restorePreview.can_restore
                  ? "Validasi hash, path, dan integritas SQLite lulus"
                  : restorePreview.errors.join("; ")
              }
            />
            <div className="summary-grid">
              <span>Lembaga: {restorePreview.counts.institutions ?? 0}</span>
              <span>Siswa: {restorePreview.counts.students ?? 0}</span>
              <span>Pegawai: {restorePreview.counts.staff ?? 0}</span>
              <span>Kegiatan: {restorePreview.counts.exams ?? 0}</span>
            </div>
          </div>
        )}
      </CRUDModal>
    </div>
  );
}
