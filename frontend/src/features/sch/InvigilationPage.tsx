import { useCallback, useEffect, useMemo, useState } from "react";
import {
  CheckCircle2,
  Lock,
  Plus,
  Sparkles,
  Trash2,
  UserCheck,
  UserX,
} from "lucide-react";
import { Button } from "../../components/ui/Button";
import { StatusIndicator, useToast } from "../../components/ui/Feedback";
import { CRUDModal } from "../../components/ui/Modal";
import { invokeBridge } from "../../lib/bridge";
import type { ExamItem } from "../evt/types";
import type { PlanItem } from "../ses/types";
import type {
  InvigilationDetail,
  InvigilationRules,
  InvigilationSlotItem,
  SchStaffItem,
} from "./types";

interface InvigilationPageProps {
  institutionId: string;
  activeExam: ExamItem | null;
}

const DEFAULT_RULES: InvigilationRules = {
  hard_avoid_own_class: true,
  hard_avoid_own_subject: false,
  hard_max_daily: true,
  hard_max_total: true,
  respect_locks: true,
  weight_load_deviation: 10,
  weight_own_class: 20,
  weight_own_subject: 15,
  weight_consecutive: 5,
};

function getErrMsg(err: unknown, fallback: string): string {
  return err instanceof Error ? err.message : fallback;
}

