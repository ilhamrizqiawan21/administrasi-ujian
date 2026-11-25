import { useCallback, useEffect, useMemo, useState } from "react";
import { CheckCircle2, Lock, Plus, Shuffle, Unlock } from "lucide-react";
import { Button, IconButton } from "../../components/ui/Button";
import { StatePanel, StatusIndicator, useToast } from "../../components/ui/Feedback";
import { DateField, SelectField, TextField } from "../../components/ui/FormFields";
import { CRUDModal } from "../../components/ui/Modal";
import { invokeBridge } from "../../lib/bridge";
import type { ExamItem } from "../evt/types";
import type { PlanDetail, PlanItem, ScheduleConflict } from "./types";

export interface TimetablePageProps {
  institutionId: string;
  activeExam: ExamItem | null;
}

export function TimetablePage({ institutionId, activeExam }: TimetablePageProps) {
  const { pushToast } = useToast();
  const [plans, setPlans] = useState<PlanItem[]>([]);
  const [activePlanId, setActivePlanId] = useState<string>("");
  const [detail, setDetail] = useState<PlanDetail | null>(null);
  const [conflicts, setConflicts] = useState<ScheduleConflict[]>([]);
  const [dateFilter, setDateFilter] = useState<string>("ALL");

  const [sessionModalOpen, setSessionModalOpen] = useState(false);
  const [sessionForm, setSessionForm] = useState({
    label: "",
    local_date: activeExam?.starts_on ?? "2026-11-30",
    start_local: "07:30",
    end_local: "09:00",
    mode: "paper" as "paper" | "cbt" | "practice" | "hybrid",
  });

  const [assignModalOpen, setAssignModalOpen] = useState(false);
  const [assignForm, setAssignForm] = useState({
    requirement_id: "",
    session_id: "",
    exam_room_id: "",
  });

  const loadPlans = useCallback(async () => {
    if (!activeExam) {
      setPlans([]);
      setDetail(null);
      return;
    }
    const res = await invokeBridge<{ items: PlanItem[] }>("ses.plans.list", {
      institution_id: institutionId,
      exam_id: activeExam.id,
    });
    setPlans(res.items);
    setActivePlanId((prev) =>
      res.items.some((p) => p.id === prev) ? prev : (res.items[0]?.id ?? "")
    );
  }, [institutionId, activeExam]);

  const loadDetail = useCallback(async () => {
    if (!activeExam || !activePlanId) {
      setDetail(null);
      return;
    }
    const res = await invokeBridge<PlanDetail>("ses.plans.detail", {
      institution_id: institutionId,
      exam_id: activeExam.id,
      plan_id: activePlanId,
    });
    setDetail(res);
  }, [institutionId, activeExam, activePlanId]);

  useEffect(() => {
    void loadPlans();
  }, [loadPlans]);

  useEffect(() => {
    void loadDetail();
  }, [loadDetail]);

  const dates = useMemo(() => {
    if (!detail) return [];
    return Array.from(new Set(detail.sessions.map((s) => s.local_date))).sort();
  }, [detail]);

  const visibleSessions = useMemo(() => {
    if (!detail) return [];
    return dateFilter === "ALL"
      ? detail.sessions
      : detail.sessions.filter((s) => s.local_date === dateFilter);
  }, [detail, dateFilter]);

  if (!activeExam) {
    return (
      <section className="uc-panel">
        <StatePanel
          kind="empty"
          title="Belum ada kegiatan ujian"
          description="Pilih atau buat kegiatan ujian untuk menyusun sesi dan jadwal ujian."
        />
      </section>
    );
  }

  async function handleCreateDraft() {
    if (!activeExam) return;
    const res = await invokeBridge<{ plan: PlanItem }>("ses.plans.create", {
      institution_id: institutionId,
      exam_id: activeExam.id,
      clone_from_plan_id: activePlanId || null,
    });
    setActivePlanId(res.plan.id);
    await loadPlans();
    pushToast(`Draf revisi v${res.plan.version} dibuat.`, "success");
  }

  async function handleSaveSession() {
    if (!activeExam || !detail) return;
    try {
      await invokeBridge("ses.sessions.save", {
        institution_id: institutionId,
        exam_id: activeExam.id,
        plan_id: detail.plan.id,
        label: sessionForm.label,
        local_date: sessionForm.local_date,
        start_local: sessionForm.start_local,
        end_local: sessionForm.end_local,
        sort_order: detail.sessions.length + 1,
        mode: sessionForm.mode,
      });
      setSessionModalOpen(false);
      await loadDetail();
      pushToast("Sesi ujian disimpan.", "success");
    } catch (err: unknown) {
      pushToast(err instanceof Error ? err.message : "Gagal menyimpan sesi.", "error");
    }
  }

  async function handleAssignPaper() {
    if (!activeExam || !detail) return;
    try {
      await invokeBridge("ses.papers.assign", {
        institution_id: institutionId,
        exam_id: activeExam.id,
        plan_id: detail.plan.id,
        expected_revision: detail.plan.revision,
        requirement_id: assignForm.requirement_id,
        session_id: assignForm.session_id,
        exam_room_id: assignForm.exam_room_id,
      });
      setAssignModalOpen(false);
      await loadDetail();
      pushToast("Jadwal mapel ditempatkan.", "success");
    } catch (err: unknown) {
      pushToast(err instanceof Error ? err.message : "Penempatan ditolak.", "error");
    }
  }

  async function handleAutoGenerate() {
    if (!activeExam || !detail) return;
    try {
      const res = await invokeBridge<{
        ok: boolean;
        status: string;
        assigned_count?: number;
        diagnostics?: string[];
      }>("ses.schedule.auto_generate", {
        institution_id: institutionId,
        exam_id: activeExam.id,
        plan_id: detail.plan.id,
        expected_revision: detail.plan.revision,
      });
      if (!res.ok) {
        pushToast(res.diagnostics?.[0] ?? `Status solver: ${res.status}`, "error");
        return;
      }
      await loadDetail();
      pushToast(`Draf otomatis terisi (${res.assigned_count} penempatan).`, "success");
    } catch (err: unknown) {
      pushToast(err instanceof Error ? err.message : "Gagal generate jadwal.", "error");
    }
  }

  async function handleValidate() {
    if (!activeExam || !detail) return;
    const res = await invokeBridge<{
      valid: boolean;
      conflicts: ScheduleConflict[];
    }>("ses.plans.validate", {
      institution_id: institutionId,
      exam_id: activeExam.id,
      plan_id: detail.plan.id,
    });
    setConflicts(res.conflicts);
    await loadPlans();
    await loadDetail();
    pushToast(
      res.valid
        ? "Validasi jadwal lulus tanpa konflik."
        : `Ditemukan ${res.conflicts.length} konflik jadwal.`,
      res.valid ? "success" : "error"
    );
  }

  async function handlePublish() {
    if (!activeExam || !detail) return;
    try {
      await invokeBridge("ses.plans.publish", {
        institution_id: institutionId,
        exam_id: activeExam.id,
        plan_id: detail.plan.id,
        expected_revision: detail.plan.revision,
      });
      await loadPlans();
      await loadDetail();
      pushToast(`Rencana v${detail.plan.version} diterbitkan.`, "success");
    } catch (err: unknown) {
      pushToast(err instanceof Error ? err.message : "Gagal menerbitkan.", "error");
    }
  }

  return (
    <div style={{ display: "grid", gap: 16 }}>
      <div className="uc-actions">
        {plans.length > 0 && (
          <select
            className="uc-select"
            style={{ width: "auto" }}
            aria-label="Revisi rencana jadwal"
            value={activePlanId}
            onChange={(e) => setActivePlanId(e.target.value)}
          >
            {plans.map((p) => (
              <option key={p.id} value={p.id}>
                Revisi v{p.version} · {p.state}
              </option>
            ))}
          </select>
        )}
        <Button variant="secondary" size="sm" onClick={handleCreateDraft}>
          <Plus size={14} aria-hidden="true" />
          Buat Draf Revisi
        </Button>

        {detail && detail.plan.state !== "published" && detail.plan.state !== "superseded" && (
          <>
            <Button
              variant="neutral"
              size="sm"
              onClick={() => {
                setSessionForm({
                  label: `Sesi ${detail.sessions.length + 1}`,
                  local_date: activeExam.starts_on,
                  start_local: "07:30",
                  end_local: "09:00",
                  mode: "paper",
                });
                setSessionModalOpen(true);
              }}
            >
              Tambah Sesi
            </Button>
            <Button
              variant="neutral"
              size="sm"
              onClick={() => {
                setAssignForm({
                  requirement_id: detail.requirements[0]?.id ?? "",
                  session_id: detail.sessions[0]?.id ?? "",
                  exam_room_id: detail.rooms[0]?.id ?? "",
                });
                setAssignModalOpen(true);
              }}
            >
              Tempatkan Mapel
            </Button>
            <Button variant="secondary" size="sm" onClick={handleAutoGenerate}>
              <Shuffle size={14} aria-hidden="true" />
              Generate Otomatis
            </Button>
            <Button variant="neutral" size="sm" onClick={handleValidate}>
              <CheckCircle2 size={14} aria-hidden="true" />
              Validasi
            </Button>
            <Button variant="primary" size="sm" onClick={handlePublish}>
              Terbitkan
            </Button>
          </>
        )}
      </div>

      {!detail ? (
        <section className="uc-panel">
          <StatePanel
            kind="empty"
            title="Belum ada revisi rencana jadwal"
            description="Buat draf revisi baru untuk mendefinisikan sesi, ruang, dan penempatan mata pelajaran."
            actionLabel="Buat Draf Revisi"
            onAction={handleCreateDraft}
          />
        </section>
      ) : (
        <>
          {detail.session_overlaps.length > 0 && (
            <div className="uc-callout">
              <div>
                <strong>Peringatan Interval Sesi:</strong>{" "}
                {detail.session_overlaps.map((o) => o.message).join(" ")}
              </div>
            </div>
          )}

          <section className="uc-panel">
            <div className="uc-panel-head">
              <h2>Kisi Jadwal · Revisi v{detail.plan.version}</h2>
              <div className="uc-actions">
                <select
                  className="uc-select"
                  style={{ width: "auto", height: 32 }}
                  aria-label="Filter tanggal"
                  value={dateFilter}
                  onChange={(e) => setDateFilter(e.target.value)}
                >
                  <option value="ALL">Semua Tanggal</option>
                  {dates.map((d) => (
                    <option key={d} value={d}>
                      {d}
                    </option>
                  ))}
                </select>
                <StatusIndicator
                  label={detail.plan.state}
                  tone={detail.plan.state === "published" ? "success" : "warning"}
                />
              </div>
            </div>

            <div className="uc-table-wrap">
              <table className="uc-table">
                <thead>
                  <tr>
                    <th scope="col">Ruang</th>
                    {visibleSessions.map((ses) => (
                      <th key={ses.id} scope="col">
                        {ses.label}
                        <div className="uc-sub">
                          {ses.local_date} · {ses.start_local}–{ses.end_local}
                        </div>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {detail.rooms.map((rm) => (
                    <tr key={rm.id}>
                      <td className="uc-td-left">
                        <strong>{rm.code}</strong> · {rm.name}
                      </td>
                      {visibleSessions.map((ses) => {
                        const cellPapers = detail.papers.filter(
                          (p) => p.exam_room_id === rm.id && p.session_id === ses.id
                        );
                        return (
                          <td key={ses.id} className="uc-td-center">
                            {cellPapers.length === 0 ? (
                              <span className="uc-sub">—</span>
                            ) : (
                              cellPapers.map((cp) => {
                                const req = detail.requirements.find(
                                  (r) => r.id === cp.requirement_id
                                );
                                return (
                                  <div
                                    key={cp.id}
                                    style={{
                                      display: "inline-flex",
                                      alignItems: "center",
                                      gap: 6,
                                    }}
                                  >
                                    <span>
                                      {req?.subject_code} ({req?.group_label})
                                    </span>
                                    <IconButton
                                      label={cp.locked ? "Buka kunci" : "Kunci sel"}
                                      icon={
                                        cp.locked ? (
                                          <Lock size={14} aria-hidden="true" />
                                        ) : (
                                          <Unlock size={14} aria-hidden="true" />
                                        )
                                      }
                                      onClick={async () => {
                                        await invokeBridge("ses.papers.lock", {
                                          institution_id: institutionId,
                                          exam_id: activeExam.id,
                                          plan_id: detail.plan.id,
                                          paper_id: cp.id,
                                          locked: !cp.locked,
                                        });
                                        await loadDetail();
                                      }}
                                    />
                                  </div>
                                );
                              })
                            )}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          {conflicts.length > 0 && (
            <section className="uc-panel" role="alert">
              <div className="uc-panel-head">
                <h2>Hasil Validasi Independen ({conflicts.length} Konflik)</h2>
              </div>
              <div className="uc-panel-body" style={{ display: "grid", gap: 8 }}>
                {conflicts.map((c, idx) => (
                  <div key={`${c.code}-${idx}`} className="uc-callout">
                    <div>
                      <strong>{c.code}:</strong> {c.message}
                      <div className="uc-sub">Saran: {c.resolution_path}</div>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          )}
        </>
      )}

      <CRUDModal
        open={sessionModalOpen}
        title="Tambah Sesi Ujian"
        onClose={() => setSessionModalOpen(false)}
        onSubmit={handleSaveSession}
      >
        <div className="uc-field-grid">
          <TextField
            label="Label Sesi"
            value={sessionForm.label}
            onChange={(e) =>
              setSessionForm({ ...sessionForm, label: e.target.value })
            }
          />
          <DateField
            label="Tanggal"
            value={sessionForm.local_date}
            onChange={(e) =>
              setSessionForm({ ...sessionForm, local_date: e.target.value })
            }
          />
          <TextField
            label="Jam Mulai (HH:MM)"
            value={sessionForm.start_local}
            onChange={(e) =>
              setSessionForm({ ...sessionForm, start_local: e.target.value })
            }
          />
          <TextField
            label="Jam Selesai (HH:MM)"
            value={sessionForm.end_local}
            onChange={(e) =>
              setSessionForm({ ...sessionForm, end_local: e.target.value })
            }
          />
        </div>
      </CRUDModal>

      <CRUDModal
        open={assignModalOpen}
        title="Tempatkan Mapel ke Kisi Jadwal"
        onClose={() => setAssignModalOpen(false)}
        onSubmit={handleAssignPaper}
      >
        <div className="uc-field-grid">
          <SelectField
            label="Kelompok & Mapel"
            value={assignForm.requirement_id}
            options={(detail?.requirements ?? []).map((r) => ({
              value: r.id,
              label: `${r.group_label} · ${r.subject_code}`,
            }))}
            onChange={(e) =>
              setAssignForm({ ...assignForm, requirement_id: e.target.value })
            }
          />
          <SelectField
            label="Sesi"
            value={assignForm.session_id}
            options={(detail?.sessions ?? []).map((s) => ({
              value: s.id,
              label: `${s.label} (${s.local_date} ${s.start_local})`,
            }))}
            onChange={(e) =>
              setAssignForm({ ...assignForm, session_id: e.target.value })
            }
          />
          <SelectField
            label="Ruang"
            value={assignForm.exam_room_id}
            options={(detail?.rooms ?? []).map((rm) => ({
              value: rm.id,
              label: `${rm.code} — ${rm.name}`,
            }))}
            onChange={(e) =>
              setAssignForm({ ...assignForm, exam_room_id: e.target.value })
            }
          />
        </div>
      </CRUDModal>
    </div>
  );
}
