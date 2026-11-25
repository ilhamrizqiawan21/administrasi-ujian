import { useCallback, useEffect, useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  ClipboardCheck,
  FileText,
  Play,
  Plus,
  Users,
} from "lucide-react";
import { Button } from "../../components/ui/Button";
import { StatusIndicator, useToast } from "../../components/ui/Feedback";
import { CRUDModal } from "../../components/ui/Modal";
import { invokeBridge } from "../../lib/bridge";
import type { ExamItem } from "../evt/types";
import type { PlanItem } from "../ses/types";
import type { OpsDetail, OpsRoomSessionItem, StudentAttState } from "./types";

interface ExecutionPageProps {
  institutionId: string;
  activeExam: ExamItem | null;
}

function getErrMsg(err: unknown, fallback: string): string {
  return err instanceof Error ? err.message : fallback;
}

export function ExecutionPage({
  institutionId,
  activeExam,
}: ExecutionPageProps) {
  const { pushToast } = useToast();
  const [plans, setPlans] = useState<PlanItem[]>([]);
  const [activePlanId, setActivePlanId] = useState("");
  const [detail, setDetail] = useState<OpsDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [tab, setTab] = useState<
    "monitor" | "students" | "staff" | "incidents"
  >("monitor");
  const [selectedRsId, setSelectedRsId] = useState("");
  const [includeConfidential, setIncludeConfidential] = useState(false);

  // Berita acara modal
  const [reportRs, setReportRs] = useState<OpsRoomSessionItem | null>(null);
  const [remarks, setRemarks] = useState("");
  const [signerName, setSignerName] = useState("");

  // Incident modal
  const [showIncidentModal, setShowIncidentModal] = useState(false);
  const [incType, setIncType] = useState<"late" | "violation" | "technical" | "other">("other");
  const [incSeverity, setIncSeverity] = useState<"low" | "medium" | "high">("low");
  const [incNote, setIncNote] = useState("");
  const [incConf, setIncConf] = useState(false);

  const loadPlans = useCallback(async () => {
    if (!activeExam) {
      setPlans([]);
      setActivePlanId("");
      setDetail(null);
      return;
    }
    try {
      const data = await invokeBridge<{ items: PlanItem[] }>("ses.plans.list", {
        institution_id: institutionId,
        exam_id: activeExam.id,
      });
      setPlans(data.items);
      if (data.items.length > 0) {
        setActivePlanId((prev) =>
          data.items.some((p) => p.id === prev) ? prev : data.items[0].id
        );
      } else {
        setActivePlanId("");
        setDetail(null);
      }
    } catch (err) {
      pushToast(getErrMsg(err, "Gagal memuat rencana jadwal."), "error");
    }
  }, [institutionId, activeExam, pushToast]);

  const loadDetail = useCallback(
    async (planId: string) => {
      if (!activeExam || !planId) {
        setDetail(null);
        return;
      }
      setLoading(true);
      try {
        const data = await invokeBridge<OpsDetail>("ops.detail", {
          institution_id: institutionId,
          exam_id: activeExam.id,
          plan_id: planId,
          include_confidential: includeConfidential,
        });
        setDetail(data);
        if (data.room_sessions.length > 0 && !selectedRsId) {
          setSelectedRsId(data.room_sessions[0].room_session_id);
        }
      } catch (err) {
        pushToast(getErrMsg(err, "Gagal memuat pelaksanaan ujian."), "error");
      } finally {
        setLoading(false);
      }
    },
    [institutionId, activeExam, includeConfidential, pushToast, selectedRsId]
  );

  useEffect(() => {
    void loadPlans();
  }, [loadPlans]);

  useEffect(() => {
    if (activePlanId) {
      void loadDetail(activePlanId);
    }
  }, [activePlanId, loadDetail]);

  const activeRs = detail?.room_sessions.find(
    (rs) => rs.room_session_id === selectedRsId
  );

  const handleRoomState = async (
    rsId: string,
    actualState: "scheduled" | "in_progress" | "finished"
  ) => {
    if (!activeExam || !activePlanId) return;
    try {
      await invokeBridge("ops.room_session.state", {
        institution_id: institutionId,
        exam_id: activeExam.id,
        plan_id: activePlanId,
        room_session_id: rsId,
        actual_state: actualState,
      });
      pushToast("Status sesi ruang diperbarui.", "success");
      await loadDetail(activePlanId);
    } catch (err) {
      pushToast(getErrMsg(err, "Gagal memperbarui status ruang."), "error");
    }
  };

  const handleMarkStudent = async (
    sittingIds: string[],
    state: StudentAttState
  ) => {
    if (!activeExam || !activePlanId || sittingIds.length === 0) return;
    try {
      await invokeBridge("ops.students.attendance", {
        institution_id: institutionId,
        exam_id: activeExam.id,
        sitting_ids: sittingIds,
        state,
      });
      pushToast("Kehadiran peserta disimpan.", "success");
      await loadDetail(activePlanId);
    } catch (err) {
      pushToast(getErrMsg(err, "Gagal menyimpan kehadiran peserta."), "error");
    }
  };

  const handleFinalizeReport = async (finalize: boolean) => {
    if (!activeExam || !activePlanId || !reportRs) return;
    try {
      const method = finalize ? "ops.reports.finalize" : "ops.reports.save";
      const res = await invokeBridge<{ warnings: string[] }>(method, {
        institution_id: institutionId,
        exam_id: activeExam.id,
        plan_id: activePlanId,
        room_session_id: reportRs.room_session_id,
        remarks,
        signer_name: signerName,
      });
      setReportRs(null);
      if (res.warnings.length > 0) {
        pushToast(res.warnings[0], "info");
      } else {
        pushToast(
          finalize ? "Berita acara difinalisasi." : "Berita acara disimpan.",
          "success"
        );
      }
      await loadDetail(activePlanId);
    } catch (err) {
      pushToast(getErrMsg(err, "Gagal menyimpan berita acara."), "error");
    }
  };

  const handleRecordIncident = async () => {
    if (!activeExam || !selectedRsId || !incNote.trim()) return;
    try {
      await invokeBridge("ops.incidents.record", {
        institution_id: institutionId,
        exam_id: activeExam.id,
        room_session_id: selectedRsId,
        type_code: incType,
        severity: incSeverity,
        note: incNote.trim(),
        confidential: incConf,
      });
      setShowIncidentModal(false);
      setIncNote("");
      pushToast("Insiden dicatat.", "success");
      await loadDetail(activePlanId);
    } catch (err) {
      pushToast(getErrMsg(err, "Gagal mencatat insiden."), "error");
    }
  };

  const handleClosingComplete = async () => {
    if (!activeExam || !activePlanId) return;
    try {
      await invokeBridge("ops.closing.complete", {
        institution_id: institutionId,
        exam_id: activeExam.id,
        plan_id: activePlanId,
      });
      pushToast("Penutupan ujian diverifikasi lengkap.", "success");
    } catch (err) {
      pushToast(getErrMsg(err, "Penutupan belum dapat diselesaikan."), "error");
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
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
            <Button
              variant={tab === "monitor" ? "primary" : "secondary"}
              onClick={() => setTab("monitor")}
            >
              <Play size={16} aria-hidden="true" />
              Monitor &amp; Berita Acara
            </Button>
            <Button
              variant={tab === "students" ? "primary" : "secondary"}
              onClick={() => setTab("students")}
            >
              <Users size={16} aria-hidden="true" />
              Presensi Peserta
            </Button>
            <Button
              variant={tab === "staff" ? "primary" : "secondary"}
              onClick={() => setTab("staff")}
            >
              <ClipboardCheck size={16} aria-hidden="true" />
              Presensi Pengawas &amp; Panitia
            </Button>
            <Button
              variant={tab === "incidents" ? "primary" : "secondary"}
              onClick={() => setTab("incidents")}
            >
              <AlertTriangle size={16} aria-hidden="true" />
              Insiden &amp; Susulan ({detail?.incidents.length ?? 0})
            </Button>
          </div>
          <Button variant="secondary" onClick={() => void handleClosingComplete()}>
            <CheckCircle2 size={16} aria-hidden="true" />
            Verifikasi Penutupan
          </Button>
        </div>
      </section>

      {!detail ? (
        <section className="uc-panel">
          <div className="uc-panel-body">
            <p className="uc-sub">
              {loading
                ? "Memuat monitor pelaksanaan..."
                : "Buat rencana jadwal terlebih dahulu."}
            </p>
          </div>
        </section>
      ) : tab === "monitor" ? (
        <section className="uc-panel">
          <div className="uc-panel-header">
            <h2>Monitor Sesi Ruang</h2>
            <select
              className="uc-input"
              aria-label="Pilih Versi Rencana"
              value={activePlanId}
              onChange={(e) => setActivePlanId(e.target.value)}
            >
              {plans.map((p) => (
                <option key={p.id} value={p.id}>
                  v{p.version} ({p.state})
                </option>
              ))}
            </select>
          </div>
          <div className="uc-panel-body" style={{ overflowX: "auto" }}>
            <table className="uc-table" aria-label="Monitor Sesi Ruang">
              <thead>
                <tr>
                  <th>Tanggal &amp; Sesi</th>
                  <th>Ruang</th>
                  <th>Status</th>
                  <th>Hadir / Belum Dicatat / Alpa</th>
                  <th>Berita Acara</th>
                  <th>Aksi</th>
                </tr>
              </thead>
              <tbody>
                {detail.room_sessions.map((rs) => (
                  <tr key={rs.room_session_id}>
                    <td>
                      {rs.local_date} · {rs.session_label}
                    </td>
                    <td>
                      {rs.room_code} · {rs.room_name}
                    </td>
                    <td>
                      <StatusIndicator
                        tone={
                          rs.actual_state === "finished"
                            ? "success"
                            : rs.actual_state === "in_progress"
                              ? "warning"
                              : "neutral"
                        }
                        label={rs.actual_state}
                      />
                    </td>
                    <td>
                      {rs.counts.present} / {rs.counts.unrecorded} /{" "}
                      {rs.counts.absent}
                    </td>
                    <td>
                      {rs.report.finalized_at ? "Final" : "Draf"}
                    </td>
                    <td style={{ display: "flex", gap: 6 }}>
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() =>
                          void handleRoomState(
                            rs.room_session_id,
                            rs.actual_state === "scheduled"
                              ? "in_progress"
                              : "finished"
                          )
                        }
                      >
                        {rs.actual_state === "scheduled" ? "Mulai" : "Selesai"}
                      </Button>
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => {
                          setReportRs(rs);
                          setRemarks(rs.report.remarks);
                          setSignerName("");
                        }}
                      >
                        <FileText size={14} aria-hidden="true" />
                        Berita Acara
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ) : tab === "students" ? (
        <section className="uc-panel">
          <div className="uc-panel-header">
            <select
              className="uc-input"
              aria-label="Pilih Ruang Sesi"
              value={selectedRsId}
              onChange={(e) => setSelectedRsId(e.target.value)}
            >
              {detail.room_sessions.map((rs) => (
                <option key={rs.room_session_id} value={rs.room_session_id}>
                  {rs.room_code} · {rs.session_label}
                </option>
              ))}
            </select>
            <Button
              variant="primary"
              size="sm"
              disabled={!activeRs || activeRs.sittings.length === 0}
              onClick={() =>
                void handleMarkStudent(
                  (activeRs?.sittings ?? []).map((s) => s.sitting_id),
                  "present"
                )
              }
            >
              Tandai Semua Hadir
            </Button>
          </div>
          <div className="uc-panel-body" style={{ overflowX: "auto" }}>
            <table className="uc-table" aria-label="Presensi Peserta">
              <thead>
                <tr>
                  <th>Nomor</th>
                  <th>Nama Peserta</th>
                  <th>Status</th>
                  <th>Ubah</th>
                </tr>
              </thead>
              <tbody>
                {(activeRs?.sittings ?? []).map((s) => (
                  <tr key={s.sitting_id}>
                    <td>{s.participant_number ?? "-"}</td>
                    <td>{s.display_name}</td>
                    <td>{s.state}</td>
                    <td style={{ display: "flex", gap: 6 }}>
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() =>
                          void handleMarkStudent([s.sitting_id], "present")
                        }
                      >
                        Hadir
                      </Button>
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() =>
                          void handleMarkStudent([s.sitting_id], "absent")
                        }
                      >
                        Alpa
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ) : tab === "staff" ? (
        <section className="uc-panel">
          <div className="uc-panel-header">
            <h2>Presensi Pengawas &amp; Panitia</h2>
          </div>
          <div className="uc-panel-body" style={{ overflowX: "auto" }}>
            <table className="uc-table" aria-label="Presensi Pengawas">
              <thead>
                <tr>
                  <th>Slot</th>
                  <th>Perencanaan</th>
                  <th>Aktual</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {detail.staff_slots.map((sl) => (
                  <tr key={sl.slot_id}>
                    <td>{sl.role_code}</td>
                    <td>{sl.planned_name ?? "-"}</td>
                    <td>{sl.actual_name ?? "-"}</td>
                    <td>{sl.state}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ) : (
        <section className="uc-panel">
          <div className="uc-panel-header">
            <label style={{ display: "flex", gap: 6, alignItems: "center" }}>
              <input
                type="checkbox"
                checked={includeConfidential}
                onChange={(e) => setIncludeConfidential(e.target.checked)}
              />
              <span>Tampilkan catatan rahasia</span>
            </label>
            <Button
              variant="primary"
              size="sm"
              disabled={!selectedRsId}
              onClick={() => setShowIncidentModal(true)}
            >
              <Plus size={14} aria-hidden="true" />
              Catat Insiden
            </Button>
          </div>
          <div className="uc-panel-body" style={{ overflowX: "auto" }}>
            <table className="uc-table" aria-label="Log Insiden">
              <thead>
                <tr>
                  <th>Jenis</th>
                  <th>Tingkat</th>
                  <th>Catatan</th>
                  <th>Rahasia</th>
                </tr>
              </thead>
              <tbody>
                {detail.incidents.map((inc) => (
                  <tr key={inc.id}>
                    <td>{inc.type_code}</td>
                    <td>{inc.severity}</td>
                    <td>{inc.note}</td>
                    <td>{inc.confidential ? "Ya" : "Tidak"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      <CRUDModal
        open={reportRs !== null}
        title={`Berita Acara · ${reportRs?.room_code ?? ""}`}
        onClose={() => setReportRs(null)}
        onSubmit={() => void handleFinalizeReport(true)}
        submitLabel="Finalisasi"
      >
        <div style={{ display: "grid", gap: 12 }}>
          <label className="uc-field">
            <span className="uc-label">Nama Penanda Tangan</span>
            <input
              type="text"
              className="uc-input"
              value={signerName}
              onChange={(e) => setSignerName(e.target.value)}
            />
          </label>
          <label className="uc-field">
            <span className="uc-label">Catatan Pelaksanaan</span>
            <textarea
              rows={3}
              className="uc-input"
              value={remarks}
              onChange={(e) => setRemarks(e.target.value)}
            />
          </label>
        </div>
      </CRUDModal>

      <CRUDModal
        open={showIncidentModal}
        title="Catat Insiden Ujian"
        onClose={() => setShowIncidentModal(false)}
        onSubmit={() => void handleRecordIncident()}
      >
        <div style={{ display: "grid", gap: 12 }}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
            <label className="uc-field">
              <span className="uc-label">Jenis</span>
              <select
                className="uc-input"
                value={incType}
                onChange={(e) =>
                  setIncType(
                    e.target.value as "late" | "violation" | "technical" | "other"
                  )
                }
              >
                <option value="late">Terlambat</option>
                <option value="violation">Pelanggaran</option>
                <option value="technical">Teknis</option>
                <option value="other">Lainnya</option>
              </select>
            </label>
            <label className="uc-field">
              <span className="uc-label">Tingkat</span>
              <select
                className="uc-input"
                value={incSeverity}
                onChange={(e) =>
                  setIncSeverity(e.target.value as "low" | "medium" | "high")
                }
              >
                <option value="low">Rendah</option>
                <option value="medium">Sedang</option>
                <option value="high">Tinggi</option>
              </select>
            </label>
          </div>
          <label className="uc-field">
            <span className="uc-label">Uraian Insiden</span>
            <textarea
              rows={3}
              className="uc-input"
              value={incNote}
              onChange={(e) => setIncNote(e.target.value)}
            />
          </label>
          <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <input
              type="checkbox"
              checked={incConf}
              onChange={(e) => setIncConf(e.target.checked)}
            />
            <span>Bersifat rahasia (tidak diekspor standar)</span>
          </label>
        </div>
      </CRUDModal>
    </div>
  );
}
