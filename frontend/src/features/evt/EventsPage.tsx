import { useCallback, useEffect, useMemo, useState } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import { Copy, Hash, Plus } from "lucide-react";
import { DataTable } from "../../components/shared/DataTable";
import { RowActions } from "../../components/shared/RowActions";
import { Button } from "../../components/ui/Button";
import { StatusIndicator, useToast } from "../../components/ui/Feedback";
import {
  DateField,
  IdentifierField,
  SelectField,
  TextField,
} from "../../components/ui/FormFields";
import { CRUDModal } from "../../components/ui/Modal";
import { invokeBridge } from "../../lib/bridge";
import type { AcademicYear, ExamTypeItem } from "../cfg/types";
import type {
  ExamGroupItem,
  ExamItem,
  ExamParticipantItem,
  ExamState,
} from "./types";

export interface EventsPageProps {
  institutionId: string;
  exams: ExamItem[];
  activeExam: ExamItem | null;
  onSelectExam: (examId: string) => void;
  onExamsChanged: () => void;
}

export function EventsPage({
  institutionId,
  exams,
  activeExam,
  onSelectExam,
  onExamsChanged,
}: EventsPageProps) {
  const { pushToast } = useToast();
  const [years, setYears] = useState<AcademicYear[]>([]);
  const [examTypes, setExamTypes] = useState<ExamTypeItem[]>([]);
  const [participants, setParticipants] = useState<ExamParticipantItem[]>([]);
  const [groups, setGroups] = useState<ExamGroupItem[]>([]);

  const [createOpen, setCreateOpen] = useState(false);
  const [createForm, setCreateForm] = useState({
    title: "",
    year_id: "",
    exam_type_id: "",
    semester_label: "Ganjil",
    mode: "paper" as "paper" | "cbt" | "practice" | "hybrid",
    starts_on: "2026-11-30",
    ends_on: "2026-12-08",
  });

  const [numberingOpen, setNumberingOpen] = useState(false);
  const [numPrefix, setNumPrefix] = useState("UC");

  const [transitionOpen, setTransitionOpen] = useState(false);
  const [targetState, setTargetState] = useState<ExamState>("PREPARATION");
  const [transitionReason, setTransitionReason] = useState("");

  const [cloneOpen, setCloneOpen] = useState(false);
  const [cloneTitle, setCloneTitle] = useState("");

  const loadConfig = useCallback(async () => {
    const [yrRes, etRes] = await Promise.all([
      invokeBridge<{ items: AcademicYear[] }>("cfg.years.list", {
        institution_id: institutionId,
      }),
      invokeBridge<{ items: ExamTypeItem[] }>("cfg.exam_types.list", {
        institution_id: institutionId,
      }),
    ]);
    setYears(yrRes.items);
    setExamTypes(etRes.items);
  }, [institutionId]);

  const loadExamDetails = useCallback(async () => {
    if (!activeExam) {
      setParticipants([]);
      setGroups([]);
      return;
    }
    const [ptRes, grRes] = await Promise.all([
      invokeBridge<{ items: ExamParticipantItem[] }>("evt.participants.list", {
        institution_id: institutionId,
        exam_id: activeExam.id,
      }),
      invokeBridge<{ groups: ExamGroupItem[] }>("evt.groups.list", {
        institution_id: institutionId,
        exam_id: activeExam.id,
      }),
    ]);
    setParticipants(ptRes.items);
    setGroups(grRes.groups);
  }, [institutionId, activeExam]);

  useEffect(() => {
    void loadConfig();
  }, [loadConfig]);

  useEffect(() => {
    void loadExamDetails();
  }, [loadExamDetails]);

  async function handleCreateExam() {
    try {
      const res = await invokeBridge<{ exam: ExamItem }>("evt.exams.create", {
        institution_id: institutionId,
        year_id: createForm.year_id || years[0]?.id,
        exam_type_id: createForm.exam_type_id || examTypes[0]?.id,
        title: createForm.title,
        semester_label: createForm.semester_label,
        mode: createForm.mode,
        starts_on: createForm.starts_on,
        ends_on: createForm.ends_on,
      });
      setCreateOpen(false);
      onSelectExam(res.exam.id);
      onExamsChanged();
      pushToast(`Kegiatan '${res.exam.title}' dibuat dengan snapshot.`, "success");
    } catch (err: unknown) {
      pushToast(err instanceof Error ? err.message : "Gagal membuat kegiatan.", "error");
    }
  }

  async function handleGenerateNumbers() {
    if (!activeExam) return;
    try {
      const res = await invokeBridge<{ assigned_count: number }>(
        "evt.numbering.generate",
        {
          institution_id: institutionId,
          exam_id: activeExam.id,
          expected_revision: activeExam.revision,
          prefix: numPrefix,
          padding: 4,
          start_seq: 1,
          sort_by: "name",
        }
      );
      setNumberingOpen(false);
      onExamsChanged();
      await loadExamDetails();
      pushToast(`${res.assigned_count} nomor peserta dibuat.`, "success");
    } catch (err: unknown) {
      pushToast(err instanceof Error ? err.message : "Gagal membuat nomor.", "error");
    }
  }

  async function handleTransition() {
    if (!activeExam) return;
    try {
      await invokeBridge("evt.exams.transition", {
        institution_id: institutionId,
        exam_id: activeExam.id,
        expected_revision: activeExam.revision,
        target_state: targetState,
        reason: transitionReason,
      });
      setTransitionOpen(false);
      setTransitionReason("");
      onExamsChanged();
      pushToast(`Status kegiatan diubah ke ${targetState}.`, "success");
    } catch (err: unknown) {
      pushToast(err instanceof Error ? err.message : "Gagal ubah status.", "error");
    }
  }

  async function handleClone() {
    if (!activeExam) return;
    try {
      const res = await invokeBridge<{ exam: ExamItem }>("evt.exams.clone", {
        institution_id: institutionId,
        source_exam_id: activeExam.id,
        title: cloneTitle,
        starts_on: activeExam.starts_on,
        ends_on: activeExam.ends_on,
      });
      setCloneOpen(false);
      onSelectExam(res.exam.id);
      onExamsChanged();
      pushToast(`Konfigurasi disalin ke '${res.exam.title}'.`, "success");
    } catch (err: unknown) {
      pushToast(err instanceof Error ? err.message : "Gagal menduplikasi.", "error");
    }
  }

  const examCols = useMemo<ColumnDef<ExamItem, unknown>[]>(
    () => [
      { accessorKey: "title", header: "Kegiatan" },
      { accessorKey: "semester_label", header: "Semester" },
      { accessorKey: "mode", header: "Mode" },
      { accessorKey: "starts_on", header: "Mulai" },
      {
        accessorKey: "state",
        header: "Status",
        cell: ({ row }) => (
          <StatusIndicator
            label={row.original.state}
            tone={row.original.state === "READY" ? "success" : "warning"}
          />
        ),
      },
      {
        id: "actions",
        header: "Aksi",
        enableSorting: false,
        cell: ({ row }) => (
          <RowActions
            itemLabel={row.original.title}
            onView={() => onSelectExam(row.original.id)}
          />
        ),
      },
    ],
    [onSelectExam]
  );

  const partCols = useMemo<ColumnDef<ExamParticipantItem, unknown>[]>(
    () => [
      { accessorKey: "participant_number", header: "No. Peserta" },
      { accessorKey: "code", header: "NIS" },
      { accessorKey: "display_name", header: "Nama Peserta" },
      { accessorKey: "class_label", header: "Kelas" },
    ],
    []
  );

  return (
    <div style={{ display: "grid", gap: 16 }}>
      <div className="uc-actions">
        <Button
          variant="primary"
          size="sm"
          onClick={() => {
            setCreateForm({
              title: "",
              year_id: years[0]?.id ?? "",
              exam_type_id: examTypes[0]?.id ?? "",
              semester_label: "Ganjil",
              mode: "paper",
              starts_on: "2026-11-30",
              ends_on: "2026-12-08",
            });
            setCreateOpen(true);
          }}
        >
          <Plus size={14} aria-hidden="true" />
          Kegiatan Baru
        </Button>

        {activeExam && (
          <>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setNumberingOpen(true)}
            >
              <Hash size={14} aria-hidden="true" />
              Nomor Peserta
            </Button>
            <Button
              variant="neutral"
              size="sm"
              onClick={() => {
                setTargetState(activeExam.state);
                setTransitionOpen(true);
              }}
            >
              Ubah Status ({activeExam.state})
            </Button>
            <Button
              variant="neutral"
              size="sm"
              onClick={() => {
                setCloneTitle(`${activeExam.title} (Salinan)`);
                setCloneOpen(true);
              }}
            >
              <Copy size={14} aria-hidden="true" />
              Duplikasi
            </Button>
          </>
        )}
      </div>

      <DataTable
        data={exams}
        columns={examCols}
        searchPlaceholder="Cari kegiatan ujian..."
        getCellAlign={(id) => (id === "state" || id === "mode" ? "center" : "left")}
      />

      {activeExam && (
        <>
          <DataTable
            data={participants}
            columns={partCols}
            searchPlaceholder="Cari peserta snapshot..."
          />
          <section className="uc-panel">
            <div className="uc-panel-head">
              <h2>Kelompok &amp; Kebutuhan Mapel ({groups.length})</h2>
            </div>
            <div className="uc-panel-body">
              {groups.map((g) => (
                <div key={g.id} className="uc-sub">
                  <strong>{g.label}</strong>: {g.member_count} peserta ·{" "}
                  {g.requirements.length} mata pelajaran
                </div>
              ))}
            </div>
          </section>
        </>
      )}

      <CRUDModal
        open={createOpen}
        title="Buat Kegiatan Ujian Baru"
        onClose={() => setCreateOpen(false)}
        onSubmit={handleCreateExam}
      >
        <div className="uc-field-grid">
          <TextField
            label="Nama Kegiatan"
            value={createForm.title}
            onChange={(e) =>
              setCreateForm({ ...createForm, title: e.target.value })
            }
          />
          <SelectField
            label="Jenis Ujian"
            value={createForm.exam_type_id}
            options={examTypes.map((et) => ({
              value: et.id,
              label: `${et.code} — ${et.label}`,
            }))}
            onChange={(e) =>
              setCreateForm({ ...createForm, exam_type_id: e.target.value })
            }
          />
          <SelectField
            label="Tahun Ajaran"
            value={createForm.year_id}
            options={years.map((y) => ({ value: y.id, label: y.label }))}
            onChange={(e) =>
              setCreateForm({ ...createForm, year_id: e.target.value })
            }
          />
          <SelectField
            label="Mode"
            value={createForm.mode}
            options={[
              { value: "paper", label: "Kertas" },
              { value: "cbt", label: "CBT" },
              { value: "practice", label: "Praktik" },
              { value: "hybrid", label: "Hybrid" },
            ]}
            onChange={(e) =>
              setCreateForm({
                ...createForm,
                mode: e.target.value as "paper" | "cbt" | "practice" | "hybrid",
              })
            }
          />
          <DateField
            label="Tanggal Mulai"
            value={createForm.starts_on}
            onChange={(e) =>
              setCreateForm({ ...createForm, starts_on: e.target.value })
            }
          />
          <DateField
            label="Tanggal Selesai"
            value={createForm.ends_on}
            onChange={(e) =>
              setCreateForm({ ...createForm, ends_on: e.target.value })
            }
          />
        </div>
      </CRUDModal>

      <CRUDModal
        open={numberingOpen}
        title="Generate Nomor Peserta"
        onClose={() => setNumberingOpen(false)}
        onSubmit={handleGenerateNumbers}
      >
        <IdentifierField
          label="Prefix Nomor"
          value={numPrefix}
          onChange={(e) => setNumPrefix(e.target.value)}
        />
      </CRUDModal>

      <CRUDModal
        open={transitionOpen}
        title="Ubah Status Siklus Kegiatan"
        onClose={() => setTransitionOpen(false)}
        onSubmit={handleTransition}
      >
        <SelectField
          label="Status Tujuan"
          value={targetState}
          options={[
            "DRAFT",
            "PREPARATION",
            "READY",
            "RUNNING",
            "COMPLETED",
            "ARCHIVED",
          ].map((s) => ({ value: s, label: s }))}
          onChange={(e) => setTargetState(e.target.value as ExamState)}
        />
        <TextField
          label="Alasan (wajib bila mundur/reopen)"
          value={transitionReason}
          onChange={(e) => setTransitionReason(e.target.value)}
        />
      </CRUDModal>

      <CRUDModal
        open={cloneOpen}
        title="Duplikasi Konfigurasi Kegiatan"
        onClose={() => setCloneOpen(false)}
        onSubmit={handleClone}
      >
        <TextField
          label="Nama Kegiatan Baru"
          value={cloneTitle}
          onChange={(e) => setCloneTitle(e.target.value)}
        />
      </CRUDModal>
    </div>
  );
}
