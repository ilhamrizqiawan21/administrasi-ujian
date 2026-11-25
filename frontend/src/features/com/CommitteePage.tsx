import { useCallback, useEffect, useState } from "react";
import { Plus, Trash2, UserPlus } from "lucide-react";
import { Button } from "../../components/ui/Button";
import { StatusIndicator, useToast } from "../../components/ui/Feedback";
import { CRUDModal } from "../../components/ui/Modal";
import { invokeBridge } from "../../lib/bridge";
import type { ExamItem } from "../evt/types";
import type { CommitteeDetail, OrgTreeNode } from "./types";

interface CommitteePageProps {
  institutionId: string;
  activeExam: ExamItem | null;
}

function getErrMsg(err: unknown, fallback: string): string {
  return err instanceof Error ? err.message : fallback;
}

function OrgNodeView({ node, depth = 0 }: { node: OrgTreeNode; depth?: number }) {
  return (
    <div
      style={{
        marginLeft: depth * 18,
        paddingLeft: 12,
        borderLeft: depth > 0 ? "2px solid var(--border-subtle)" : "none",
        display: "grid",
        gap: 6,
      }}
    >
      <div
        style={{
          padding: 10,
          borderRadius: 6,
          border: "1px solid var(--border-subtle)",
          background: "var(--bg-elevated)",
        }}
      >
        <div style={{ fontWeight: 600, wordBreak: "break-word" }}>
          {node.name}
        </div>
        {node.jobdesc && (
          <div className="uc-sub" style={{ fontSize: 12 }}>
            {node.jobdesc}
          </div>
        )}
        <div style={{ fontSize: 12, marginTop: 4 }}>
          {node.members.length > 0
            ? node.members.map((m) => m.person_name).join(", ")
            : "Belum ada anggota"}
        </div>
      </div>
      {node.children.map((ch) => (
        <OrgNodeView key={ch.id} node={ch} depth={depth + 1} />
      ))}
    </div>
  );
}

