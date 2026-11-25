import { useCallback, useEffect, useMemo, useState } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import { Plus, Upload } from "lucide-react";
import { DataTable } from "../../components/shared/DataTable";
import { RowActions } from "../../components/shared/RowActions";
import { Button, ExportActionGroup } from "../../components/ui/Button";
import { StatePanel, StatusIndicator, useToast } from "../../components/ui/Feedback";
import {
  IdentifierField,
  SelectField,
  TextField,
} from "../../components/ui/FormFields";
import { ConfirmDialog, CRUDModal } from "../../components/ui/Modal";
import { invokeBridge } from "../../lib/bridge";
import type { AcademicYear, LevelItem } from "../cfg/types";
import { ImportWizardModal } from "./ImportWizardModal";
import type {
  ClassItem,
  DataQualityIssue,
  RoomItem,
  StaffItem,
  StudentItem,
  SubjectItem,
} from "./types";

type MasterTab = "students" | "staff" | "classes" | "subjects" | "rooms" | "quality";

export interface MasterDataPageProps {
  institutionId: string;
}

export function MasterDataPage({ institutionId }: MasterDataPageProps) {
  const { pushToast } = useToast();
  const [tab, setTab] = useState<MasterTab>("students");

  const [students, setStudents] = useState<StudentItem[]>([]);
  const [staff, setStaff] = useState<StaffItem[]>([]);
  const [classes, setClasses] = useState<ClassItem[]>([]);
  const [subjects, setSubjects] = useState<SubjectItem[]>([]);
  const [subjectWarnings, setSubjectWarnings] = useState<string[]>([]);
  const [rooms, setRooms] = useState<RoomItem[]>([]);
  const [issues, setIssues] = useState<DataQualityIssue[]>([]);
  const [years, setYears] = useState<AcademicYear[]>([]);
  const [levels, setLevels] = useState<LevelItem[]>([]);

  const [importOpen, setImportOpen] = useState(false);
  const [studentModalOpen, setStudentModalOpen] = useState(false);
  const [studentForm, setStudentForm] = useState({
    id: null as string | null,
    expected_revision: null as number | null,
    nis: "",
    nisn: "",
    full_name: "",
  });

  const [staffModalOpen, setStaffModalOpen] = useState(false);
  const [staffForm, setStaffForm] = useState({
    staff_code: "",
    nip: "",
    full_name: "",
    role: "teacher" as "teacher" | "tu" | "external_invigilator",
  });

  const [classModalOpen, setClassModalOpen] = useState(false);
  const [classForm, setClassForm] = useState({
    year_id: "",
    level_id: "",
    name: "",
    program: "",
  });

  const [subjectModalOpen, setSubjectModalOpen] = useState(false);
  const [subjectForm, setSubjectForm] = useState({
    code: "",
    name: "",
    category: "",
  });

  const [roomModalOpen, setRoomModalOpen] = useState(false);
  const [roomForm, setRoomForm] = useState({
    code: "",
    name: "",
    mode: "paper" as "paper" | "cbt" | "practice" | "hybrid",
    rows: 4,
    cols: 5,
    seats_per_desk: 1,
    capacity_limit: 20,
  });

  const [deleteTarget, setDeleteTarget] = useState<{
    kind: "students" | "staff";
    id: string;
    label: string;
  } | null>(null);

  const loadAll = useCallback(async () => {
    try {
      const [stRes, sfRes, clRes, sbRes, rmRes, dqRes, yrRes, lvRes] =
        await Promise.all([
          invokeBridge<{ items: StudentItem[] }>("mst.students.list", {
            institution_id: institutionId,
          }),
          invokeBridge<{ items: StaffItem[] }>("mst.staff.list", {
            institution_id: institutionId,
          }),
          invokeBridge<{ items: ClassItem[] }>("mst.classes.list", {
            institution_id: institutionId,
          }),
          invokeBridge<{ items: SubjectItem[]; warnings: string[] }>(
            "mst.subjects.list",
            { institution_id: institutionId }
          ),
          invokeBridge<{ items: RoomItem[] }>("mst.rooms.list", {
            institution_id: institutionId,
          }),
          invokeBridge<{ issues: DataQualityIssue[] }>("mst.quality.report", {
            institution_id: institutionId,
          }),
          invokeBridge<{ items: AcademicYear[] }>("cfg.years.list", {
            institution_id: institutionId,
          }),
          invokeBridge<{ items: LevelItem[] }>("cfg.levels.list", {
            institution_id: institutionId,
          }),
        ]);
      setStudents(stRes.items);
      setStaff(sfRes.items);
      setClasses(clRes.items);
      setSubjects(sbRes.items);
      setSubjectWarnings(sbRes.warnings);
      setRooms(rmRes.items);
      setIssues(dqRes.issues);
      setYears(yrRes.items);
      setLevels(lvRes.items);
    } catch (err: unknown) {
      pushToast(
        err instanceof Error ? err.message : "Gagal memuat master data.",
        "error"
      );
    }
  }, [institutionId, pushToast]);

  useEffect(() => {
    void loadAll();
  }, [loadAll]);

  async function handleExportXlsx(kind: "students" | "staff" | "subjects" | "rooms") {
    try {
      const res = await invokeBridge<{
        filename: string;
        row_count: number;
        content_base64: string;
      }>("mst.exports.xlsx", {
        institution_id: institutionId,
        kind,
      });
      const bytes = Uint8Array.from(window.atob(res.content_base64), (c) =>
        c.charCodeAt(0)
      );
      const blob = new Blob([bytes], {
        type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = res.filename;
      a.click();
      URL.revokeObjectURL(url);
      pushToast(`Ekspor ${res.row_count} baris (${res.filename}) selesai.`, "success");
    } catch (err: unknown) {
      pushToast(err instanceof Error ? err.message : "Ekspor gagal.", "error");
    }
  }

  async function saveStudent() {
    try {
      const res = await invokeBridge<{ warnings: string[] }>("mst.students.save", {
        institution_id: institutionId,
        id: studentForm.id,
        expected_revision: studentForm.expected_revision,
        nis: studentForm.nis || null,
        nisn: studentForm.nisn || null,
        full_name: studentForm.full_name,
      });
      setStudentModalOpen(false);
      await loadAll();
      pushToast(
        res.warnings[0] ? `Tersimpan (${res.warnings[0]})` : "Data siswa disimpan.",
        "success"
      );
    } catch (err: unknown) {
      pushToast(err instanceof Error ? err.message : "Gagal menyimpan siswa.", "error");
    }
  }

  async function saveStaff() {
    try {
      await invokeBridge("mst.staff.save", {
        institution_id: institutionId,
        staff_code: staffForm.staff_code,
        nip: staffForm.nip || null,
        full_name: staffForm.full_name,
        role: staffForm.role,
      });
      setStaffModalOpen(false);
      await loadAll();
      pushToast("Data staf disimpan.", "success");
    } catch (err: unknown) {
      pushToast(err instanceof Error ? err.message : "Gagal menyimpan staf.", "error");
    }
  }

  async function saveClass() {
    try {
      await invokeBridge("mst.classes.save", {
        institution_id: institutionId,
        year_id: classForm.year_id || years[0]?.id,
        level_id: classForm.level_id || levels[0]?.id,
        name: classForm.name,
        program: classForm.program || null,
      });
      setClassModalOpen(false);
      await loadAll();
      pushToast("Data kelas disimpan.", "success");
    } catch (err: unknown) {
      pushToast(err instanceof Error ? err.message : "Gagal menyimpan kelas.", "error");
    }
  }

  async function saveSubject() {
    try {
      await invokeBridge("mst.subjects.save", {
        institution_id: institutionId,
        code: subjectForm.code,
        name: subjectForm.name,
        category: subjectForm.category || null,
      });
      setSubjectModalOpen(false);
      await loadAll();
      pushToast("Mata pelajaran disimpan.", "success");
    } catch (err: unknown) {
      pushToast(err instanceof Error ? err.message : "Gagal menyimpan mapel.", "error");
    }
  }

  async function saveRoom() {
    try {
      await invokeBridge("mst.rooms.save", {
        institution_id: institutionId,
        code: roomForm.code,
        name: roomForm.name,
        mode: roomForm.mode,
        capacity_limit: roomForm.capacity_limit,
        layout: {
          rows: roomForm.rows,
          cols: roomForm.cols,
          seats_per_desk: roomForm.seats_per_desk,
          disabled_cells: [],
          accessible_seats: [],
          board_position: "top",
        },
      });
      setRoomModalOpen(false);
      await loadAll();
      pushToast("Ruang ujian disimpan.", "success");
    } catch (err: unknown) {
      pushToast(err instanceof Error ? err.message : "Gagal menyimpan ruang.", "error");
    }
  }

  const studentCols = useMemo<ColumnDef<StudentItem, unknown>[]>(
    () => [
      { accessorKey: "nis", header: "NIS" },
      { accessorKey: "nisn", header: "NISN" },
      { accessorKey: "full_name", header: "Nama Siswa" },
      {
        accessorKey: "active",
        header: "Status",
        cell: ({ row }) => (
          <StatusIndicator
            label={row.original.active ? "Aktif" : "Nonaktif"}
            tone={row.original.active ? "success" : "neutral"}
          />
        ),
      },
      {
        id: "actions",
        header: "Aksi",
        enableSorting: false,
        cell: ({ row }) => (
          <RowActions
            itemLabel={row.original.full_name}
            onEdit={() => {
              setStudentForm({
                id: row.original.id,
                expected_revision: row.original.revision,
                nis: row.original.nis ?? "",
                nisn: row.original.nisn ?? "",
                full_name: row.original.full_name,
              });
              setStudentModalOpen(true);
            }}
            onDelete={() =>
              setDeleteTarget({
                kind: "students",
                id: row.original.id,
                label: row.original.full_name,
              })
            }
          />
        ),
      },
    ],
    []
  );

  const staffCols = useMemo<ColumnDef<StaffItem, unknown>[]>(
    () => [
      { accessorKey: "staff_code", header: "Kode" },
      { accessorKey: "nip", header: "NIP" },
      { accessorKey: "full_name", header: "Nama" },
      { accessorKey: "role", header: "Peran" },
      {
        id: "actions",
        header: "Aksi",
        enableSorting: false,
        cell: ({ row }) => (
          <RowActions
            itemLabel={row.original.full_name}
            onDelete={() =>
              setDeleteTarget({
                kind: "staff",
                id: row.original.id,
                label: row.original.full_name,
              })
            }
          />
        ),
      },
    ],
    []
  );

  const classCols = useMemo<ColumnDef<ClassItem, unknown>[]>(
    () => [
      { accessorKey: "name", header: "Rombel" },
      { accessorKey: "program", header: "Program" },
    ],
    []
  );

  const subjectCols = useMemo<ColumnDef<SubjectItem, unknown>[]>(
    () => [
      { accessorKey: "code", header: "Kode" },
      { accessorKey: "name", header: "Mata Pelajaran" },
      { accessorKey: "category", header: "Kategori" },
    ],
    []
  );

  const roomCols = useMemo<ColumnDef<RoomItem, unknown>[]>(
    () => [
      { accessorKey: "code", header: "Kode" },
      { accessorKey: "name", header: "Nama Ruang" },
      { accessorKey: "mode", header: "Mode" },
      { accessorKey: "capacity_limit", header: "Kapasitas" },
    ],
    []
  );

  const qualityCols = useMemo<ColumnDef<DataQualityIssue, unknown>[]>(
    () => [
      {
        accessorKey: "severity",
        header: "Tingkat",
        cell: ({ row }) => (
          <StatusIndicator
            label={row.original.severity === "error" ? "Kritis" : "Peringatan"}
            tone={row.original.severity === "error" ? "destructive" : "warning"}
          />
        ),
      },
      { accessorKey: "kind", header: "Jenis" },
      { accessorKey: "message", header: "Temuan Kualitas Data" },
    ],
    []
  );

  const tabs: Array<{ id: MasterTab; label: string }> = [
    { id: "students", label: `Siswa (${students.length})` },
    { id: "staff", label: `Staf & Guru (${staff.length})` },
    { id: "classes", label: `Kelas (${classes.length})` },
    { id: "subjects", label: `Mapel (${subjects.length})` },
    { id: "rooms", label: `Ruang (${rooms.length})` },
    { id: "quality", label: `Kualitas Data (${issues.length})` },
  ];

  const importableTab =
    tab === "students" || tab === "staff" || tab === "subjects" || tab === "rooms";

  return (
    <div style={{ display: "grid", gap: 16 }}>
      <div className="uc-actions" role="tablist" aria-label="Kategori master data">
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

        {importableTab && (
          <Button
            variant="secondary"
            size="sm"
            onClick={() => setImportOpen(true)}
          >
            <Upload size={14} aria-hidden="true" />
            Impor XLSX
          </Button>
        )}

        {tab === "students" && (
          <Button
            variant="primary"
            size="sm"
            onClick={() => {
              setStudentForm({
                id: null,
                expected_revision: null,
                nis: "",
                nisn: "",
                full_name: "",
              });
              setStudentModalOpen(true);
            }}
          >
            <Plus size={14} aria-hidden="true" />
            Tambah Siswa
          </Button>
        )}
        {tab === "staff" && (
          <Button variant="primary" size="sm" onClick={() => setStaffModalOpen(true)}>
            <Plus size={14} aria-hidden="true" />
            Tambah Staf
          </Button>
        )}
        {tab === "classes" && (
          <Button
            variant="primary"
            size="sm"
            onClick={() => {
              setClassForm({
                year_id: years[0]?.id ?? "",
                level_id: levels[0]?.id ?? "",
                name: "",
                program: "",
              });
              setClassModalOpen(true);
            }}
          >
            <Plus size={14} aria-hidden="true" />
            Tambah Kelas
          </Button>
        )}
        {tab === "subjects" && (
          <Button
            variant="primary"
            size="sm"
            onClick={() => setSubjectModalOpen(true)}
          >
            <Plus size={14} aria-hidden="true" />
            Tambah Mapel
          </Button>
        )}
        {tab === "rooms" && (
          <Button variant="primary" size="sm" onClick={() => setRoomModalOpen(true)}>
            <Plus size={14} aria-hidden="true" />
            Tambah Ruang
          </Button>
        )}
      </div>

      {tab === "subjects" && subjectWarnings.length > 0 && (
        <div className="uc-callout">
          <div>{subjectWarnings[0]}</div>
        </div>
      )}

      {tab === "students" && (
        <DataTable
          data={students}
          columns={studentCols}
          searchPlaceholder="Cari NIS, NISN, atau nama..."
          toolbarExtra={
            <ExportActionGroup onExportExcel={() => handleExportXlsx("students")} />
          }
          getCellAlign={(id) => (id === "active" ? "center" : "left")}
        />
      )}

      {tab === "staff" && (
        <DataTable
          data={staff}
          columns={staffCols}
          searchPlaceholder="Cari kode, NIP, atau nama..."
          toolbarExtra={
            <ExportActionGroup onExportExcel={() => handleExportXlsx("staff")} />
          }
        />
      )}

      {tab === "classes" && (
        <DataTable
          data={classes}
          columns={classCols}
          searchPlaceholder="Cari rombel..."
        />
      )}

      {tab === "subjects" && (
        <DataTable
          data={subjects}
          columns={subjectCols}
          searchPlaceholder="Cari kode atau mapel..."
          toolbarExtra={
            <ExportActionGroup onExportExcel={() => handleExportXlsx("subjects")} />
          }
        />
      )}

      {tab === "rooms" && (
        <DataTable
          data={rooms}
          columns={roomCols}
          searchPlaceholder="Cari ruang..."
          toolbarExtra={
            <ExportActionGroup onExportExcel={() => handleExportXlsx("rooms")} />
          }
          getCellAlign={(id) => (id === "capacity_limit" ? "num" : "left")}
        />
      )}

      {tab === "quality" &&
        (issues.length === 0 ? (
          <section className="uc-panel">
            <StatePanel
              kind="empty"
              title="Tidak ada temuan kualitas data"
              description="Seluruh master data telah terisi dan konsisten."
            />
          </section>
        ) : (
          <DataTable
            data={issues}
            columns={qualityCols}
            searchPlaceholder="Cari temuan..."
            getCellAlign={(id) => (id === "severity" ? "center" : "left")}
          />
        ))}

      {importableTab && (
        <ImportWizardModal
          open={importOpen}
          institutionId={institutionId}
          kind={tab}
          onClose={() => setImportOpen(false)}
          onCommitted={() => void loadAll()}
        />
      )}

      <CRUDModal
        open={studentModalOpen}
        title={studentForm.id ? "Edit Siswa" : "Tambah Siswa"}
        onClose={() => setStudentModalOpen(false)}
        onSubmit={saveStudent}
      >
        <div className="uc-field-grid">
          <IdentifierField
            label="NIS"
            value={studentForm.nis}
            onChange={(e) =>
              setStudentForm({ ...studentForm, nis: e.target.value })
            }
          />
          <IdentifierField
            label="NISN (Opsional)"
            value={studentForm.nisn}
            onChange={(e) =>
              setStudentForm({ ...studentForm, nisn: e.target.value })
            }
          />
          <TextField
            label="Nama Lengkap"
            value={studentForm.full_name}
            onChange={(e) =>
              setStudentForm({ ...studentForm, full_name: e.target.value })
            }
          />
        </div>
      </CRUDModal>

      <CRUDModal
        open={staffModalOpen}
        title="Tambah Staf / Pengawas"
        onClose={() => setStaffModalOpen(false)}
        onSubmit={saveStaff}
      >
        <div className="uc-field-grid">
          <TextField
            label="Kode Staf"
            value={staffForm.staff_code}
            onChange={(e) =>
              setStaffForm({ ...staffForm, staff_code: e.target.value })
            }
          />
          <IdentifierField
            label="NIP (Opsional untuk eksternal)"
            value={staffForm.nip}
            onChange={(e) =>
              setStaffForm({ ...staffForm, nip: e.target.value })
            }
          />
          <TextField
            label="Nama Lengkap"
            value={staffForm.full_name}
            onChange={(e) =>
              setStaffForm({ ...staffForm, full_name: e.target.value })
            }
          />
          <SelectField
            label="Peran"
            value={staffForm.role}
            options={[
              { value: "teacher", label: "Guru" },
              { value: "tu", label: "Tenaga Kependidikan / TU" },
              { value: "external_invigilator", label: "Pengawas Silang / Eksternal" },
            ]}
            onChange={(e) =>
              setStaffForm({
                ...staffForm,
                role: e.target.value as "teacher" | "tu" | "external_invigilator",
              })
            }
          />
        </div>
      </CRUDModal>

      <CRUDModal
        open={classModalOpen}
        title="Tambah Kelas / Rombel"
        onClose={() => setClassModalOpen(false)}
        onSubmit={saveClass}
      >
        <div className="uc-field-grid">
          <SelectField
            label="Tahun Ajaran"
            value={classForm.year_id}
            options={years.map((y) => ({ value: y.id, label: y.label }))}
            onChange={(e) =>
              setClassForm({ ...classForm, year_id: e.target.value })
            }
          />
          <SelectField
            label="Tingkatan"
            value={classForm.level_id}
            options={levels.map((l) => ({ value: l.id, label: l.label }))}
            onChange={(e) =>
              setClassForm({ ...classForm, level_id: e.target.value })
            }
          />
          <TextField
            label="Nama Rombel"
            value={classForm.name}
            onChange={(e) =>
              setClassForm({ ...classForm, name: e.target.value })
            }
          />
          <TextField
            label="Program / Jurusan (Opsional)"
            value={classForm.program}
            onChange={(e) =>
              setClassForm({ ...classForm, program: e.target.value })
            }
          />
        </div>
      </CRUDModal>

      <CRUDModal
        open={subjectModalOpen}
        title="Tambah Mata Pelajaran"
        onClose={() => setSubjectModalOpen(false)}
        onSubmit={saveSubject}
      >
        <div className="uc-field-grid">
          <TextField
            label="Kode Mapel"
            value={subjectForm.code}
            onChange={(e) =>
              setSubjectForm({ ...subjectForm, code: e.target.value })
            }
          />
          <TextField
            label="Nama Mata Pelajaran"
            value={subjectForm.name}
            onChange={(e) =>
              setSubjectForm({ ...subjectForm, name: e.target.value })
            }
          />
          <TextField
            label="Kategori (Opsional)"
            value={subjectForm.category}
            onChange={(e) =>
              setSubjectForm({ ...subjectForm, category: e.target.value })
            }
          />
        </div>
      </CRUDModal>

      <CRUDModal
        open={roomModalOpen}
        title="Tambah Ruang Ujian"
        onClose={() => setRoomModalOpen(false)}
        onSubmit={saveRoom}
      >
        <div className="uc-field-grid">
          <TextField
            label="Kode Ruang"
            value={roomForm.code}
            onChange={(e) => setRoomForm({ ...roomForm, code: e.target.value })}
          />
          <TextField
            label="Nama Ruang"
            value={roomForm.name}
            onChange={(e) => setRoomForm({ ...roomForm, name: e.target.value })}
          />
          <SelectField
            label="Mode"
            value={roomForm.mode}
            options={[
              { value: "paper", label: "Kertas" },
              { value: "cbt", label: "CBT" },
              { value: "practice", label: "Praktik" },
              { value: "hybrid", label: "Hybrid" },
            ]}
            onChange={(e) =>
              setRoomForm({
                ...roomForm,
                mode: e.target.value as "paper" | "cbt" | "practice" | "hybrid",
              })
            }
          />
          <IdentifierField
            label="Batas Kapasitas"
            value={String(roomForm.capacity_limit)}
            onChange={(e) =>
              setRoomForm({
                ...roomForm,
                capacity_limit: Number.parseInt(e.target.value || "0", 10) || 0,
              })
            }
          />
        </div>
      </CRUDModal>

      <ConfirmDialog
        open={deleteTarget !== null}
        title={`Hapus ${deleteTarget?.label ?? ""}?`}
        impactMessage="Data yang sudah dirujuk oleh rombel, penugasan mengajar, atau kegiatan ujian akan dilindungi dan ditolak penghapusannya."
        onCancel={() => setDeleteTarget(null)}
        onConfirm={async () => {
          if (!deleteTarget) return;
          try {
            await invokeBridge(
              deleteTarget.kind === "students"
                ? "mst.students.delete"
                : "mst.staff.delete",
              { institution_id: institutionId, id: deleteTarget.id }
            );
            setDeleteTarget(null);
            await loadAll();
            pushToast("Data dihapus.", "info");
          } catch (err: unknown) {
            pushToast(
              err instanceof Error ? err.message : "Gagal menghapus data.",
              "error"
            );
          }
        }}
      />
    </div>
  );
}
