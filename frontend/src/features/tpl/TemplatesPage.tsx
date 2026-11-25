import { useCallback, useEffect, useState } from "react";
import { FileText, Image as ImageIcon, Palette, Plus } from "lucide-react";
import { Button } from "../../components/ui/Button";
import { StatusIndicator, useToast } from "../../components/ui/Feedback";
import { CRUDModal } from "../../components/ui/Modal";
import { invokeBridge } from "../../lib/bridge";
import type { PaperSize, TplDetail } from "./types";

interface TemplatesPageProps {
  institutionId: string;
}

function getErrMsg(err: unknown, fallback: string): string {
  return err instanceof Error ? err.message : fallback;
}

export function TemplatesPage({ institutionId }: TemplatesPageProps) {
  const { pushToast } = useToast();
  const [detail, setDetail] = useState<TplDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [tab, setTab] = useState<"letterhead" | "templates" | "brand">(
    "letterhead"
  );

  // Manual letterhead modal
  const [showLhModal, setShowLhModal] = useState(false);
  const [lhName, setLhName] = useState("Kop Resmi");
  const [lhLines, setLhLines] = useState("PEMERINTAH KABUPATEN\nSEKOLAH CONTOH");
  const [lhPaper, setLhPaper] = useState<PaperSize>("A4");
  const [lhLineStyle, setLhLineStyle] = useState<"single" | "double" | "none">(
    "double"
  );

  // Custom template modal
  const [showTplModal, setShowTplModal] = useState(false);
  const [tplDocType, setTplDocType] = useState("kartu_peserta");
  const [tplName, setTplName] = useState("");
  const [tplPaper, setTplPaper] = useState<PaperSize>("F4");
  const [tplCols, setTplCols] = useState(2);

  // Brand theme state
  const [themeName, setThemeName] = useState("Ocean Ledger");
  const [appTitle, setAppTitle] = useState("Ujian Cerdas");
  const [surfaceHex, setSurfaceHex] = useState("#FFFFFF");
  const [textHex, setTextHex] = useState("#0F172A");
  const [accentHex, setAccentHex] = useState("#0F766E");

  const loadDetail = useCallback(async () => {
    setLoading(true);
    try {
      const data = await invokeBridge<TplDetail>("tpl.detail", {
        institution_id: institutionId,
      });
      setDetail(data);
    } catch (err) {
      pushToast(getErrMsg(err, "Gagal memuat template & branding."), "error");
    } finally {
      setLoading(false);
    }
  }, [institutionId, pushToast]);

  useEffect(() => {
    void loadDetail();
  }, [loadDetail]);

  const handleSaveManualLh = async () => {
    const lines = lhLines
      .split("\n")
      .map((s) => s.trim())
      .filter(Boolean);
    if (!lhName.trim() || lines.length === 0) return;
    try {
      await invokeBridge("tpl.letterheads.save_manual", {
        institution_id: institutionId,
        name: lhName.trim(),
        header_lines: lines,
        alignment: "center",
        line_style: lhLineStyle,
        paper_size: lhPaper,
      });
      setShowLhModal(false);
      pushToast("Kop surat disimpan (versi baru).", "success");
      await loadDetail();
    } catch (err) {
      pushToast(getErrMsg(err, "Gagal menyimpan kop surat."), "error");
    }
  };

  const handleSaveTemplate = async () => {
    if (!tplName.trim()) return;
    try {
      await invokeBridge("tpl.templates.save", {
        institution_id: institutionId,
        doc_type: tplDocType,
        name: tplName.trim(),
        engine: "reportlab",
        layout: {
          paper_size: tplPaper,
          columns: tplCols,
        },
        activate: true,
      });
      setShowTplModal(false);
      setTplName("");
      pushToast("Template kustom disimpan.", "success");
      await loadDetail();
    } catch (err) {
      pushToast(getErrMsg(err, "Gagal menyimpan template."), "error");
    }
  };

  const handleSaveTheme = async () => {
    try {
      const res = await invokeBridge<{ contrast_ratio: number }>(
        "tpl.themes.save",
        {
          institution_id: institutionId,
          name: themeName.trim() || "Tema Lembaga",
          app_title: appTitle.trim() || "Ujian Cerdas",
          palette_preset: "ocean_ledger",
          density: "comfortable",
          surface_hex: surfaceHex,
          text_hex: textHex,
          accent_hex: accentHex,
        }
      );
      pushToast(`Tema disimpan (rasio kontras ${res.contrast_ratio}:1).`, "success");
      await loadDetail();
    } catch (err) {
      pushToast(getErrMsg(err, "Gagal menyimpan tema."), "error");
    }
  };

  return (
    <div style={{ display: "grid", gap: "var(--space-4)" }}>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
        <Button
          variant={tab === "letterhead" ? "primary" : "secondary"}
          onClick={() => setTab("letterhead")}
        >
          <ImageIcon size={16} aria-hidden="true" />
          Kop Surat ({detail?.letterheads.length ?? 0})
        </Button>
        <Button
          variant={tab === "templates" ? "primary" : "secondary"}
          onClick={() => setTab("templates")}
        >
          <FileText size={16} aria-hidden="true" />
          Katalog Template ({detail?.templates.length ?? 0})
        </Button>
        <Button
          variant={tab === "brand" ? "primary" : "secondary"}
          onClick={() => setTab("brand")}
        >
          <Palette size={16} aria-hidden="true" />
          Branding &amp; Kontras
        </Button>
      </div>

      {!detail ? (
        <section className="uc-panel">
          <div className="uc-panel-body">
            <p className="uc-sub">
              {loading ? "Memuat template..." : "Tidak ada data."}
            </p>
          </div>
        </section>
      ) : tab === "letterhead" ? (
        <section className="uc-panel">
          <div className="uc-panel-header">
            <h2>Daftar Versi Kop Surat</h2>
            <Button
              variant="primary"
              size="sm"
              onClick={() => setShowLhModal(true)}
            >
              <Plus size={14} aria-hidden="true" />
              Buat Kop Manual
            </Button>
          </div>
          <div className="uc-panel-body" style={{ overflowX: "auto" }}>
            <table className="uc-table" aria-label="Daftar Kop Surat">
              <thead>
                <tr>
                  <th>Nama</th>
                  <th>Mode</th>
                  <th>Versi</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {detail.letterheads.map((lh) => (
                  <tr key={lh.id}>
                    <td>{lh.name}</td>
                    <td>{lh.mode}</td>
                    <td>v{lh.version}</td>
                    <td>
                      <StatusIndicator
                        tone={lh.active ? "success" : "neutral"}
                        label={lh.active ? "Aktif" : "Arsip"}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ) : tab === "templates" ? (
        <section className="uc-panel">
          <div className="uc-panel-header">
            <div>
              <h2>Katalog Template Dokumen</h2>
              <p className="uc-sub">
                F4 eksplisit: 215 x 330 mm · A4: 210 x 297 mm
              </p>
            </div>
            <Button
              variant="primary"
              size="sm"
              onClick={() => setShowTplModal(true)}
            >
              <Plus size={14} aria-hidden="true" />
              Template Kustom
            </Button>
          </div>
          <div className="uc-panel-body" style={{ overflowX: "auto" }}>
            <table className="uc-table" aria-label="Katalog Template">
              <thead>
                <tr>
                  <th>Nama Template</th>
                  <th>Jenis Dokumen</th>
                  <th>Engine</th>
                  <th>Versi</th>
                  <th>Sumber</th>
                </tr>
              </thead>
              <tbody>
                {detail.templates.map((t) => (
                  <tr key={t.id}>
                    <td>{t.name}</td>
                    <td>{t.doc_type}</td>
                    <td>{t.engine}</td>
                    <td>v{t.version}</td>
                    <td>{t.builtin ? "Bawaan" : "Kustom"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ) : (
        <section className="uc-panel">
          <div className="uc-panel-header">
            <h2>Editor Branding &amp; Kontras (WCAG &ge; 4.5:1)</h2>
            <Button variant="primary" size="sm" onClick={() => void handleSaveTheme()}>
              Simpan Tema
            </Button>
          </div>
          <div className="uc-panel-body" style={{ display: "grid", gap: 12 }}>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
              <label className="uc-field">
                <span className="uc-label">Nama Profil Tema</span>
                <input
                  type="text"
                  className="uc-input"
                  value={themeName}
                  onChange={(e) => setThemeName(e.target.value)}
                />
              </label>
              <label className="uc-field">
                <span className="uc-label">Judul Aplikasi</span>
                <input
                  type="text"
                  className="uc-input"
                  value={appTitle}
                  onChange={(e) => setAppTitle(e.target.value)}
                />
              </label>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12 }}>
              <label className="uc-field">
                <span className="uc-label">Latar (#RRGGBB)</span>
                <input
                  type="text"
                  className="uc-input"
                  value={surfaceHex}
                  onChange={(e) => setSurfaceHex(e.target.value)}
                />
              </label>
              <label className="uc-field">
                <span className="uc-label">Teks Utama (#RRGGBB)</span>
                <input
                  type="text"
                  className="uc-input"
                  value={textHex}
                  onChange={(e) => setTextHex(e.target.value)}
                />
              </label>
              <label className="uc-field">
                <span className="uc-label">Aksen (#RRGGBB)</span>
                <input
                  type="text"
                  className="uc-input"
                  value={accentHex}
                  onChange={(e) => setAccentHex(e.target.value)}
                />
              </label>
            </div>
          </div>
        </section>
      )}

      <CRUDModal
        open={showLhModal}
        title="Buat Kop Surat Manual"
        onClose={() => setShowLhModal(false)}
        onSubmit={() => void handleSaveManualLh()}
      >
        <div style={{ display: "grid", gap: 12 }}>
          <label className="uc-field">
            <span className="uc-label">Nama Kop</span>
            <input
              type="text"
              className="uc-input"
              value={lhName}
              onChange={(e) => setLhName(e.target.value)}
            />
          </label>
          <label className="uc-field">
            <span className="uc-label">Baris Kop (satu per baris)</span>
            <textarea
              rows={3}
              className="uc-input"
              value={lhLines}
              onChange={(e) => setLhLines(e.target.value)}
            />
          </label>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
            <label className="uc-field">
              <span className="uc-label">Kertas</span>
              <select
                className="uc-input"
                value={lhPaper}
                onChange={(e) => setLhPaper(e.target.value as PaperSize)}
              >
                <option value="A4">A4 (210 x 297 mm)</option>
                <option value="F4">F4 (215 x 330 mm)</option>
              </select>
            </label>
            <label className="uc-field">
              <span className="uc-label">Garis Bawah</span>
              <select
                className="uc-input"
                value={lhLineStyle}
                onChange={(e) =>
                  setLhLineStyle(e.target.value as "single" | "double" | "none")
                }
              >
                <option value="double">Ganda</option>
                <option value="single">Tunggal</option>
                <option value="none">Tanpa Garis</option>
              </select>
            </label>
          </div>
        </div>
      </CRUDModal>

      <CRUDModal
        open={showTplModal}
        title="Tambah Template Kustom"
        onClose={() => setShowTplModal(false)}
        onSubmit={() => void handleSaveTemplate()}
      >
        <div style={{ display: "grid", gap: 12 }}>
          <label className="uc-field">
            <span className="uc-label">Jenis Dokumen</span>
            <select
              className="uc-input"
              value={tplDocType}
              onChange={(e) => setTplDocType(e.target.value)}
            >
              <option value="kartu_peserta">Kartu Peserta</option>
              <option value="daftar_hadir">Daftar Hadir</option>
              <option value="berita_acara">Berita Acara</option>
              <option value="denah_ruang">Denah Ruang</option>
              <option value="sk_panitia">SK Panitia</option>
            </select>
          </label>
          <label className="uc-field">
            <span className="uc-label">Nama Template</span>
            <input
              type="text"
              className="uc-input"
              value={tplName}
              onChange={(e) => setTplName(e.target.value)}
            />
          </label>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
            <label className="uc-field">
              <span className="uc-label">Ukuran Kertas</span>
              <select
                className="uc-input"
                value={tplPaper}
                onChange={(e) => setTplPaper(e.target.value as PaperSize)}
              >
                <option value="A4">A4</option>
                <option value="F4">F4 (215 x 330 mm)</option>
              </select>
            </label>
            <label className="uc-field">
              <span className="uc-label">Kolom</span>
              <input
                type="number"
                min={1}
                max={3}
                className="uc-input"
                value={tplCols}
                onChange={(e) => setTplCols(Number(e.target.value))}
              />
            </label>
          </div>
        </div>
      </CRUDModal>
    </div>
  );
}
