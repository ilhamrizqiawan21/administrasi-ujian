import { useCallback, useEffect, useMemo, useState } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import { Plus, RotateCcw } from "lucide-react";
import { DataTable } from "../../components/shared/DataTable";
import { RowActions } from "../../components/shared/RowActions";
import { Button } from "../../components/ui/Button";
import { useToast } from "../../components/ui/Feedback";
import {
  IdentifierField,
  SelectField,
  TextField,
} from "../../components/ui/FormFields";
import { ConfirmDialog, CRUDModal } from "../../components/ui/Modal";
import { invokeBridge } from "../../lib/bridge";
import type {
  AcademicYear,
  ExamTypeItem,
  Institution,
  LevelItem,
  NumberPolicyConfig,
  TypedSettingsConfig,
} from "./types";

type SettingsTab = "institution" | "levels" | "exam_types" | "numbering" | "config";

export interface SettingsPageProps {
  institution: Institution;
  levelPresets: Record<string, string[]>;
  onInstitutionUpdated: (inst: Institution) => void;
  onAddInstitution: () => void;
}

export function SettingsPage({
  institution,
  levelPresets,
  onInstitutionUpdated,
  onAddInstitution,
}: SettingsPageProps) {
  const { pushToast } = useToast();
  const [tab, setTab] = useState<SettingsTab>("institution");

  const [instForm, setInstForm] = useState({
    name: institution.name,
    short_name: institution.short_name ?? "",
    npsn: institution.npsn ?? "",
    nsm: institution.nsm ?? "",
    address: institution.address ?? "",
    timezone: institution.timezone,
  });

  const [levels, setLevels] = useState<LevelItem[]>([]);
  const [years, setYears] = useState<AcademicYear[]>([]);
  const [examTypes, setExamTypes] = useState<ExamTypeItem[]>([]);
  const [policy, setPolicy] = useState<NumberPolicyConfig | null>(null);
  const [policyRev, setPolicyRev] = useState(0);
  const [previewSample, setPreviewSample] = useState<{
    participant_samples: string[];
    document_samples: string[];
  } | null>(null);

  const [settings, setSettings] = useState<TypedSettingsConfig | null>(null);
  const [settingsRev, setSettingsRev] = useState(0);

  const [levelModalOpen, setLevelModalOpen] = useState(false);
  const [newLevelLabel, setNewLevelLabel] = useState("");
  const [examTypeModalOpen, setExamTypeModalOpen] = useState(false);
  const [newExamType, setNewExamType] = useState({
    code: "",
    label: "",
    mode_default: "paper" as "paper" | "cbt" | "practice" | "hybrid",
  });
  const [resetConfirmOpen, setResetConfirmOpen] = useState(false);

  const loadAll = useCallback(async () => {
    try {
      const [lvlRes, yrRes, etRes, npRes, stRes] = await Promise.all([
        invokeBridge<{ items: LevelItem[] }>("cfg.levels.list", {
          institution_id: institution.id,
        }),
        invokeBridge<{ items: AcademicYear[] }>("cfg.years.list", {
          institution_id: institution.id,
        }),
        invokeBridge<{ items: ExamTypeItem[] }>("cfg.exam_types.list", {
          institution_id: institution.id,
        }),
        invokeBridge<{ policy: NumberPolicyConfig; revision: number }>(
          "cfg.number_policy.get",
          { institution_id: institution.id }
        ),
        invokeBridge<{ settings: TypedSettingsConfig; revision: number }>(
          "cfg.settings.get",
          { institution_id: institution.id }
        ),
      ]);
      setLevels(lvlRes.items);
      setYears(yrRes.items);
      setExamTypes(etRes.items);
      setPolicy(npRes.policy);
      setPolicyRev(npRes.revision);
      setSettings(stRes.settings);
      setSettingsRev(stRes.revision);
    } catch (err: unknown) {
      pushToast(
        err instanceof Error ? err.message : "Gagal memuat konfigurasi.",
        "error"
      );
    }
  }, [institution.id, pushToast]);

  useEffect(() => {
    setInstForm({
      name: institution.name,
      short_name: institution.short_name ?? "",
      npsn: institution.npsn ?? "",
      nsm: institution.nsm ?? "",
      address: institution.address ?? "",
      timezone: institution.timezone,
    });
    void loadAll();
  }, [institution, loadAll]);

  async function saveInstitutionProfile() {
    try {
      const res = await invokeBridge<{ institution: Institution }>(
        "cfg.institutions.save",
        {
          id: institution.id,
          expected_revision: institution.revision,
          name: instForm.name,
          short_name: instForm.short_name || null,
          npsn: instForm.npsn || null,
          nsm: instForm.nsm || null,
          address: instForm.address || null,
          timezone: instForm.timezone,
        }
      );
      onInstitutionUpdated(res.institution);
      pushToast("Profil lembaga diperbarui.", "success");
    } catch (err: unknown) {
      pushToast(err instanceof Error ? err.message : "Gagal menyimpan.", "error");
    }
  }

  async function handleAddLevel() {
    try {
      await invokeBridge("cfg.levels.save", {
        institution_id: institution.id,
        label: newLevelLabel,
        sort_order: levels.length + 1,
      });
      setNewLevelLabel("");
      setLevelModalOpen(false);
      await loadAll();
      pushToast("Tingkatan ditambahkan.", "success");
    } catch (err: unknown) {
      pushToast(err instanceof Error ? err.message : "Gagal menambah tingkatan.", "error");
    }
  }

  async function handleAddExamType() {
    try {
      await invokeBridge("cfg.exam_types.save", {
        institution_id: institution.id,
        code: newExamType.code,
        label: newExamType.label,
        mode_default: newExamType.mode_default,
      });
      setNewExamType({ code: "", label: "", mode_default: "paper" });
      setExamTypeModalOpen(false);
      await loadAll();
      pushToast("Jenis ujian ditambahkan.", "success");
    } catch (err: unknown) {
      pushToast(err instanceof Error ? err.message : "Gagal menambah jenis ujian.", "error");
    }
  }

  async function handlePreviewNumbers() {
    if (!policy) return;
    try {
      const res = await invokeBridge<{
        participant_samples: string[];
        document_samples: string[];
      }>("cfg.number_policy.preview", {
        policy,
        series: "PAN",
        exam_code: examTypes[0]?.code ?? "SAS",
        year: "2026",
        count: 3,
      });
      setPreviewSample(res);
    } catch (err: unknown) {
      pushToast(err instanceof Error ? err.message : "Pratinjau gagal.", "error");
    }
  }

  async function handleSavePolicy() {
    if (!policy) return;
    try {
      const res = await invokeBridge<{ policy: NumberPolicyConfig; revision: number }>(
        "cfg.number_policy.save",
        {
          institution_id: institution.id,
          expected_revision: policyRev || null,
          policy,
        }
      );
      setPolicy(res.policy);
      setPolicyRev(res.revision);
      pushToast("Kebijakan penomoran disimpan.", "success");
    } catch (err: unknown) {
      pushToast(err instanceof Error ? err.message : "Gagal menyimpan kebijakan.", "error");
    }
  }

  async function handleSaveSettings() {
    if (!settings) return;
    try {
      const res = await invokeBridge<{ settings: TypedSettingsConfig; revision: number }>(
        "cfg.settings.update",
        {
          institution_id: institution.id,
          expected_revision: settingsRev,
          settings,
        }
      );
      setSettings(res.settings);
      setSettingsRev(res.revision);
      pushToast("Konfigurasi tersimpan.", "success");
    } catch (err: unknown) {
      pushToast(err instanceof Error ? err.message : "Konfigurasi ditolak.", "error");
    }
  }

  async function handleResetSettings() {
    try {
      const res = await invokeBridge<{ settings: TypedSettingsConfig; revision: number }>(
        "cfg.settings.reset",
        {
          institution_id: institution.id,
          expected_revision: settingsRev,
        }
      );
      setSettings(res.settings);
      setSettingsRev(res.revision);
      setResetConfirmOpen(false);
      pushToast("Konfigurasi dikembalikan ke default.", "info");
    } catch (err: unknown) {
      pushToast(err instanceof Error ? err.message : "Gagal reset konfigurasi.", "error");
    }
  }

  const levelColumns = useMemo<ColumnDef<LevelItem, unknown>[]>(
    () => [
      { accessorKey: "sort_order", header: "Urutan" },
      { accessorKey: "label", header: "Label Tingkatan" },
      {
        id: "actions",
        header: "Aksi",
        enableSorting: false,
        cell: ({ row }) => (
          <RowActions
            itemLabel={row.original.label}
            onDelete={async () => {
              await invokeBridge("cfg.levels.delete", {
                institution_id: institution.id,
                id: row.original.id,
              });
              await loadAll();
            }}
          />
        ),
      },
    ],
    [institution.id, loadAll]
  );

  const examTypeColumns = useMemo<ColumnDef<ExamTypeItem, unknown>[]>(
    () => [
      { accessorKey: "code", header: "Kode" },
      { accessorKey: "label", header: "Nama Jenis Ujian" },
      { accessorKey: "mode_default", header: "Mode Default" },
      {
        id: "actions",
        header: "Aksi",
        enableSorting: false,
        cell: ({ row }) => (
          <RowActions
            itemLabel={row.original.code}
            onDelete={async () => {
              await invokeBridge("cfg.exam_types.delete", {
                institution_id: institution.id,
                id: row.original.id,
              });
              await loadAll();
            }}
          />
        ),
      },
    ],
    [institution.id, loadAll]
  );

  const tabs: Array<{ id: SettingsTab; label: string }> = [
    { id: "institution", label: "Profil Lembaga" },
    { id: "levels", label: "Tingkatan & Tahun" },
    { id: "exam_types", label: "Jenis Ujian" },
    { id: "numbering", label: "Penomoran" },
    { id: "config", label: "Konfigurasi" },
  ];

  return (
    <div style={{ display: "grid", gap: 16 }}>
      <div className="uc-actions" role="tablist" aria-label="Kategori pengaturan">
        {tabs.map((item) => (
          <Button
            key={item.id}
            role="tab"
            aria-selected={tab === item.id}
            variant={tab === item.id ? "primary" : "neutral"}
            size="sm"
            onClick={() => setTab(item.id)}
          >
            {item.label}
          </Button>
        ))}
        <Button variant="secondary" size="sm" onClick={onAddInstitution}>
          <Plus size={14} aria-hidden="true" />
          Tambah Lembaga
        </Button>
      </div>

      {tab === "institution" && (
        <section className="uc-panel">
          <div className="uc-panel-head">
            <h2>Identitas Lembaga (Rev. {institution.revision})</h2>
            <Button variant="primary" size="sm" onClick={saveInstitutionProfile}>
              Simpan Profil
            </Button>
          </div>
          <div className="uc-panel-body uc-field-grid">
            <TextField
              label="Nama Lembaga"
              value={instForm.name}
              onChange={(e) => setInstForm({ ...instForm, name: e.target.value })}
            />
            <TextField
              label="Nama Singkat"
              value={instForm.short_name}
              onChange={(e) =>
                setInstForm({ ...instForm, short_name: e.target.value })
              }
            />
            <IdentifierField
              label="NPSN"
              value={instForm.npsn}
              onChange={(e) => setInstForm({ ...instForm, npsn: e.target.value })}
            />
            <IdentifierField
              label="NSM"
              value={instForm.nsm}
              onChange={(e) => setInstForm({ ...instForm, nsm: e.target.value })}
            />
            <SelectField
              label="Zona Waktu"
              value={instForm.timezone}
              options={[
                { value: "Asia/Jakarta", label: "WIB (Asia/Jakarta)" },
                { value: "Asia/Makassar", label: "WITA (Asia/Makassar)" },
                { value: "Asia/Jayapura", label: "WIT (Asia/Jayapura)" },
              ]}
              onChange={(e) =>
                setInstForm({ ...instForm, timezone: e.target.value })
              }
            />
            <TextField
              label="Alamat"
              value={instForm.address}
              onChange={(e) =>
                setInstForm({ ...instForm, address: e.target.value })
              }
            />
          </div>
        </section>
      )}

      {tab === "levels" && (
        <div style={{ display: "grid", gap: 16 }}>
          <DataTable
            data={levels}
            columns={levelColumns}
            searchPlaceholder="Cari tingkatan..."
            toolbarExtra={
              <div className="uc-actions">
                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => setLevelModalOpen(true)}
                >
                  <Plus size={14} aria-hidden="true" />
                  Tambah Tingkatan
                </Button>
                {Object.keys(levelPresets)
                  .filter((p) => levelPresets[p].length > 0)
                  .map((preset) => (
                    <Button
                      key={preset}
                      variant="neutral"
                      size="sm"
                      onClick={async () => {
                        await invokeBridge("cfg.levels.apply_preset", {
                          institution_id: institution.id,
                          preset_name: preset,
                        });
                        await loadAll();
                      }}
                    >
                      Preset {preset}
                    </Button>
                  ))}
              </div>
            }
            getCellAlign={(id) => (id === "sort_order" ? "num" : "left")}
          />
          <section className="uc-panel">
            <div className="uc-panel-head">
              <h2>Tahun Ajaran Terdaftar</h2>
            </div>
            <div className="uc-panel-body">
              {years.map((y) => (
                <div key={y.id} className="uc-sub">
                  {y.label} {y.is_active ? "(Aktif)" : ""}
                </div>
              ))}
            </div>
          </section>
        </div>
      )}

      {tab === "exam_types" && (
        <DataTable
          data={examTypes}
          columns={examTypeColumns}
          searchPlaceholder="Cari jenis ujian..."
          toolbarExtra={
            <Button
              variant="primary"
              size="sm"
              onClick={() => setExamTypeModalOpen(true)}
            >
              <Plus size={14} aria-hidden="true" />
              Tambah Jenis Ujian
            </Button>
          }
          getCellAlign={(id) => (id === "mode_default" ? "center" : "left")}
        />
      )}

      {tab === "numbering" && policy && (
        <section className="uc-panel">
          <div className="uc-panel-head">
            <h2>Kebijakan Penomoran (Rev. {policyRev})</h2>
            <div className="uc-actions">
              <Button variant="secondary" size="sm" onClick={handlePreviewNumbers}>
                Pratinjau Nomor
              </Button>
              <Button variant="primary" size="sm" onClick={handleSavePolicy}>
                Simpan Kebijakan
              </Button>
            </div>
          </div>
          <div className="uc-panel-body" style={{ display: "grid", gap: 12 }}>
            <div className="uc-field-grid">
              <TextField
                label="Prefix Nomor Peserta"
                value={policy.participant.prefix}
                onChange={(e) =>
                  setPolicy({
                    ...policy,
                    participant: { ...policy.participant, prefix: e.target.value },
                  })
                }
              />
              <TextField
                label="Pola Nomor Surat"
                value={policy.document.pattern}
                onChange={(e) =>
                  setPolicy({
                    ...policy,
                    document: { ...policy.document, pattern: e.target.value },
                  })
                }
              />
            </div>
            {previewSample && (
              <div className="uc-callout">
                <div>
                  <strong>Contoh Peserta:</strong>{" "}
                  {previewSample.participant_samples.join(", ")}
                  <br />
                  <strong>Contoh Surat:</strong>{" "}
                  {previewSample.document_samples.join(", ")}
                </div>
              </div>
            )}
          </div>
        </section>
      )}

      {tab === "config" && settings && (
        <section className="uc-panel">
          <div className="uc-panel-head">
            <h2>Konfigurasi Tervalidasi (Rev. {settingsRev})</h2>
            <div className="uc-actions">
              <Button
                variant="destructive"
                size="sm"
                onClick={() => setResetConfirmOpen(true)}
              >
                <RotateCcw size={14} aria-hidden="true" />
                Reset Default
              </Button>
              <Button variant="primary" size="sm" onClick={handleSaveSettings}>
                Simpan Konfigurasi
              </Button>
            </div>
          </div>
          <div className="uc-panel-body uc-field-grid">
            <SelectField
              label="Ukuran Kertas Default"
              value={settings.default_paper_size}
              options={[
                { value: "A4", label: "A4" },
                { value: "F4", label: "F4 (215 × 330 mm)" },
                { value: "Letter", label: "Letter" },
              ]}
              onChange={(e) =>
                setSettings({
                  ...settings,
                  default_paper_size: e.target.value as "A4" | "F4" | "Letter",
                })
              }
            />
            <IdentifierField
              label="Batas Waktu Solver (detik)"
              value={String(settings.solver_time_limit_sec)}
              onChange={(e) =>
                setSettings({
                  ...settings,
                  solver_time_limit_sec:
                    Number.parseInt(e.target.value || "0", 10) || 0,
                })
              }
            />
          </div>
        </section>
      )}

      <CRUDModal
        open={levelModalOpen}
        title="Tambah Tingkatan Kustom"
        onClose={() => setLevelModalOpen(false)}
        onSubmit={handleAddLevel}
      >
        <TextField
          label="Label Tingkatan"
          hint="Mendukung angka maupun non-numerik (mis. Tahfidz, Paket B)"
          value={newLevelLabel}
          onChange={(e) => setNewLevelLabel(e.target.value)}
        />
      </CRUDModal>

      <CRUDModal
        open={examTypeModalOpen}
        title="Tambah Jenis Ujian"
        onClose={() => setExamTypeModalOpen(false)}
        onSubmit={handleAddExamType}
      >
        <div className="uc-field-grid">
          <TextField
            label="Kode"
            value={newExamType.code}
            onChange={(e) =>
              setNewExamType({ ...newExamType, code: e.target.value })
            }
          />
          <TextField
            label="Nama Jenis Ujian"
            value={newExamType.label}
            onChange={(e) =>
              setNewExamType({ ...newExamType, label: e.target.value })
            }
          />
          <SelectField
            label="Mode Default"
            value={newExamType.mode_default}
            options={[
              { value: "paper", label: "Kertas" },
              { value: "cbt", label: "CBT" },
              { value: "practice", label: "Praktik" },
              { value: "hybrid", label: "Hybrid" },
            ]}
            onChange={(e) =>
              setNewExamType({
                ...newExamType,
                mode_default: e.target.value as
                  | "paper"
                  | "cbt"
                  | "practice"
                  | "hybrid",
              })
            }
          />
        </div>
      </CRUDModal>

      <ConfirmDialog
        open={resetConfirmOpen}
        title="Reset konfigurasi ke default?"
        impactMessage="Pengaturan kertas dan batas waktu solver lembaga ini akan kembali ke bawaan. Snapshot kegiatan yang sudah diarsipkan tidak berubah."
        confirmLabel="Reset"
        onCancel={() => setResetConfirmOpen(false)}
        onConfirm={handleResetSettings}
      />
    </div>
  );
}
