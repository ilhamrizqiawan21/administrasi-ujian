import { useCallback, useEffect, useState } from "react";
import { Download, FileCheck2, History, Printer, RefreshCw } from "lucide-react";
import { Button } from "../../components/ui/Button";
import { StatusIndicator, useToast } from "../../components/ui/Feedback";
import { invokeBridge } from "../../lib/bridge";
import type { ExamItem } from "../evt/types";
import type { DocDetail, DocFormat, PaperSize } from "./types";

interface DocumentCenterPageProps {
  institutionId: string;
  activeExam: ExamItem | null;
}

function getErrMsg(err: unknown, fallback: string): string {
  return err instanceof Error ? err.message : fallback;
}

export function DocumentCenterPage({
  institutionId,
  activeExam,
}: DocumentCenterPageProps) {
  const { pushToast } = useToast();
  const [detail, setDetail] = useState<DocDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);

  const [docType, setDocType] = useState("daftar_hadir");
  const [format, setFormat] = useState<DocFormat>("pdf");
  const [paperSize, setPaperSize] = useState<PaperSize>("A4");
  const [series, setSeries] = useState("UJN");
  const [lastHash, setLastHash] = useState<string | null>(null);

  const loadDetail = useCallback(async () => {
    if (!activeExam) {
      setDetail(null);
      return;
    }
    setLoading(true);
    try {
      const data = await invokeBridge<DocDetail>("doc.detail", {
        institution_id: institutionId,
        exam_id: activeExam.id,
      });
      setDetail(data);
    } catch (err) {
      pushToast(getErrMsg(err, "Gagal memuat riwayat dokumen."), "error");
    } finally {
      setLoading(false);
    }
  }, [institutionId, activeExam, pushToast]);

  useEffect(() => {
    void loadDetail();
  }, [loadDetail]);

  const handleGenerate = async (isFinal: boolean) => {
    if (!activeExam) return;
    setGenerating(true);
    try {
      const res = await invokeBridge<{
        run_id: string;
        document_number: string | null;
        output_hash: string;
      }>("doc.generate", {
        institution_id: institutionId,
        exam_id: activeExam.id,
        doc_type: docType,
        format,
        paper_size: paperSize,
        series: series.trim() || "UJN",
        is_final: isFinal,
      });
      setLastHash(res.output_hash);
      pushToast(
        isFinal
          ? `Dokumen final diterbitkan (${res.document_number ?? "-"}).`
          : "Pratinjau dokumen berhasil dibuat (tanpa nomor surat).",
        "success"
      );
      await loadDetail();
    } catch (err) {
      pushToast(getErrMsg(err, "Gagal menghasilkan dokumen."), "error");
    } finally {
      setGenerating(false);
    }
  };

  const handleReprint = async (runId: string) => {
    if (!activeExam) return;
    try {
      const res = await invokeBridge<{ output_hash: string }>("doc.reprint", {
        institution_id: institutionId,
        exam_id: activeExam.id,
        run_id: runId,
      });
      pushToast(`Arsip siap dicetak ulang (hash ${res.output_hash.slice(0, 8)}).`, "info");
    } catch (err) {
      pushToast(getErrMsg(err, "Gagal memuat arsip dokumen."), "error");
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
        <div className="uc-panel-header">
          <h2>Generator &amp; Ekspor Dokumen</h2>
          <Button variant="secondary" size="sm" onClick={() => window.print()}>
            <Printer size={14} aria-hidden="true" />
            Cetak Halaman
          </Button>
        </div>
        <div className="uc-panel-body" style={{ display: "grid", gap: 12 }}>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
              gap: 12,
            }}
          >
            <label className="uc-field">
              <span className="uc-label">Jenis Dokumen</span>
              <select
                className="uc-input"
                aria-label="Jenis Dokumen"
                value={docType}
                onChange={(e) => setDocType(e.target.value)}
              >
                <option value="kartu_peserta">Kartu Peserta</option>
                <option value="daftar_hadir">Daftar Hadir</option>
                <option value="berita_acara">Berita Acara</option>
                <option value="denah_ruang">Denah Ruang</option>
                <option value="sk_panitia">SK Panitia</option>
                <option value="program_kerja">Program Kerja</option>
              </select>
            </label>

            <label className="uc-field">
              <span className="uc-label">Format</span>
              <select
                className="uc-input"
                aria-label="Format Dokumen"
                value={format}
                onChange={(e) => setFormat(e.target.value as DocFormat)}
              >
                <option value="pdf">PDF (ReportLab)</option>
                <option value="docx">DOCX (Word Editable)</option>
                <option value="xlsx">XLSX (Excel)</option>
              </select>
            </label>

            <label className="uc-field">
              <span className="uc-label">Ukuran Kertas</span>
              <select
                className="uc-input"
                aria-label="Ukuran Kertas"
                value={paperSize}
                onChange={(e) => setPaperSize(e.target.value as PaperSize)}
              >
                <option value="A4">A4 (210 x 297 mm)</option>
                <option value="F4">F4 (215 x 330 mm)</option>
              </select>
            </label>

            <label className="uc-field">
              <span className="uc-label">Seri Nomor Surat</span>
              <input
                type="text"
                className="uc-input"
                value={series}
                onChange={(e) => setSeries(e.target.value)}
              />
            </label>
          </div>

          <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
            <Button
              variant="secondary"
              loading={generating}
              onClick={() => void handleGenerate(false)}
            >
              <Download size={16} aria-hidden="true" />
              Pratinjau (Tanpa Nomor)
            </Button>
            <Button
              variant="primary"
              loading={generating}
              onClick={() => void handleGenerate(true)}
            >
              <FileCheck2 size={16} aria-hidden="true" />
              Terbitkan Final &amp; Nomor
            </Button>
          </div>
          {lastHash && (
            <p className="uc-sub" style={{ fontSize: 12 }}>
              SHA-256 keluaran terakhir: <code>{lastHash}</code>
            </p>
          )}
        </div>
      </section>

      <section className="uc-panel">
        <div className="uc-panel-header">
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <History size={16} aria-hidden="true" />
            <h2>Riwayat Versi Dokumen</h2>
          </div>
          <Button variant="secondary" size="sm" onClick={() => void loadDetail()}>
            <RefreshCw size={14} aria-hidden="true" />
            Muat Ulang
          </Button>
        </div>
        <div className="uc-panel-body" style={{ overflowX: "auto" }}>
          {loading ? (
            <p className="uc-sub">Memuat riwayat...</p>
          ) : (
            <table className="uc-table" aria-label="Riwayat Dokumen">
              <thead>
                <tr>
                  <th>Dokumen</th>
                  <th>Format</th>
                  <th>Status</th>
                  <th>Sinkronisasi</th>
                  <th>Aksi</th>
                </tr>
              </thead>
              <tbody>
                {(detail?.runs ?? []).map((r) => (
                  <tr key={r.id}>
                    <td>{r.doc_type}</td>
                    <td>{r.format.toUpperCase()}</td>
                    <td>{r.status}</td>
                    <td>
                      <StatusIndicator
                        tone={r.is_stale ? "warning" : "success"}
                        label={r.is_stale ? "Perlu Perbarui (Stale)" : "Mutakhir"}
                      />
                    </td>
                    <td>
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => void handleReprint(r.id)}
                      >
                        Cetak Ulang
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </section>
    </div>
  );
}
