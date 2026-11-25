import { useCallback, useEffect, useState } from "react";
import { CheckCircle2, FileDown, FileText, Paperclip, Plus, Save } from "lucide-react";
import { Button } from "../../components/ui/Button";
import { StatusIndicator, useToast } from "../../components/ui/Feedback";
import { CRUDModal } from "../../components/ui/Modal";
import { invokeBridge } from "../../lib/bridge";
import type { ExamItem } from "../evt/types";
import type { LpjDetail } from "./types";

interface LpjPageProps {
  institutionId: string;
  activeExam: ExamItem | null;
}

function getErrMsg(err: unknown, fallback: string): string {
  return err instanceof Error ? err.message : fallback;
}

function fmtIdr(val: number): string {
  return `Rp ${val.toLocaleString("id-ID")}`;
}

export function LpjPage({ institutionId, activeExam }: LpjPageProps) {
  const { pushToast } = useToast();
  const [detail, setDetail] = useState<LpjDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [tab, setTab] = useState<"sections" | "evaluation" | "attachments">("sections");
  const [selectedVersionId, setSelectedVersionId] = useState<string>("");
  const [selectedSectionKey, setSelectedSectionKey] = useState<string>("intro");
  const [narrativeDraft, setNarrativeDraft] = useState<string>("");

  // Evaluation modal
  const [showEvalModal, setShowEvalModal] = useState(false);
  const [evalIssue, setEvalIssue] = useState("");
  const [evalRes, setEvalRes] = useState("");
  const [evalRec, setEvalRec] = useState("");
  const [evalPic, setEvalPic] = useState("");
  const [evalIncidentId, setEvalIncidentId] = useState("");

  // Attachment modal
  const [showAttModal, setShowAttModal] = useState(false);
  const [attTitle, setAttTitle] = useState("");
  const [attDocRunId, setAttDocRunId] = useState("");
  const [attPath, setAttPath] = useState("");
  const [attIncluded, setAttIncluded] = useState(true);
  const [attExclusion, setAttExclusion] = useState("");

  const load = useCallback(
    async (verId?: string) => {
      if (!activeExam) return;
      setLoading(true);
      try {
        const res = await invokeBridge<LpjDetail>("lpj.detail", {
          institution_id: institutionId,
          exam_id: activeExam.id,
          lpj_version_id: verId || selectedVersionId || null,
        });
        setDetail(res);
        setSelectedVersionId(res.active_version.id);
        const sec =
          res.sections.find((s) => s.key === selectedSectionKey) ?? res.sections[0];
        if (sec) {
          setSelectedSectionKey(sec.key);
          setNarrativeDraft(sec.narrative);
        }
      } catch (err) {
        pushToast(getErrMsg(err, "Gagal memuat data LPJ."), "error");
      } finally {
        setLoading(false);
      }
    },
    [institutionId, activeExam, selectedVersionId, selectedSectionKey, pushToast],
  );

  useEffect(() => {
    void load();
  }, [activeExam?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!activeExam) {
    return (
      <div className="rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-surface)] p-6 text-sm text-[var(--color-text-muted)]">
        Pilih kegiatan ujian aktif terlebih dahulu untuk menyusun LPJ.
      </div>
    );
  }

  const activeVer = detail?.active_version;
  const totals = detail?.snapshot.derived_totals;
  const checks = detail?.snapshot.policy_checks;

  const handleSelectSection = (key: string) => {
    setSelectedSectionKey(key);
    const sec = detail?.sections.find((s) => s.key === key);
    setNarrativeDraft(sec?.narrative ?? "");
  };

  const handleSaveSection = async () => {
    if (!activeVer) return;
    try {
      const updated = await invokeBridge<LpjDetail>("lpj.sections.save", {
        institution_id: institutionId,
        exam_id: activeExam.id,
        lpj_version_id: activeVer.id,
        section_key: selectedSectionKey,
        narrative: narrativeDraft,
      });
      setDetail(updated);
      setSelectedVersionId(updated.active_version.id);
      pushToast(
        updated.active_version.id !== activeVer.id
          ? `Revisi baru v${updated.active_version.version} dibuat dan narasi disimpan.`
          : "Narasi bagian LPJ disimpan.",
        "success",
      );
    } catch (err) {
      pushToast(getErrMsg(err, "Gagal menyimpan narasi LPJ."), "error");
    }
  };

  const handleSaveEval = async () => {
    if (!activeVer) return;
    try {
      const updated = await invokeBridge<LpjDetail>("lpj.evaluations.save", {
        institution_id: institutionId,
        exam_id: activeExam.id,
        lpj_version_id: activeVer.id,
        incident_id: evalIncidentId || null,
        issue_title: evalIssue,
        resolution: evalRes,
        recommendation: evalRec,
        pic_name: evalPic,
        notes: "",
        sort_order: (detail?.evaluations.length ?? 0) + 1,
      });
      setDetail(updated);
      setSelectedVersionId(updated.active_version.id);
      setShowEvalModal(false);
      setEvalIssue("");
      setEvalRes("");
      setEvalRec("");
      setEvalPic("");
      pushToast("Evaluasi ditambahkan ke LPJ.", "success");
    } catch (err) {
      pushToast(getErrMsg(err, "Gagal menyimpan evaluasi."), "error");
    }
  };

  const handleSaveAttachment = async () => {
    if (!activeVer) return;
    try {
      const updated = await invokeBridge<LpjDetail>("lpj.attachments.save", {
        institution_id: institutionId,
        exam_id: activeExam.id,
        lpj_version_id: activeVer.id,
        doc_run_id: attDocRunId || null,
        title: attTitle,
        file_path: attPath,
        included: attIncluded,
        exclusion_reason: attIncluded ? "" : attExclusion,
        sort_order: (detail?.attachments.length ?? 0) + 1,
      });
      setDetail(updated);
      setSelectedVersionId(updated.active_version.id);
      setShowAttModal(false);
      setAttTitle("");
      setAttDocRunId("");
      setAttPath("");
      setAttIncluded(true);
      setAttExclusion("");
      pushToast("Lampiran LPJ diperbarui.", "success");
    } catch (err) {
      pushToast(getErrMsg(err, "Gagal menyimpan lampiran."), "error");
    }
  };

  const handleFinalize = async () => {
    if (!activeVer) return;
    try {
      const updated = await invokeBridge<LpjDetail>("lpj.finalize", {
        institution_id: institutionId,
        exam_id: activeExam.id,
        lpj_version_id: activeVer.id,
      });
      setDetail(updated);
      pushToast(`LPJ v${updated.active_version.version} berhasil difinalisasi.`, "success");
    } catch (err) {
      pushToast(getErrMsg(err, "Finalisasi LPJ ditolak."), "error");
    }
  };

  const handleExport = async (format: "pdf" | "docx") => {
    if (!activeVer) return;
    try {
      const res = await invokeBridge<{ output_path: string; version: number }>(
        "lpj.export",
        {
          institution_id: institutionId,
          exam_id: activeExam.id,
          lpj_version_id: activeVer.id,
          format,
          paper_size: "A4",
        },
      );
      pushToast(
        `Ekspor LPJ v${res.version} (${format.toUpperCase()}) tersimpan di ${res.output_path}.`,
        "success",
      );
      void load(activeVer.id);
    } catch (err) {
      pushToast(getErrMsg(err, "Gagal mengekspor LPJ."), "error");
    }
  };

  return (
    <div className="space-y-4">
      {/* Header & Version Controls */}
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
        <div>
          <h2 className="text-base font-semibold text-[var(--color-text)]">
            LPJ Kegiatan: {activeExam.title}
          </h2>
          <p className="text-xs text-[var(--color-text-muted)]">
            Susun narasi terstruktur tanpa mengubah angka turunan resmi, kelola evaluasi &amp; lampiran, lalu finalisasi.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {detail && (
            <select
              aria-label="Pilih Versi LPJ"
              value={activeVer?.id ?? ""}
              onChange={(e) => void load(e.target.value)}
              className="h-9 rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-surface)] px-2 text-xs text-[var(--color-text)]"
            >
              {detail.versions.map((v) => (
                <option key={v.id} value={v.id}>
                  v{v.version} ({v.state.toUpperCase()})
                </option>
              ))}
            </select>
          )}
          {activeVer && (
            <StatusIndicator
              tone={activeVer.state === "final" ? "success" : "warning"}
              label={activeVer.state === "final" ? "FINAL" : "DRAFT"}
            />
          )}
          {activeVer?.state === "draft" && (
            <Button size="sm" onClick={() => void handleFinalize()}>
              <CheckCircle2 size={14} className="mr-1" aria-hidden="true" />
              Finalisasi LPJ
            </Button>
          )}
          <Button size="sm" variant="secondary" onClick={() => void handleExport("pdf")}>
            <FileDown size={14} className="mr-1" aria-hidden="true" />
            Ekspor PDF
          </Button>
          <Button size="sm" variant="secondary" onClick={() => void handleExport("docx")}>
            <FileText size={14} className="mr-1" aria-hidden="true" />
            Ekspor DOCX
          </Button>
        </div>
      </div>

      {/* Derived Totals (Read-Only) */}
      {totals && (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <div className="rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-surface)] p-3">
            <div className="text-xs text-[var(--color-text-muted)]">Peserta Eligible / Hadir</div>
            <div className="mt-1 text-sm font-semibold text-[var(--color-text)]">
              {totals.participants_eligible} / {totals.participant_present}
            </div>
          </div>
          <div className="rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-surface)] p-3">
            <div className="text-xs text-[var(--color-text-muted)]">RAB Disetujui</div>
            <div className="mt-1 text-sm font-semibold text-[var(--color-text)]">
              {fmtIdr(totals.rab_approved_idr)}
            </div>
          </div>
          <div className="rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-surface)] p-3">
            <div className="text-xs text-[var(--color-text-muted)]">Saldo Akhir Kas</div>
            <div className="mt-1 text-sm font-semibold text-[var(--color-text)]">
              {fmtIdr(totals.ledger_closing_balance_idr)}
            </div>
          </div>
          <div className="rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-surface)] p-3">
            <div className="text-xs text-[var(--color-text-muted)]">Total Honor / Insiden</div>
            <div className="mt-1 text-sm font-semibold text-[var(--color-text)]">
              {fmtIdr(totals.honor_total_idr)} / {totals.incidents_total} insiden
            </div>
          </div>
        </div>
      )}

      {/* Policy Warnings */}
      {checks &&
        (checks.draft_ledger_count > 0 ||
          !checks.signatories_valid ||
          (detail?.missing_attachments.length ?? 0) > 0) && (
          <div className="rounded-[var(--radius-md)] border border-[var(--color-warning)] bg-[var(--color-surface)] p-3 text-xs text-[var(--color-text)]">
            <strong>Kesiapan Finalisasi:</strong>{" "}
            {checks.draft_ledger_count > 0 &&
              `${checks.draft_ledger_count} transaksi kas masih draft. `}
            {!checks.signatories_valid &&
              `Penanda tangan wajib kurang (${checks.missing_signatories.join(", ")}). `}
            {(detail?.missing_attachments.length ?? 0) > 0 &&
              `Lampiran belum tersedia di disk: ${detail?.missing_attachments.join(", ")}.`}
          </div>
        )}

      {/* Tabs */}
      <div className="flex gap-2 border-b border-[var(--color-border)] pb-2">
        {(
          [
            ["sections", "1. Bagian & Narasi"],
            ["evaluation", "2. Evaluasi & Rekomendasi"],
            ["attachments", "3. Daftar Lampiran"],
          ] as const
        ).map(([k, label]) => (
          <Button
            key={k}
            size="sm"
            variant={tab === k ? "primary" : "secondary"}
            onClick={() => setTab(k)}
          >
            {label}
          </Button>
        ))}
      </div>

      {loading && !detail ? (
        <div className="text-xs text-[var(--color-text-muted)]">Memuat LPJ...</div>
      ) : tab === "sections" && detail ? (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <div className="space-y-1 rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-surface)] p-3">
            {detail.sections.map((sec) => (
              <button
                key={sec.key}
                type="button"
                onClick={() => handleSelectSection(sec.key)}
                className={`w-full rounded-[var(--radius-sm)] px-3 py-2 text-left text-xs transition ${
                  selectedSectionKey === sec.key
                    ? "bg-[var(--color-primary)] font-semibold text-white"
                    : "text-[var(--color-text)] hover:bg-[var(--color-surface-muted)]"
                }`}
              >
                {sec.title}
              </button>
            ))}
          </div>
          <div className="space-y-3 rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-surface)] p-4 md:col-span-2">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-[var(--color-text)]">
                {detail.sections.find((s) => s.key === selectedSectionKey)?.title}
              </h3>
              <Button size="sm" onClick={() => void handleSaveSection()}>
                <Save size={14} className="mr-1" aria-hidden="true" />
                Simpan Narasi
              </Button>
            </div>
            <textarea
              aria-label="Narasi Bagian LPJ"
              rows={10}
              value={narrativeDraft}
              onChange={(e) => setNarrativeDraft(e.target.value)}
              className="w-full rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-surface)] p-3 text-sm text-[var(--color-text)]"
            />
            <p className="text-xs text-[var(--color-text-muted)]">
              Catatan: Mengubah narasi tidak dapat menimpa angka rekapitulasi peserta atau saldo keuangan.
            </p>
          </div>
        </div>
      ) : tab === "evaluation" && detail ? (
        <div className="space-y-3 rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-[var(--color-text)]">
              Catatan Evaluasi Pelaksanaan
            </h3>
            <Button size="sm" onClick={() => setShowEvalModal(true)}>
              <Plus size={14} className="mr-1" aria-hidden="true" />
              Tambah Evaluasi
            </Button>
          </div>
          {detail.evaluations.length === 0 ? (
            <p className="text-xs text-[var(--color-text-muted)]">Belum ada catatan evaluasi.</p>
          ) : (
            <div className="space-y-2">
              {detail.evaluations.map((ev) => (
                <div
                  key={ev.id}
                  className="rounded-[var(--radius-sm)] border border-[var(--color-border)] p-3 text-xs"
                >
                  <div className="font-semibold text-[var(--color-text)]">{ev.issue_title}</div>
                  <div className="mt-1 text-[var(--color-text-muted)]">
                    Solusi: {ev.resolution || "-"} | Rekomendasi: {ev.recommendation || "-"} | PIC:{" "}
                    {ev.pic_name || "-"}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      ) : tab === "attachments" && detail ? (
        <div className="space-y-3 rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-[var(--color-text)]">
              Manifest Lampiran LPJ
            </h3>
            <Button size="sm" onClick={() => setShowAttModal(true)}>
              <Paperclip size={14} className="mr-1" aria-hidden="true" />
              Tambah Lampiran
            </Button>
          </div>
          {detail.attachments.length === 0 ? (
            <p className="text-xs text-[var(--color-text-muted)]">Belum ada lampiran terdaftar.</p>
          ) : (
            <div className="space-y-2">
              {detail.attachments.map((att) => (
                <div
                  key={att.id}
                  className="flex items-center justify-between rounded-[var(--radius-sm)] border border-[var(--color-border)] p-3 text-xs"
                >
                  <div>
                    <div className="font-semibold text-[var(--color-text)]">{att.title}</div>
                    <div className="text-[var(--color-text-muted)]">
                      {att.file_path || "-"} {att.exclusion_reason ? `(${att.exclusion_reason})` : ""}
                    </div>
                  </div>
                  <StatusIndicator
                    tone={
                      !att.included
                        ? "neutral"
                        : att.file_exists
                          ? "success"
                          : "destructive"
                    }
                    label={
                      !att.included
                        ? "Dikecualikan"
                        : att.file_exists
                          ? "Tersedia"
                          : "Hilang"
                    }
                  />
                </div>
              ))}
            </div>
          )}
        </div>
      ) : null}

      <CRUDModal
        open={showEvalModal}
        title="Tambah Evaluasi LPJ"
        onClose={() => setShowEvalModal(false)}
        onSubmit={() => void handleSaveEval()}
        submitLabel="Simpan"
      >
        <div className="space-y-3">
          <label className="block text-xs font-medium text-[var(--color-text)]">
            Judul Isu / Temuan
            <input
              type="text"
              value={evalIssue}
              onChange={(e) => setEvalIssue(e.target.value)}
              className="mt-1 h-9 w-full rounded-[var(--radius-md)] border border-[var(--color-border)] px-2 text-sm"
            />
          </label>
          <label className="block text-xs font-medium text-[var(--color-text)]">
            Tautan Insiden (Opsional)
            <select
              value={evalIncidentId}
              onChange={(e) => setEvalIncidentId(e.target.value)}
              className="mt-1 h-9 w-full rounded-[var(--radius-md)] border border-[var(--color-border)] px-2 text-sm"
            >
              <option value="">-- Tidak ditautkan --</option>
              {detail?.available_incidents.map((inc) => (
                <option key={inc.id} value={inc.id}>
                  {inc.type_code}: {inc.summary}
                </option>
              ))}
            </select>
          </label>
          <label className="block text-xs font-medium text-[var(--color-text)]">
            Solusi
            <input
              type="text"
              value={evalRes}
              onChange={(e) => setEvalRes(e.target.value)}
              className="mt-1 h-9 w-full rounded-[var(--radius-md)] border border-[var(--color-border)] px-2 text-sm"
            />
          </label>
          <label className="block text-xs font-medium text-[var(--color-text)]">
            Rekomendasi
            <input
              type="text"
              value={evalRec}
              onChange={(e) => setEvalRec(e.target.value)}
              className="mt-1 h-9 w-full rounded-[var(--radius-md)] border border-[var(--color-border)] px-2 text-sm"
            />
          </label>
          <label className="block text-xs font-medium text-[var(--color-text)]">
            PIC
            <input
              type="text"
              value={evalPic}
              onChange={(e) => setEvalPic(e.target.value)}
              className="mt-1 h-9 w-full rounded-[var(--radius-md)] border border-[var(--color-border)] px-2 text-sm"
            />
          </label>
        </div>
      </CRUDModal>

      <CRUDModal
        open={showAttModal}
        title="Tambah Lampiran LPJ"
        onClose={() => setShowAttModal(false)}
        onSubmit={() => void handleSaveAttachment()}
        submitLabel="Simpan"
      >
        <div className="space-y-3">
          <label className="block text-xs font-medium text-[var(--color-text)]">
            Judul Lampiran
            <input
              type="text"
              value={attTitle}
              onChange={(e) => setAttTitle(e.target.value)}
              className="mt-1 h-9 w-full rounded-[var(--radius-md)] border border-[var(--color-border)] px-2 text-sm"
            />
          </label>
          <label className="block text-xs font-medium text-[var(--color-text)]">
            Pilih Dokumen Terbit (Opsional)
            <select
              value={attDocRunId}
              onChange={(e) => {
                setAttDocRunId(e.target.value);
                const dr = detail?.available_doc_runs.find(
                  (d) => d.id === e.target.value,
                );
                if (dr) {
                  setAttPath(dr.output_path);
                  if (!attTitle) setAttTitle(`${dr.doc_type} (${dr.format})`);
                }
              }}
              className="mt-1 h-9 w-full rounded-[var(--radius-md)] border border-[var(--color-border)] px-2 text-sm"
            >
              <option value="">-- Path Manual --</option>
              {detail?.available_doc_runs.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.doc_type} ({d.format}) - {d.status}
                </option>
              ))}
            </select>
          </label>
          <label className="block text-xs font-medium text-[var(--color-text)]">
            Path File
            <input
              type="text"
              value={attPath}
              onChange={(e) => setAttPath(e.target.value)}
              className="mt-1 h-9 w-full rounded-[var(--radius-md)] border border-[var(--color-border)] px-2 text-sm"
            />
          </label>
          <label className="flex items-center gap-2 text-xs font-medium text-[var(--color-text)]">
            <input
              type="checkbox"
              checked={attIncluded}
              onChange={(e) => setAttIncluded(e.target.checked)}
            />
            Sertakan dalam paket lampiran final
          </label>
          {!attIncluded && (
            <label className="block text-xs font-medium text-[var(--color-text)]">
              Alasan Pengecualian (Wajib)
              <input
                type="text"
                value={attExclusion}
                onChange={(e) => setAttExclusion(e.target.value)}
                className="mt-1 h-9 w-full rounded-[var(--radius-md)] border border-[var(--color-border)] px-2 text-sm"
              />
            </label>
          )}
        </div>
      </CRUDModal>
    </div>
  );
}