export function InvigilationPage({
  institutionId,
  activeExam,
}: InvigilationPageProps) {
  const { pushToast } = useToast();
  const [plans, setPlans] = useState<PlanItem[]>([]);
  const [activePlanId, setActivePlanId] = useState<string>("");
  const [detail, setDetail] = useState<InvigilationDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [solving, setSolving] = useState(false);
  const [solveReason, setSolveReason] = useState<string | null>(null);
  const [rules, setRules] = useState<InvigilationRules>(DEFAULT_RULES);
  const [activeTab, setActiveTab] = useState<"grid" | "workload" | "reserves">(
    "grid"
  );

  // Filters (SCH-06)
  const [filterDate, setFilterDate] = useState("");
  const [filterRoom, setFilterRoom] = useState("");
  const [filterPerson, setFilterPerson] = useState("");

  // Manual assign modal (SCH-06)
  const [editingSlot, setEditingSlot] = useState<InvigilationSlotItem | null>(
    null
  );
  const [assignPersonId, setAssignPersonId] = useState<string>("");
  const [assignLocked, setAssignLocked] = useState(false);

  // Staff profile & availability modals (SCH-01)
  const [editingProfile, setEditingProfile] = useState<SchStaffItem | null>(
    null
  );
  const [profMaxDaily, setProfMaxDaily] = useState<string>("");
  const [profMaxTotal, setProfMaxTotal] = useState<string>("");
  const [profWeightPct, setProfWeightPct] = useState<number>(100);
  const [showAvailModal, setShowAvailModal] = useState(false);
  const [availPersonId, setAvailPersonId] = useState("");
  const [availStart, setAvailStart] = useState("2026-12-01T00:00:00+00:00");
  const [availEnd, setAvailEnd] = useState("2026-12-01T03:00:00+00:00");
  const [availReason, setAvailReason] = useState("");

  // Reserve modal (SCH-08)
  const [showReserveModal, setShowReserveModal] = useState(false);
  const [resSessionId, setResSessionId] = useState("");
  const [resPersonId, setResPersonId] = useState("");

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
      pushToast(getErrMsg(err, "Gagal memuat daftar rencana."), "error");
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
        const data = await invokeBridge<InvigilationDetail>(
          "sch.invigilation.detail",
          {
            institution_id: institutionId,
            exam_id: activeExam.id,
            plan_id: planId,
          }
        );
        setDetail(data);
        if (data.staff.length > 0 && !availPersonId) {
          setAvailPersonId(data.staff[0].id);
          setResPersonId(data.staff[0].id);
        }
        if (data.slots.length > 0 && !resSessionId) {
          setResSessionId(data.slots[0].session_id);
        }
      } catch (err) {
        pushToast(getErrMsg(err, "Gagal memuat jadwal pengawas."), "error");
      } finally {
        setLoading(false);
      }
    },
    [institutionId, activeExam, pushToast, availPersonId, resSessionId]
  );

  useEffect(() => {
    void loadPlans();
  }, [loadPlans]);

  useEffect(() => {
    if (activePlanId) {
      void loadDetail(activePlanId);
      setSolveReason(null);
    }
  }, [activePlanId, loadDetail]);

  const isReadOnly =
    detail?.plan_state === "published" || detail?.plan_state === "superseded";

  const filteredSlots = useMemo(() => {
    const slots = detail?.slots ?? [];
    return slots.filter((s) => {
      if (filterDate && s.local_date !== filterDate) return false;
      if (filterRoom && s.room_code !== filterRoom) return false;
      if (filterPerson && s.exam_person_id !== filterPerson) return false;
      return true;
    });
  }, [detail, filterDate, filterRoom, filterPerson]);

  const distinctDates = useMemo(
    () => Array.from(new Set((detail?.slots ?? []).map((s) => s.local_date))),
    [detail]
  );
  const distinctRooms = useMemo(
    () => Array.from(new Set((detail?.slots ?? []).map((s) => s.room_code))),
    [detail]
  );
  const distinctSessions = useMemo(() => {
    const map = new Map<string, string>();
    for (const s of detail?.slots ?? []) {
      map.set(s.session_id, `${s.local_date} · ${s.session_label}`);
    }
    return Array.from(map.entries());
  }, [detail]);

  const handleSolve = async () => {
    if (!activeExam || !detail) return;
    setSolving(true);
    setSolveReason(null);
    try {
      const data = await invokeBridge<{
        ok: boolean;
        status: string;
        diagnostics?: { reason?: string };
      }>("sch.invigilation.solve", {
        institution_id: institutionId,
        exam_id: activeExam.id,
        plan_id: detail.plan_id,
        expected_revision: detail.plan_revision,
        rules,
      });
      if (!data.ok) {
        setSolveReason(
          data.diagnostics?.reason ??
            "Solver tidak menemukan penugasan pengawas yang memenuhi syarat."
        );
        pushToast("Alokasi pengawas tidak feasible.", "error");
        return;
      }
      pushToast(`Jadwal pengawas selesai (${data.status}).`, "success");
      await loadDetail(detail.plan_id);
    } catch (err) {
      pushToast(getErrMsg(err, "Gagal menjalankan solver pengawas."), "error");
    } finally {
      setSolving(false);
    }
  };

  const handleSaveSlotAssign = async () => {
    if (!activeExam || !detail || !editingSlot) return;
    try {
      await invokeBridge<{ plan_revision: number }>("sch.invigilation.assign", {
        institution_id: institutionId,
        exam_id: activeExam.id,
        plan_id: detail.plan_id,
        expected_revision: detail.plan_revision,
        slot_id: editingSlot.id,
        exam_person_id: assignPersonId || null,
        locked: assignLocked,
        rules,
      });
      setEditingSlot(null);
      pushToast("Penugasan slot pengawas diperbarui.", "success");
      await loadDetail(detail.plan_id);
    } catch (err) {
      pushToast(getErrMsg(err, "Gagal memperbarui penugasan slot."), "error");
    }
  };

  const handleSaveProfile = async () => {
    if (!activeExam || !editingProfile || !detail) return;
    try {
      await invokeBridge("sch.profiles.save", {
        institution_id: institutionId,
        exam_id: activeExam.id,
        exam_person_id: editingProfile.id,
        max_daily: profMaxDaily ? Number(profMaxDaily) : null,
        max_total: profMaxTotal ? Number(profMaxTotal) : null,
        target_weight_pct: profWeightPct,
        role_skills: editingProfile.role_skills,
      });
      setEditingProfile(null);
      pushToast("Profil beban pengawas disimpan.", "success");
      await loadDetail(detail.plan_id);
    } catch (err) {
      pushToast(getErrMsg(err, "Gagal menyimpan profil pengawas."), "error");
    }
  };

  const handleSaveAvailability = async () => {
    if (!activeExam || !detail || !availPersonId) return;
    try {
      await invokeBridge("sch.availability.save", {
        institution_id: institutionId,
        exam_id: activeExam.id,
        exam_person_id: availPersonId,
        starts_at: availStart,
        ends_at: availEnd,
        state: "unavailable",
        reason: availReason,
      });
      setShowAvailModal(false);
      pushToast("Ketidakhadiran pengawas ditambahkan.", "success");
      await loadDetail(detail.plan_id);
    } catch (err) {
      pushToast(getErrMsg(err, "Gagal menyimpan ketersediaan."), "error");
    }
  };

  const handleDeleteAvailability = async (id: string) => {
    if (!activeExam || !detail) return;
    try {
      await invokeBridge("sch.availability.delete", {
        institution_id: institutionId,
        exam_id: activeExam.id,
        availability_id: id,
      });
      pushToast("Data ketersediaan dihapus.", "info");
      await loadDetail(detail.plan_id);
    } catch (err) {
      pushToast(getErrMsg(err, "Gagal menghapus ketersediaan."), "error");
    }
  };

  const handleAssignReserve = async () => {
    if (!activeExam || !detail || !resSessionId || !resPersonId) return;
    try {
      await invokeBridge("sch.reserves.assign", {
        institution_id: institutionId,
        exam_id: activeExam.id,
        plan_id: detail.plan_id,
        expected_revision: detail.plan_revision,
        session_id: resSessionId,
        exam_person_id: resPersonId,
      });
      setShowReserveModal(false);
      pushToast("Pengawas cadangan ditambahkan.", "success");
      await loadDetail(detail.plan_id);
    } catch (err) {
      pushToast(getErrMsg(err, "Gagal menambah pengawas cadangan."), "error");
    }
  };

  const handleDeleteReserve = async (reserveId: string) => {
    if (!activeExam || !detail) return;
    try {
      await invokeBridge("sch.reserves.delete", {
        institution_id: institutionId,
        exam_id: activeExam.id,
        plan_id: detail.plan_id,
        expected_revision: detail.plan_revision,
        reserve_id: reserveId,
      });
      pushToast("Pengawas cadangan dihapus.", "info");
      await loadDetail(detail.plan_id);
    } catch (err) {
      pushToast(getErrMsg(err, "Gagal menghapus cadangan."), "error");
    }
  };

  const handlePublish = async () => {
    if (!activeExam || !detail) return;
    try {
      await invokeBridge("ses.plans.publish", {
        institution_id: institutionId,
        exam_id: activeExam.id,
        plan_id: detail.plan_id,
        expected_revision: detail.plan_revision,
      });
      pushToast("Jadwal & penugasan pengawas diterbitkan.", "success");
      await loadPlans();
      await loadDetail(detail.plan_id);
    } catch (err) {
      pushToast(getErrMsg(err, "Gagal menerbitkan rencana."), "error");
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
      {/* Top Toolbar */}
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
          <div style={{ display: "flex", gap: "var(--space-3)", alignItems: "center" }}>
            <label style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span className="uc-label">Versi Rencana</span>
              <select
                className="uc-input"
                aria-label="Pilih Versi Rencana"
                value={activePlanId}
                onChange={(e) => setActivePlanId(e.target.value)}
              >
                {plans.length === 0 ? (
                  <option value="">Belum ada draf rencana</option>
                ) : (
                  plans.map((p) => (
                    <option key={p.id} value={p.id}>
                      v{p.version} ({p.state}) · rev {p.revision}
                    </option>
                  ))
                )}
              </select>
            </label>
            {detail && (
              <StatusIndicator
                tone={
                  detail.plan_state === "published"
                    ? "success"
                    : detail.validation.valid
                      ? "neutral"
                      : "warning"
                }
                label={
                  detail.plan_state === "published"
                    ? "Terbit (Terkunci)"
                    : detail.validation.valid
                      ? "Valid"
                      : "Ada Konflik"
                }
              />
            )}
          </div>

          <div style={{ display: "flex", flexWrap: "wrap", gap: "var(--space-2)" }}>
            <Button
              variant="secondary"
              disabled={!detail || isReadOnly}
              onClick={() => setShowAvailModal(true)}
            >
              <UserX size={16} aria-hidden="true" />
              Ketidakhadiran
            </Button>
            <Button
              variant="primary"
              disabled={!detail || isReadOnly || solving}
              onClick={() => void handleSolve()}
            >
              <Sparkles size={16} aria-hidden="true" />
              {solving ? "Menjadwalkan..." : "Alokasi Pengawas"}
            </Button>
            {detail && detail.plan_state === "draft" && (
              <Button
                variant="secondary"
                disabled={!detail.validation.valid}
                onClick={() => void handlePublish()}
              >
                <CheckCircle2 size={16} aria-hidden="true" />
                Terbitkan
              </Button>
            )}
          </div>
        </div>
      </section>

      {!detail ? (
        <section className="uc-panel">
          <div className="uc-panel-body">
            <p className="uc-sub">
              {loading
                ? "Memuat jadwal pengawas..."
                : "Buat draf rencana terlebih dahulu di menu Jadwal Ujian."}
            </p>
          </div>
        </section>
      ) : (
        <>
          {/* Sub-navigation tabs */}
          <div style={{ display: "flex", gap: "var(--space-2)" }}>
            <Button
              variant={activeTab === "grid" ? "primary" : "secondary"}
              onClick={() => setActiveTab("grid")}
            >
              Jadwal Pengawas ({detail.validation.summary.assigned_slots}/
              {detail.validation.summary.total_slots})
            </Button>
            <Button
              variant={activeTab === "workload" ? "primary" : "secondary"}
              onClick={() => setActiveTab("workload")}
            >
              Beban Kerja &amp; Aturan
            </Button>
            <Button
              variant={activeTab === "reserves" ? "primary" : "secondary"}
              onClick={() => setActiveTab("reserves")}
            >
              Cadangan ({detail.reserves.length})
            </Button>
          </div>

          {solveReason && (
            <section className="uc-panel" role="alert">
              <div className="uc-panel-body uc-field-error">{solveReason}</div>
            </section>
          )}

          {detail.validation.hard_conflicts.length > 0 && (
            <section className="uc-panel" role="alert">
              <div className="uc-panel-body" style={{ display: "grid", gap: 4 }}>
                {detail.validation.hard_conflicts.map((hc, i) => (
                  <div key={`${hc.code}-${i}`} className="uc-field-error">
                    {hc.message}
                  </div>
                ))}
              </div>
            </section>
          )}

          {activeTab === "grid" && (
            <section className="uc-panel">
              <div className="uc-panel-header">
                <h2>Grid Penugasan Pengawas</h2>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                  <select
                    className="uc-input"
                    aria-label="Filter Tanggal"
                    value={filterDate}
                    onChange={(e) => setFilterDate(e.target.value)}
                  >
                    <option value="">Semua Tanggal</option>
                    {distinctDates.map((d) => (
                      <option key={d} value={d}>
                        {d}
                      </option>
                    ))}
                  </select>
                  <select
                    className="uc-input"
                    aria-label="Filter Ruang"
                    value={filterRoom}
                    onChange={(e) => setFilterRoom(e.target.value)}
                  >
                    <option value="">Semua Ruang</option>
                    {distinctRooms.map((r) => (
                      <option key={r} value={r}>
                        {r}
                      </option>
                    ))}
                  </select>
                  <select
                    className="uc-input"
                    aria-label="Filter Pengawas"
                    value={filterPerson}
                    onChange={(e) => setFilterPerson(e.target.value)}
                  >
                    <option value="">Semua Pengawas</option>
                    {detail.staff.map((st) => (
                      <option key={st.id} value={st.id}>
                        {st.display_name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="uc-panel-body" style={{ overflowX: "auto" }}>
                <table className="uc-table" aria-label="Grid Jadwal Pengawas">
                  <thead>
                    <tr>
                      <th>Tanggal &amp; Sesi</th>
                      <th>Ruang</th>
                      <th>Peran</th>
                      <th>Pengawas</th>
                      <th>Aksi</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredSlots.map((sl) => (
                      <tr key={sl.id}>
                        <td>
                          {sl.local_date} · {sl.session_label}
                        </td>
                        <td>{sl.room_code}</td>
                        <td>
                          {sl.role_code} #{sl.slot_index}
                        </td>
                        <td>
                          {sl.person_name ? (
                            <span>
                              {sl.person_name}{" "}
                              {sl.locked && (
                                <Lock
                                  size={12}
                                  aria-label="Terkunci"
                                  style={{ display: "inline" }}
                                />
                              )}
                            </span>
                          ) : (
                            <span className="uc-sub">Belum terisi</span>
                          )}
                        </td>
                        <td>
                          <Button
                            variant="secondary"
                            size="sm"
                            disabled={isReadOnly}
                            onClick={() => {
                              setEditingSlot(sl);
                              setAssignPersonId(sl.exam_person_id ?? "");
                              setAssignLocked(sl.locked);
                            }}
                          >
                            Ubah
                          </Button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}

          {activeTab === "workload" && (
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "minmax(260px, 320px) minmax(0, 1fr)",
                gap: "var(--space-4)",
                alignItems: "start",
              }}
            >
              <section className="uc-panel">
                <div className="uc-panel-header">
                  <h2>Aturan Penjadwalan</h2>
                </div>
                <div className="uc-panel-body" style={{ display: "grid", gap: 10 }}>
                  <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
                    <input
                      type="checkbox"
                      checked={rules.hard_avoid_own_class}
                      disabled={isReadOnly}
                      onChange={(e) =>
                        setRules((r) => ({
                          ...r,
                          hard_avoid_own_class: e.target.checked,
                        }))
                      }
                    />
                    <span>Larang awasi rombel sendiri (keras)</span>
                  </label>
                  <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
                    <input
                      type="checkbox"
                      checked={rules.hard_avoid_own_subject}
                      disabled={isReadOnly}
                      onChange={(e) =>
                        setRules((r) => ({
                          ...r,
                          hard_avoid_own_subject: e.target.checked,
                        }))
                      }
                    />
                    <span>Larang awasi mapel sendiri (keras)</span>
                  </label>
                  <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
                    <input
                      type="checkbox"
                      checked={rules.hard_max_daily}
                      disabled={isReadOnly}
                      onChange={(e) =>
                        setRules((r) => ({
                          ...r,
                          hard_max_daily: e.target.checked,
                        }))
                      }
                    />
                    <span>Batas maksimal harian (keras)</span>
                  </label>
                  <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
                    <input
                      type="checkbox"
                      checked={rules.hard_max_total}
                      disabled={isReadOnly}
                      onChange={(e) =>
                        setRules((r) => ({
                          ...r,
                          hard_max_total: e.target.checked,
                        }))
                      }
                    />
                    <span>Batas maksimal total (keras)</span>
                  </label>

                  <div style={{ marginTop: 8, fontSize: 13 }}>
                    Min beban: <strong>{detail.validation.summary.min_load}</strong> ·
                    Maks beban: <strong>{detail.validation.summary.max_load}</strong>
                  </div>
                </div>
              </section>

              <section className="uc-panel">
                <div className="uc-panel-header">
                  <h2>Rekap Beban Kerja Pengawas</h2>
                </div>
                <div className="uc-panel-body" style={{ overflowX: "auto" }}>
                  <table className="uc-table" aria-label="Beban Kerja Pengawas">
                    <thead>
                      <tr>
                        <th>Pengawas</th>
                        <th>Tugas Aktif</th>
                        <th>Cadangan</th>
                        <th>Bobot (%)</th>
                        <th>Deviasi</th>
                        <th>Aksi</th>
                      </tr>
                    </thead>
                    <tbody>
                      {detail.validation.workload.map((w) => {
                        const staffObj = detail.staff.find(
                          (st) => st.id === w.exam_person_id
                        );
                        return (
                          <tr key={w.exam_person_id}>
                            <td>
                              {w.code} · {w.display_name}
                            </td>
                            <td>
                              <strong>{w.active_count}</strong>
                            </td>
                            <td>{w.reserve_count}</td>
                            <td>{w.target_weight_pct}%</td>
                            <td>{w.deviation}</td>
                            <td>
                              <Button
                                variant="secondary"
                                size="sm"
                                disabled={!staffObj}
                                onClick={() => {
                                  if (!staffObj) return;
                                  setEditingProfile(staffObj);
                                  setProfMaxDaily(
                                    staffObj.max_daily?.toString() ?? ""
                                  );
                                  setProfMaxTotal(
                                    staffObj.max_total?.toString() ?? ""
                                  );
                                  setProfWeightPct(staffObj.target_weight_pct);
                                }}
                              >
                                Atur Target
                              </Button>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </section>
            </div>
          )}

          {activeTab === "reserves" && (
            <section className="uc-panel">
              <div className="uc-panel-header">
                <div>
                  <h2>Pengawas Cadangan (Stand-by)</h2>
                  <p className="uc-sub">
                    Cadangan tidak dihitung sebagai beban tugas aktif dan bebas
                    bentrok dengan jadwal aktif.
                  </p>
                </div>
                <Button
                  variant="primary"
                  size="sm"
                  disabled={isReadOnly || distinctSessions.length === 0}
                  onClick={() => setShowReserveModal(true)}
                >
                  <Plus size={14} aria-hidden="true" />
                  Tambah Cadangan
                </Button>
              </div>
              <div className="uc-panel-body" style={{ overflowX: "auto" }}>
                <table className="uc-table" aria-label="Daftar Pengawas Cadangan">
                  <thead>
                    <tr>
                      <th>Sesi</th>
                      <th>Pengawas Cadangan</th>
                      <th>Aksi</th>
                    </tr>
                  </thead>
                  <tbody>
                    {detail.reserves.map((rv) => (
                      <tr key={rv.id}>
                        <td>{rv.session_label}</td>
                        <td>
                          <UserCheck
                            size={14}
                            aria-hidden="true"
                            style={{ display: "inline", marginRight: 6 }}
                          />
                          {rv.person_name}
                        </td>
                        <td>
                          <Button
                            variant="secondary"
                            size="sm"
                            disabled={isReadOnly}
                            aria-label={`Hapus cadangan ${rv.person_name}`}
                            onClick={() => void handleDeleteReserve(rv.id)}
                          >
                            <Trash2 size={14} aria-hidden="true" />
                          </Button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}
        </>
      )}

      {/* Manual Replace & Lock Modal */}
      <CRUDModal
        open={editingSlot !== null}
        title={
          editingSlot
            ? `Ubah Pengawas ${editingSlot.room_code} (${editingSlot.session_label})`
            : "Ubah Pengawas"
        }
        onClose={() => setEditingSlot(null)}
        onSubmit={() => void handleSaveSlotAssign()}
      >
        <div style={{ display: "grid", gap: 12 }}>
          <label className="uc-field">
            <span className="uc-label">Pilih Pengawas</span>
            <select
              className="uc-input"
              value={assignPersonId}
              onChange={(e) => setAssignPersonId(e.target.value)}
            >
              <option value="">-- Kosongkan Slot --</option>
              {(detail?.staff ?? []).map((st) => (
                <option key={st.id} value={st.id}>
                  {st.code} · {st.display_name}
                </option>
              ))}
            </select>
          </label>
          <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <input
              type="checkbox"
              checked={assignLocked}
              onChange={(e) => setAssignLocked(e.target.checked)}
            />
            <span>Kunci penugasan ini saat alokasi ulang</span>
          </label>
        </div>
      </CRUDModal>

      {/* Staff Profile Modal */}
      <CRUDModal
        open={editingProfile !== null}
        title={`Target & Batas · ${editingProfile?.display_name ?? ""}`}
        onClose={() => setEditingProfile(null)}
        onSubmit={() => void handleSaveProfile()}
      >
        <div style={{ display: "grid", gap: 12 }}>
          <label className="uc-field">
            <span className="uc-label">Maksimal Harian (opsional)</span>
            <input
              type="number"
              min={1}
              className="uc-input"
              value={profMaxDaily}
              onChange={(e) => setProfMaxDaily(e.target.value)}
            />
          </label>
          <label className="uc-field">
            <span className="uc-label">Maksimal Total (opsional)</span>
            <input
              type="number"
              min={1}
              className="uc-input"
              value={profMaxTotal}
              onChange={(e) => setProfMaxTotal(e.target.value)}
            />
          </label>
          <label className="uc-field">
            <span className="uc-label">Bobot Target (%) · 50 = paruh waktu</span>
            <input
              type="number"
              min={10}
              max={200}
              className="uc-input"
              value={profWeightPct}
              onChange={(e) => setProfWeightPct(Number(e.target.value))}
            />
          </label>
        </div>
      </CRUDModal>

      {/* Availability Modal */}
      <CRUDModal
        open={showAvailModal}
        title="Catat Ketidakhadiran Pengawas"
        onClose={() => setShowAvailModal(false)}
        onSubmit={() => void handleSaveAvailability()}
      >
        <div style={{ display: "grid", gap: 12 }}>
          <label className="uc-field">
            <span className="uc-label">Pengawas</span>
            <select
              className="uc-input"
              value={availPersonId}
              onChange={(e) => setAvailPersonId(e.target.value)}
            >
              {(detail?.staff ?? []).map((st) => (
                <option key={st.id} value={st.id}>
                  {st.display_name}
                </option>
              ))}
            </select>
          </label>
          <label className="uc-field">
            <span className="uc-label">Mulai (ISO UTC)</span>
            <input
              type="text"
              className="uc-input"
              value={availStart}
              onChange={(e) => setAvailStart(e.target.value)}
            />
          </label>
          <label className="uc-field">
            <span className="uc-label">Selesai (ISO UTC)</span>
            <input
              type="text"
              className="uc-input"
              value={availEnd}
              onChange={(e) => setAvailEnd(e.target.value)}
            />
          </label>
          <label className="uc-field">
            <span className="uc-label">Alasan</span>
            <input
              type="text"
              className="uc-input"
              value={availReason}
              onChange={(e) => setAvailReason(e.target.value)}
            />
          </label>

          {(detail?.availability ?? []).length > 0 && (
            <div style={{ display: "grid", gap: 6, marginTop: 6 }}>
              <span className="uc-label">Daftar Tercatat</span>
              {detail?.availability.map((av) => {
                const st = detail.staff.find((s) => s.id === av.exam_person_id);
                return (
                  <div
                    key={av.id}
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      fontSize: 12,
                    }}
                  >
                    <span>
                      {st?.display_name ?? av.exam_person_id}: {av.starts_at} –{" "}
                      {av.ends_at} ({av.reason || "-"})
                    </span>
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => void handleDeleteAvailability(av.id)}
                    >
                      Hapus
                    </Button>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </CRUDModal>

      {/* Reserve Modal */}
      <CRUDModal
        open={showReserveModal}
        title="Tambah Pengawas Cadangan"
        onClose={() => setShowReserveModal(false)}
        onSubmit={() => void handleAssignReserve()}
      >
        <div style={{ display: "grid", gap: 12 }}>
          <label className="uc-field">
            <span className="uc-label">Sesi</span>
            <select
              className="uc-input"
              value={resSessionId}
              onChange={(e) => setResSessionId(e.target.value)}
            >
              {distinctSessions.map(([id, label]) => (
                <option key={id} value={id}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          <label className="uc-field">
            <span className="uc-label">Pengawas</span>
            <select
              className="uc-input"
              value={resPersonId}
              onChange={(e) => setResPersonId(e.target.value)}
            >
              {(detail?.staff ?? []).map((st) => (
                <option key={st.id} value={st.id}>
                  {st.display_name}
                </option>
              ))}
            </select>
          </label>
        </div>
      </CRUDModal>
    </div>
  );
}