export function CommitteePage({
  institutionId,
  activeExam,
}: CommitteePageProps) {
  const { pushToast } = useToast();
  const [detail, setDetail] = useState<CommitteeDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [tab, setTab] = useState<
    "roles" | "program" | "meetings" | "signatories"
  >("roles");

  // Role modal
  const [showRoleModal, setShowRoleModal] = useState(false);
  const [roleName, setRoleName] = useState("");
  const [roleParentId, setRoleParentId] = useState("");
  const [roleJobdesc, setRoleJobdesc] = useState("");

  // Member modal
  const [showMemberModal, setShowMemberModal] = useState(false);
  const [memberRoleId, setMemberRoleId] = useState("");
  const [memberPersonId, setMemberPersonId] = useState("");

  // Program kerja state
  const [basisText, setBasisText] = useState("");
  const [objectivesText, setObjectivesText] = useState("");

  // Meeting modal
  const [showMeetingModal, setShowMeetingModal] = useState(false);
  const [meetingTitle, setMeetingTitle] = useState("");
  const [meetingDate, setMeetingDate] = useState("2026-12-01");
  const [meetingStart, setMeetingStart] = useState("08:00");
  const [meetingEnd, setMeetingEnd] = useState("10:00");
  const [meetingAgenda, setMeetingAgenda] = useState("");

  // Signatory modal
  const [showSigModal, setShowSigModal] = useState(false);
  const [sigRoleKey, setSigRoleKey] = useState("headmaster");
  const [sigRoleLabel, setSigRoleLabel] = useState("Kepala Sekolah");
  const [sigName, setSigName] = useState("");
  const [sigTitle, setSigTitle] = useState("");
  const [sigNip, setSigNip] = useState("");

  const loadDetail = useCallback(async () => {
    if (!activeExam) {
      setDetail(null);
      return;
    }
    setLoading(true);
    try {
      const data = await invokeBridge<CommitteeDetail>("com.detail", {
        institution_id: institutionId,
        exam_id: activeExam.id,
      });
      setDetail(data);
      setBasisText(data.program_kerja.basis_text);
      setObjectivesText(data.program_kerja.objectives.join("\n"));
      if (data.roles.length > 0 && !memberRoleId) {
        setMemberRoleId(data.roles[0].id);
      }
      if (data.staff.length > 0 && !memberPersonId) {
        setMemberPersonId(data.staff[0].id);
      }
    } catch (err) {
      pushToast(getErrMsg(err, "Gagal memuat data kepanitiaan."), "error");
    } finally {
      setLoading(false);
    }
  }, [institutionId, activeExam, pushToast, memberRoleId, memberPersonId]);

  useEffect(() => {
    void loadDetail();
  }, [loadDetail]);

  const handleSaveRole = async () => {
    if (!activeExam || !roleName.trim()) return;
    try {
      await invokeBridge("com.roles.save", {
        institution_id: institutionId,
        exam_id: activeExam.id,
        name: roleName.trim(),
        parent_id: roleParentId || null,
        jobdesc: roleJobdesc,
      });
      setShowRoleModal(false);
      setRoleName("");
      setRoleJobdesc("");
      pushToast("Peran panitia ditambahkan.", "success");
      await loadDetail();
    } catch (err) {
      pushToast(getErrMsg(err, "Gagal menyimpan peran."), "error");
    }
  };

  const handleAssignMember = async () => {
    if (!activeExam || !memberRoleId || !memberPersonId) return;
    try {
      await invokeBridge("com.members.assign", {
        institution_id: institutionId,
        exam_id: activeExam.id,
        role_id: memberRoleId,
        exam_person_id: memberPersonId,
      });
      setShowMemberModal(false);
      pushToast("Anggota panitia ditambahkan.", "success");
      await loadDetail();
    } catch (err) {
      pushToast(getErrMsg(err, "Gagal menugaskan anggota."), "error");
    }
  };

  const handleRemoveMember = async (memberId: string) => {
    if (!activeExam) return;
    try {
      await invokeBridge("com.members.remove", {
        institution_id: institutionId,
        exam_id: activeExam.id,
        member_id: memberId,
      });
      pushToast("Anggota dihapus.", "info");
      await loadDetail();
    } catch (err) {
      pushToast(getErrMsg(err, "Gagal menghapus anggota."), "error");
    }
  };

  const handleSaveProgram = async () => {
    if (!activeExam) return;
    try {
      await invokeBridge("com.program.save", {
        institution_id: institutionId,
        exam_id: activeExam.id,
        basis_text: basisText,
        objectives: objectivesText
          .split("\n")
          .map((s) => s.trim())
          .filter(Boolean),
        milestones: detail?.program_kerja.milestones ?? [],
        sections: detail?.program_kerja.sections ?? [],
      });
      pushToast("Program kerja disimpan.", "success");
      await loadDetail();
    } catch (err) {
      pushToast(getErrMsg(err, "Gagal menyimpan program kerja."), "error");
    }
  };

  const handleSaveMeeting = async () => {
    if (!activeExam || !meetingTitle.trim()) return;
    try {
      await invokeBridge("com.meetings.save", {
        institution_id: institutionId,
        exam_id: activeExam.id,
        title: meetingTitle.trim(),
        meeting_date: meetingDate,
        start_time: meetingStart,
        end_time: meetingEnd,
        agenda: meetingAgenda,
      });
      setShowMeetingModal(false);
      setMeetingTitle("");
      setMeetingAgenda("");
      pushToast("Catatan rapat disimpan.", "success");
      await loadDetail();
    } catch (err) {
      pushToast(getErrMsg(err, "Gagal menyimpan rapat."), "error");
    }
  };

  const handleSaveSignatory = async () => {
    if (!activeExam) return;
    try {
      await invokeBridge("com.signatories.save", {
        institution_id: institutionId,
        exam_id: activeExam.id,
        role_key: sigRoleKey,
        role_label: sigRoleLabel,
        signer_name: sigName,
        signer_title: sigTitle,
        signer_nip: sigNip,
        required: true,
      });
      setShowSigModal(false);
      pushToast("Penanda tangan disimpan.", "success");
      await loadDetail();
    } catch (err) {
      pushToast(getErrMsg(err, "Gagal menyimpan penanda tangan."), "error");
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
      <div style={{ display: "flex", flexWrap: "wrap", gap: "var(--space-2)" }}>
        <Button
          variant={tab === "roles" ? "primary" : "secondary"}
          onClick={() => setTab("roles")}
        >
          Struktur &amp; Anggota
        </Button>
        <Button
          variant={tab === "program" ? "primary" : "secondary"}
          onClick={() => setTab("program")}
        >
          Program Kerja
        </Button>
        <Button
          variant={tab === "meetings" ? "primary" : "secondary"}
          onClick={() => setTab("meetings")}
        >
          Rapat &amp; Notulen ({detail?.meetings.length ?? 0})
        </Button>
        <Button
          variant={tab === "signatories" ? "primary" : "secondary"}
          onClick={() => setTab("signatories")}
        >
          Penanda Tangan ({detail?.signatories.length ?? 0})
        </Button>
      </div>

      {!detail ? (
        <section className="uc-panel">
          <div className="uc-panel-body">
            <p className="uc-sub">
              {loading ? "Memuat data kepanitiaan..." : "Tidak ada data."}
            </p>
          </div>
        </section>
      ) : (
        <>
          {tab === "roles" && (
            <div style={{ display: "grid", gap: "var(--space-4)" }}>
              <section className="uc-panel">
                <div className="uc-panel-header">
                  <h2>Bagan Struktur Panitia</h2>
                  <div style={{ display: "flex", gap: 8 }}>
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => setShowRoleModal(true)}
                    >
                      <Plus size={14} aria-hidden="true" />
                      Tambah Peran
                    </Button>
                    <Button
                      variant="primary"
                      size="sm"
                      disabled={detail.roles.length === 0 || detail.staff.length === 0}
                      onClick={() => setShowMemberModal(true)}
                    >
                      <UserPlus size={14} aria-hidden="true" />
                      Tugaskan Anggota
                    </Button>
                  </div>
                </div>
                <div className="uc-panel-body" style={{ display: "grid", gap: 10 }}>
                  {detail.org_tree.length === 0 ? (
                    <p className="uc-sub">Belum ada peran panitia.</p>
                  ) : (
                    detail.org_tree.map((node) => (
                      <OrgNodeView key={node.id} node={node} />
                    ))
                  )}
                </div>
              </section>

              <section className="uc-panel">
                <div className="uc-panel-header">
                  <h2>Daftar Penugasan Anggota</h2>
                </div>
                <div className="uc-panel-body" style={{ overflowX: "auto" }}>
                  <table className="uc-table" aria-label="Anggota Panitia">
                    <thead>
                      <tr>
                        <th>Personel</th>
                        <th>Peran</th>
                        <th>Aksi</th>
                      </tr>
                    </thead>
                    <tbody>
                      {detail.members.map((m) => {
                        const role = detail.roles.find((r) => r.id === m.role_id);
                        return (
                          <tr key={m.id}>
                            <td>
                              {m.person_code} · {m.person_name}
                            </td>
                            <td>{role?.name ?? "-"}</td>
                            <td>
                              <Button
                                variant="secondary"
                                size="sm"
                                aria-label={`Hapus ${m.person_name}`}
                                onClick={() => void handleRemoveMember(m.id)}
                              >
                                <Trash2 size={14} aria-hidden="true" />
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

          {tab === "program" && (
            <section className="uc-panel">
              <div className="uc-panel-header">
                <h2>Program Kerja Panitia</h2>
                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => void handleSaveProgram()}
                >
                  Simpan Program Kerja
                </Button>
              </div>
              <div className="uc-panel-body" style={{ display: "grid", gap: 12 }}>
                <label className="uc-field">
                  <span className="uc-label">
                    Dasar Pelaksanaan (diisi sesuai dokumen resmi lembaga)
                  </span>
                  <textarea
                    rows={3}
                    className="uc-input"
                    value={basisText}
                    onChange={(e) => setBasisText(e.target.value)}
                  />
                </label>
                <label className="uc-field">
                  <span className="uc-label">Tujuan (satu per baris)</span>
                  <textarea
                    rows={4}
                    className="uc-input"
                    value={objectivesText}
                    onChange={(e) => setObjectivesText(e.target.value)}
                  />
                </label>
              </div>
            </section>
          )}

          {tab === "meetings" && (
            <section className="uc-panel">
              <div className="uc-panel-header">
                <h2>Rapat &amp; Notulen</h2>
                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => setShowMeetingModal(true)}
                >
                  <Plus size={14} aria-hidden="true" />
                  Tambah Rapat
                </Button>
              </div>
              <div className="uc-panel-body" style={{ overflowX: "auto" }}>
                <table className="uc-table" aria-label="Daftar Rapat Panitia">
                  <thead>
                    <tr>
                      <th>Judul Rapat</th>
                      <th>Tanggal &amp; Jam</th>
                      <th>Agenda</th>
                      <th>Kehadiran</th>
                    </tr>
                  </thead>
                  <tbody>
                    {detail.meetings.map((mt) => (
                      <tr key={mt.id}>
                        <td>{mt.title}</td>
                        <td>
                          {mt.meeting_date} ({mt.start_time}–{mt.end_time})
                        </td>
                        <td>{mt.agenda || "-"}</td>
                        <td>{mt.attendance.length} dicatat</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}

          {tab === "signatories" && (
            <section className="uc-panel">
              <div className="uc-panel-header">
                <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
                  <h2>Penanda Tangan Dokumen</h2>
                  <StatusIndicator
                    tone={detail.signatory_validation.valid ? "success" : "warning"}
                    label={
                      detail.signatory_validation.valid
                        ? "Lengkap"
                        : "Belum Lengkap"
                    }
                  />
                </div>
                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => setShowSigModal(true)}
                >
                  <Plus size={14} aria-hidden="true" />
                  Atur Penanda Tangan
                </Button>
              </div>
              <div className="uc-panel-body" style={{ overflowX: "auto" }}>
                <table className="uc-table" aria-label="Daftar Penanda Tangan">
                  <thead>
                    <tr>
                      <th>Peran</th>
                      <th>Nama</th>
                      <th>Jabatan</th>
                      <th>Wajib</th>
                    </tr>
                  </thead>
                  <tbody>
                    {detail.signatories.map((s) => (
                      <tr key={s.id}>
                        <td>{s.role_label}</td>
                        <td>{s.signer_name || "-"}</td>
                        <td>{s.signer_title || "-"}</td>
                        <td>{s.required ? "Ya" : "Opsional"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}
        </>
      )}

      {/* Role Modal */}
      <CRUDModal
        open={showRoleModal}
        title="Tambah Peran Panitia"
        onClose={() => setShowRoleModal(false)}
        onSubmit={() => void handleSaveRole()}
      >
        <div style={{ display: "grid", gap: 12 }}>
          <label className="uc-field">
            <span className="uc-label">Nama Peran</span>
            <input
              type="text"
              className="uc-input"
              value={roleName}
              onChange={(e) => setRoleName(e.target.value)}
            />
          </label>
          <label className="uc-field">
            <span className="uc-label">Induk Peran (opsional)</span>
            <select
              className="uc-input"
              value={roleParentId}
              onChange={(e) => setRoleParentId(e.target.value)}
            >
              <option value="">-- Tingkat Puncak --</option>
              {(detail?.roles ?? []).map((r) => (
                <option key={r.id} value={r.id}>
                  {r.name}
                </option>
              ))}
            </select>
          </label>
          <label className="uc-field">
            <span className="uc-label">Uraian Tugas</span>
            <textarea
              rows={2}
              className="uc-input"
              value={roleJobdesc}
              onChange={(e) => setRoleJobdesc(e.target.value)}
            />
          </label>
        </div>
      </CRUDModal>

      {/* Member Modal */}
      <CRUDModal
        open={showMemberModal}
        title="Tugaskan Anggota Panitia"
        onClose={() => setShowMemberModal(false)}
        onSubmit={() => void handleAssignMember()}
      >
        <div style={{ display: "grid", gap: 12 }}>
          <label className="uc-field">
            <span className="uc-label">Peran</span>
            <select
              className="uc-input"
              value={memberRoleId}
              onChange={(e) => setMemberRoleId(e.target.value)}
            >
              {(detail?.roles ?? []).map((r) => (
                <option key={r.id} value={r.id}>
                  {r.name}
                </option>
              ))}
            </select>
          </label>
          <label className="uc-field">
            <span className="uc-label">Personel</span>
            <select
              className="uc-input"
              value={memberPersonId}
              onChange={(e) => setMemberPersonId(e.target.value)}
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

      {/* Meeting Modal */}
      <CRUDModal
        open={showMeetingModal}
        title="Catat Rapat Panitia"
        onClose={() => setShowMeetingModal(false)}
        onSubmit={() => void handleSaveMeeting()}
      >
        <div style={{ display: "grid", gap: 12 }}>
          <label className="uc-field">
            <span className="uc-label">Judul Rapat</span>
            <input
              type="text"
              className="uc-input"
              value={meetingTitle}
              onChange={(e) => setMeetingTitle(e.target.value)}
            />
          </label>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8 }}>
            <label className="uc-field">
              <span className="uc-label">Tanggal</span>
              <input
                type="date"
                className="uc-input"
                value={meetingDate}
                onChange={(e) => setMeetingDate(e.target.value)}
              />
            </label>
            <label className="uc-field">
              <span className="uc-label">Mulai</span>
              <input
                type="time"
                className="uc-input"
                value={meetingStart}
                onChange={(e) => setMeetingStart(e.target.value)}
              />
            </label>
            <label className="uc-field">
              <span className="uc-label">Selesai</span>
              <input
                type="time"
                className="uc-input"
                value={meetingEnd}
                onChange={(e) => setMeetingEnd(e.target.value)}
              />
            </label>
          </div>
          <label className="uc-field">
            <span className="uc-label">Agenda</span>
            <textarea
              rows={2}
              className="uc-input"
              value={meetingAgenda}
              onChange={(e) => setMeetingAgenda(e.target.value)}
            />
          </label>
        </div>
      </CRUDModal>

      {/* Signatory Modal */}
      <CRUDModal
        open={showSigModal}
        title="Atur Penanda Tangan"
        onClose={() => setShowSigModal(false)}
        onSubmit={() => void handleSaveSignatory()}
      >
        <div style={{ display: "grid", gap: 12 }}>
          <label className="uc-field">
            <span className="uc-label">Kunci Peran</span>
            <input
              type="text"
              className="uc-input"
              value={sigRoleKey}
              onChange={(e) => setSigRoleKey(e.target.value)}
            />
          </label>
          <label className="uc-field">
            <span className="uc-label">Label Peran</span>
            <input
              type="text"
              className="uc-input"
              value={sigRoleLabel}
              onChange={(e) => setSigRoleLabel(e.target.value)}
            />
          </label>
          <label className="uc-field">
            <span className="uc-label">Nama Penanda Tangan</span>
            <input
              type="text"
              className="uc-input"
              value={sigName}
              onChange={(e) => setSigName(e.target.value)}
            />
          </label>
          <label className="uc-field">
            <span className="uc-label">Jabatan</span>
            <input
              type="text"
              className="uc-input"
              value={sigTitle}
              onChange={(e) => setSigTitle(e.target.value)}
            />
          </label>
          <label className="uc-field">
            <span className="uc-label">NIP / Kode (opsional)</span>
            <input
              type="text"
              className="uc-input"
              value={sigNip}
              onChange={(e) => setSigNip(e.target.value)}
            />
          </label>
        </div>
      </CRUDModal>
    </div>
  );
}
