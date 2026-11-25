import { useCallback, useEffect, useMemo, useState } from "react";
import { CalendarDays, ListTodo, Paperclip, Plus, Sparkles } from "lucide-react";
import { Button } from "../../components/ui/Button";
import { StatusIndicator, useToast } from "../../components/ui/Feedback";
import { CRUDModal } from "../../components/ui/Modal";
import { invokeBridge } from "../../lib/bridge";
import type { ExamItem } from "../evt/types";
import type {
  TaskItem,
  TaskPhase,
  TaskPriority,
  TasksDetail,
  TaskState,
} from "./types";

interface TasksPageProps {
  institutionId: string;
  activeExam: ExamItem | null;
}

function getErrMsg(err: unknown, fallback: string): string {
  return err instanceof Error ? err.message : fallback;
}

export function TasksPage({ institutionId, activeExam }: TasksPageProps) {
  const { pushToast } = useToast();
  const [detail, setDetail] = useState<TasksDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [view, setView] = useState<"table" | "timeline">("table");

  // Search & filters (TSK-02)
  const [search, setSearch] = useState("");
  const [filterPhase, setFilterPhase] = useState("");
  const [filterState, setFilterState] = useState("");
  const [onlyMissingPic, setOnlyMissingPic] = useState(false);

  // Task CRUD modal
  const [showTaskModal, setShowTaskModal] = useState(false);
  const [editingTaskId, setEditingTaskId] = useState<string | null>(null);
  const [taskTitle, setTaskTitle] = useState("");
  const [taskTitleErr, setTaskTitleErr] = useState("");
  const [taskPhase, setTaskPhase] = useState<TaskPhase>("preparation");
  const [taskPriority, setTaskPriority] = useState<TaskPriority>("medium");
  const [taskDue, setTaskDue] = useState("2026-12-01");
  const [taskPicId, setTaskPicId] = useState("");
  const [taskState, setTaskState] = useState<TaskState>("todo");

  // Evidence modal (TSK-05)
  const [evidenceTask, setEvidenceTask] = useState<TaskItem | null>(null);
  const [evAsset, setEvAsset] = useState("");
  const [evNote, setEvNote] = useState("");
  const [evActor, setEvActor] = useState("Operator");

  const loadDetail = useCallback(async () => {
    if (!activeExam) {
      setDetail(null);
      return;
    }
    setLoading(true);
    try {
      const data = await invokeBridge<TasksDetail>("tsk.detail", {
        institution_id: institutionId,
        exam_id: activeExam.id,
      });
      setDetail(data);
    } catch (err) {
      pushToast(getErrMsg(err, "Gagal memuat daftar tugas."), "error");
    } finally {
      setLoading(false);
    }
  }, [institutionId, activeExam, pushToast]);

  useEffect(() => {
    void loadDetail();
  }, [loadDetail]);

  const filteredTasks = useMemo(() => {
    const q = search.trim().toLowerCase();
    return (detail?.tasks ?? []).filter((t) => {
      if (q && !t.title.toLowerCase().includes(q)) return false;
      if (filterPhase && t.phase !== filterPhase) return false;
      if (filterState && t.state !== filterState) return false;
      if (onlyMissingPic && !t.missing_pic) return false;
      return true;
    });
  }, [detail, search, filterPhase, filterState, onlyMissingPic]);

  const timelineGroups = useMemo(() => {
    const map = new Map<string, TaskItem[]>();
    for (const t of filteredTasks) {
      const list = map.get(t.due_date) ?? [];
      list.push(t);
      map.set(t.due_date, list);
    }
    return Array.from(map.entries()).sort((a, b) => a[0].localeCompare(b[0]));
  }, [filteredTasks]);

  const handleApplyPreset = async () => {
    if (!activeExam) return;
    try {
      const res = await invokeBridge<{ created_count: number }>(
        "tsk.presets.apply",
        {
          institution_id: institutionId,
          exam_id: activeExam.id,
          preset_key: "standard_exam",
        }
      );
      pushToast(`${res.created_count} tugas preset ditambahkan.`, "success");
      await loadDetail();
    } catch (err) {
      pushToast(getErrMsg(err, "Gagal menerapkan preset."), "error");
    }
  };

  const openNewTask = () => {
    setEditingTaskId(null);
    setTaskTitle("");
    setTaskTitleErr("");
    setTaskPhase("preparation");
    setTaskPriority("medium");
    setTaskDue(activeExam?.starts_on ?? "2026-12-01");
    setTaskPicId("");
    setTaskState("todo");
    setShowTaskModal(true);
  };

  const openEditTask = (t: TaskItem) => {
    setEditingTaskId(t.id);
    setTaskTitle(t.title);
    setTaskTitleErr("");
    setTaskPhase(t.phase);
    setTaskPriority(t.priority);
    setTaskDue(t.due_date);
    setTaskPicId(t.pic_id ?? "");
    setTaskState(t.state);
    setShowTaskModal(true);
  };

  const handleSaveTask = async () => {
    if (!activeExam) return;
    if (!taskTitle.trim()) {
      setTaskTitleErr("Judul tugas wajib diisi.");
      return;
    }
    try {
      await invokeBridge("tsk.tasks.save", {
        institution_id: institutionId,
        exam_id: activeExam.id,
        id: editingTaskId,
        phase: taskPhase,
        title: taskTitle.trim(),
        priority: taskPriority,
        due_date: taskDue,
        pic_id: taskPicId || null,
        state: taskState,
      });
      setShowTaskModal(false);
      pushToast("Tugas disimpan.", "success");
      await loadDetail();
    } catch (err) {
      pushToast(getErrMsg(err, "Gagal menyimpan tugas."), "error");
    }
  };

  const handleAttachEvidence = async () => {
    if (!activeExam || !evidenceTask || !evAsset.trim()) return;
    try {
      await invokeBridge("tsk.evidence.attach", {
        institution_id: institutionId,
        exam_id: activeExam.id,
        task_id: evidenceTask.id,
        evidence_asset_id: evAsset.trim(),
        evidence_note: evNote,
        completed_by: evActor.trim() || "Operator",
        mark_done: true,
      });
      setEvidenceTask(null);
      pushToast("Bukti dilampirkan dan tugas diselesaikan.", "success");
      await loadDetail();
    } catch (err) {
      pushToast(getErrMsg(err, "Gagal melampirkan bukti."), "error");
    }
  };

  if (!activeExam) {
    return (
      <section className="uc-panel">
        <div className="uc-panel-body">
          <p className="uc-sub">
            Pilih atau buat kegiatan ujian terlebih dahulu di menu Kegiatan
            Ujian.
          </p>
        </div>
      </section>
    );
  }

  const readOnly = detail?.is_archived ?? false;

  return (
    <div style={{ display: "grid", gap: "var(--space-4)" }}>
      <section className="uc-panel">
        <div
          className="uc-panel-body"
          style={{
            display: "flex",
            flexWrap: "wrap",
            gap: "var(--space-3)",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
            <Button
              variant={view === "table" ? "primary" : "secondary"}
              onClick={() => setView("table")}
            >
              <ListTodo size={16} aria-hidden="true" />
              Daftar Tugas
            </Button>
            <Button
              variant={view === "timeline" ? "primary" : "secondary"}
              onClick={() => setView("timeline")}
            >
              <CalendarDays size={16} aria-hidden="true" />
              Timeline
            </Button>
            {detail && (
              <StatusIndicator
                tone={detail.overdue_count > 0 ? "warning" : "success"}
                label={`Terlambat: ${detail.overdue_count}`}
              />
            )}
          </div>

          <div style={{ display: "flex", gap: 8 }}>
            <Button
              variant="secondary"
              disabled={readOnly}
              onClick={() => void handleApplyPreset()}
            >
              <Sparkles size={16} aria-hidden="true" />
              Terapkan Preset
            </Button>
            <Button variant="primary" disabled={readOnly} onClick={openNewTask}>
              <Plus size={16} aria-hidden="true" />
              Tambah Tugas
            </Button>
          </div>
        </div>
      </section>

      <section className="uc-panel">
        <div
          className="uc-panel-body"
          style={{ display: "flex", flexWrap: "wrap", gap: 10, alignItems: "center" }}
        >
          <input
            type="search"
            className="uc-input"
            placeholder="Cari judul tugas..."
            aria-label="Cari tugas"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <select
            className="uc-input"
            aria-label="Filter Tahap"
            value={filterPhase}
            onChange={(e) => setFilterPhase(e.target.value)}
          >
            <option value="">Semua Tahap</option>
            <option value="preparation">Persiapan</option>
            <option value="implementation">Pelaksanaan</option>
            <option value="closing">Penutupan</option>
          </select>
          <select
            className="uc-input"
            aria-label="Filter Status"
            value={filterState}
            onChange={(e) => setFilterState(e.target.value)}
          >
            <option value="">Semua Status</option>
            <option value="todo">Belum Mulai</option>
            <option value="in_progress">Berjalan</option>
            <option value="blocked">Terhambat</option>
            <option value="done">Selesai</option>
          </select>
          <label style={{ display: "flex", gap: 6, alignItems: "center" }}>
            <input
              type="checkbox"
              checked={onlyMissingPic}
              onChange={(e) => setOnlyMissingPic(e.target.checked)}
            />
            <span>Hanya tanpa PIC</span>
          </label>
        </div>
      </section>

      {!detail ? (
        <section className="uc-panel">
          <div className="uc-panel-body">
            <p className="uc-sub">
              {loading ? "Memuat tugas..." : "Tidak ada data."}
            </p>
          </div>
        </section>
      ) : view === "table" ? (
        <section className="uc-panel">
          <div className="uc-panel-body" style={{ overflowX: "auto" }}>
            <table className="uc-table" aria-label="Tabel Tugas Panitia">
              <thead>
                <tr>
                  <th>Tugas</th>
                  <th>Tahap</th>
                  <th>PIC</th>
                  <th>Tenggat</th>
                  <th>Status</th>
                  <th>Aksi</th>
                </tr>
              </thead>
              <tbody>
                {filteredTasks.map((t) => (
                  <tr key={t.id}>
                    <td>
                      <strong>{t.title}</strong>
                      {t.dependencies.length > 0 && (
                        <div className="uc-sub" style={{ fontSize: 12 }}>
                          Prasyarat: {t.dependencies.length} tugas
                        </div>
                      )}
                    </td>
                    <td>{t.phase}</td>
                    <td>
                      {t.pic_name ? (
                        t.pic_name
                      ) : (
                        <StatusIndicator tone="warning" label="Belum ada PIC" />
                      )}
                    </td>
                    <td>
                      {t.due_date}{" "}
                      {t.is_overdue && (
                        <StatusIndicator tone="destructive" label="Terlambat" />
                      )}
                    </td>
                    <td>{t.state}</td>
                    <td style={{ display: "flex", gap: 6 }}>
                      <Button
                        variant="secondary"
                        size="sm"
                        disabled={readOnly}
                        onClick={() => openEditTask(t)}
                      >
                        Ubah
                      </Button>
                      <Button
                        variant="secondary"
                        size="sm"
                        disabled={readOnly}
                        aria-label={`Lampirkan bukti ${t.title}`}
                        onClick={() => {
                          setEvidenceTask(t);
                          setEvAsset(t.evidence_asset_id ?? "");
                          setEvNote(t.evidence_note ?? "");
                        }}
                      >
                        <Paperclip size={14} aria-hidden="true" />
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ) : (
        <div style={{ display: "grid", gap: "var(--space-3)" }}>
          {timelineGroups.map(([dt, items]) => (
            <section key={dt} className="uc-panel">
              <div className="uc-panel-header">
                <h2>{dt}</h2>
              </div>
              <div className="uc-panel-body" style={{ display: "grid", gap: 6 }}>
                {items.map((t) => (
                  <div
                    key={t.id}
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                    }}
                  >
                    <span>
                      <strong>{t.title}</strong> ({t.phase})
                    </span>
                    <StatusIndicator
                      tone={
                        t.state === "done"
                          ? "success"
                          : t.is_overdue
                            ? "destructive"
                            : "neutral"
                      }
                      label={t.state}
                    />
                  </div>
                ))}
              </div>
            </section>
          ))}
        </div>
      )}

      <CRUDModal
        open={showTaskModal}
        title={editingTaskId ? "Ubah Tugas" : "Tambah Tugas"}
        onClose={() => setShowTaskModal(false)}
        onSubmit={() => void handleSaveTask()}
      >
        <div style={{ display: "grid", gap: 12 }}>
          <label className="uc-field">
            <span className="uc-label">Judul Tugas</span>
            <input
              type="text"
              className="uc-input"
              value={taskTitle}
              onChange={(e) => {
                setTaskTitle(e.target.value);
                setTaskTitleErr("");
              }}
            />
            {taskTitleErr && <span className="uc-field-error">{taskTitleErr}</span>}
          </label>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
            <label className="uc-field">
              <span className="uc-label">Tahap</span>
              <select
                className="uc-input"
                value={taskPhase}
                onChange={(e) => setTaskPhase(e.target.value as TaskPhase)}
              >
                <option value="preparation">Persiapan</option>
                <option value="implementation">Pelaksanaan</option>
                <option value="closing">Penutupan</option>
              </select>
            </label>
            <label className="uc-field">
              <span className="uc-label">Prioritas</span>
              <select
                className="uc-input"
                value={taskPriority}
                onChange={(e) => setTaskPriority(e.target.value as TaskPriority)}
              >
                <option value="low">Rendah</option>
                <option value="medium">Sedang</option>
                <option value="high">Tinggi</option>
                <option value="critical">Kritis</option>
              </select>
            </label>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
            <label className="uc-field">
              <span className="uc-label">Tenggat</span>
              <input
                type="date"
                className="uc-input"
                value={taskDue}
                onChange={(e) => setTaskDue(e.target.value)}
              />
            </label>
            <label className="uc-field">
              <span className="uc-label">Status</span>
              <select
                className="uc-input"
                value={taskState}
                onChange={(e) => setTaskState(e.target.value as TaskState)}
              >
                <option value="todo">Belum Mulai</option>
                <option value="in_progress">Berjalan</option>
                <option value="blocked">Terhambat</option>
                <option value="done">Selesai</option>
              </select>
            </label>
          </div>
          <label className="uc-field">
            <span className="uc-label">PIC (opsional)</span>
            <select
              className="uc-input"
              value={taskPicId}
              onChange={(e) => setTaskPicId(e.target.value)}
            >
              <option value="">-- Belum ditentukan --</option>
              {(detail?.staff ?? []).map((st) => (
                <option key={st.id} value={st.id}>
                  {st.display_name}
                </option>
              ))}
            </select>
          </label>
        </div>
      </CRUDModal>

      <CRUDModal
        open={evidenceTask !== null}
        title={`Lampirkan Bukti · ${evidenceTask?.title ?? ""}`}
        onClose={() => setEvidenceTask(null)}
        onSubmit={() => void handleAttachEvidence()}
        submitLabel="Simpan & Selesaikan"
      >
        <div style={{ display: "grid", gap: 12 }}>
          <label className="uc-field">
            <span className="uc-label">Referensi Berkas Bukti</span>
            <input
              type="text"
              className="uc-input"
              placeholder="mis. assets/berita-acara.pdf"
              value={evAsset}
              onChange={(e) => setEvAsset(e.target.value)}
            />
          </label>
          <label className="uc-field">
            <span className="uc-label">Catatan Penyelesaian</span>
            <textarea
              rows={2}
              className="uc-input"
              value={evNote}
              onChange={(e) => setEvNote(e.target.value)}
            />
          </label>
          <label className="uc-field">
            <span className="uc-label">Pelaksana</span>
            <input
              type="text"
              className="uc-input"
              value={evActor}
              onChange={(e) => setEvActor(e.target.value)}
            />
          </label>
        </div>
      </CRUDModal>
    </div>
  );
}
