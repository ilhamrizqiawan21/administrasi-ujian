import { useCallback, useEffect, useState } from "react";
import { Banknote, BookOpen, Calculator, Plus, Sparkles } from "lucide-react";
import { Button } from "../../components/ui/Button";
import { StatusIndicator, useToast } from "../../components/ui/Feedback";
import { CRUDModal } from "../../components/ui/Modal";
import { invokeBridge } from "../../lib/bridge";
import type { ExamItem } from "../evt/types";
import type { FinanceDetail } from "./types";

interface FinancePageProps {
  institutionId: string;
  activeExam: ExamItem | null;
}

function getErrMsg(err: unknown, fallback: string): string {
  return err instanceof Error ? err.message : fallback;
}

function fmtIdr(val: number): string {
  return `Rp ${val.toLocaleString("id-ID")}`;
}

export function FinancePage({ institutionId, activeExam }: FinancePageProps) {
  const { pushToast } = useToast();
  const [detail, setDetail] = useState<FinanceDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [tab, setTab] = useState<"rab" | "cashbook" | "honor">("rab");

  // Category modal
  const [showCatModal, setShowCatModal] = useState(false);
  const [catLabel, setCatLabel] = useState("");
  const [catFund, setCatFund] = useState("BOS");

  // Ledger modal
  const [showLedgerModal, setShowLedgerModal] = useState(false);
  const [ledCatId, setLedCatId] = useState("");
  const [ledKind, setLedKind] = useState<"income" | "expense">("expense");
  const [ledAmount, setLedAmount] = useState(100000);
  const [ledDate, setLedDate] = useState("2026-12-01");
  const [ledRef, setLedRef] = useState("");

  const loadDetail = useCallback(async () => {
    if (!activeExam) {
      setDetail(null);
      return;
    }
    setLoading(true);
    try {
      const data = await invokeBridge<FinanceDetail>("fin.detail", {
        institution_id: institutionId,
        exam_id: activeExam.id,
      });
      setDetail(data);
      if (data.categories.length > 0 && !ledCatId) {
        setLedCatId(data.categories[0].id);
      }
    } catch (err) {
      pushToast(getErrMsg(err, "Gagal memuat data keuangan."), "error");
    } finally {
      setLoading(false);
    }
  }, [institutionId, activeExam, pushToast, ledCatId]);

  useEffect(() => {
    void loadDetail();
  }, [loadDetail]);

  const handleSaveCategory = async () => {
    if (!activeExam || !catLabel.trim()) return;
    try {
      await invokeBridge("fin.categories.save", {
        institution_id: institutionId,
        exam_id: activeExam.id,
        label: catLabel.trim(),
        source_fund: catFund,
      });
      setShowCatModal(false);
      setCatLabel("");
      pushToast("Kategori anggaran ditambahkan.", "success");
      await loadDetail();
    } catch (err) {
      pushToast(getErrMsg(err, "Gagal menyimpan kategori."), "error");
    }
  };

  const handleCreateBudgetVersion = async () => {
    if (!activeExam) return;
    try {
      await invokeBridge("fin.budget.create_version", {
        institution_id: institutionId,
        exam_id: activeExam.id,
      });
      pushToast("Draf versi RAB dibuat.", "success");
      await loadDetail();
    } catch (err) {
      pushToast(getErrMsg(err, "Gagal membuat versi RAB."), "error");
    }
  };

  const handleSaveLedger = async () => {
    if (!activeExam || !ledCatId) return;
    try {
      await invokeBridge("fin.ledger.save", {
        institution_id: institutionId,
        exam_id: activeExam.id,
        category_id: ledCatId,
        kind: ledKind,
        amount_idr: ledAmount,
        entry_date: ledDate,
        reference: ledRef,
      });
      setShowLedgerModal(false);
      setLedRef("");
      pushToast("Entri kas draf ditambahkan.", "success");
      await loadDetail();
    } catch (err) {
      pushToast(getErrMsg(err, "Gagal menyimpan entri kas."), "error");
    }
  };

  const handlePostLedger = async (entryId: string) => {
    if (!activeExam) return;
    try {
      await invokeBridge("fin.ledger.post", {
        institution_id: institutionId,
        exam_id: activeExam.id,
        entry_id: entryId,
      });
      pushToast("Entri kas diposting.", "success");
      await loadDetail();
    } catch (err) {
      pushToast(getErrMsg(err, "Gagal memposting entri."), "error");
    }
  };

  const handleGenerateHonor = async () => {
    if (!activeExam) return;
    try {
      const res = await invokeBridge<{ created_count: number }>(
        "fin.honor.generate",
        {
          institution_id: institutionId,
          exam_id: activeExam.id,
        }
      );
      pushToast(`${res.created_count} baris honorarium dibuat.`, "success");
      await loadDetail();
    } catch (err) {
      pushToast(getErrMsg(err, "Gagal menghasilkan honorarium."), "error");
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
              variant={tab === "rab" ? "primary" : "secondary"}
              onClick={() => setTab("rab")}
            >
              <Calculator size={16} aria-hidden="true" />
              RAB &amp; Kategori
            </Button>
            <Button
              variant={tab === "cashbook" ? "primary" : "secondary"}
              onClick={() => setTab("cashbook")}
            >
              <BookOpen size={16} aria-hidden="true" />
              Buku Kas &amp; Realisasi
            </Button>
            <Button
              variant={tab === "honor" ? "primary" : "secondary"}
              onClick={() => setTab("honor")}
            >
              <Banknote size={16} aria-hidden="true" />
              Honorarium &amp; Kuitansi
            </Button>
          </div>

          {detail && (
            <StatusIndicator
              tone={detail.closing_balance_idr >= 0 ? "success" : "destructive"}
              label={`Saldo Akhir: ${fmtIdr(detail.closing_balance_idr)}`}
            />
          )}
        </div>
      </section>

      {!detail ? (
        <section className="uc-panel">
          <div className="uc-panel-body">
            <p className="uc-sub">
              {loading ? "Memuat data keuangan..." : "Tidak ada data."}
            </p>
          </div>
        </section>
      ) : tab === "rab" ? (
        <div style={{ display: "grid", gap: "var(--space-4)" }}>
          <section className="uc-panel">
            <div className="uc-panel-header">
              <h2>Kategori Anggaran &amp; Varians</h2>
              <div style={{ display: "flex", gap: 8 }}>
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => setShowCatModal(true)}
                >
                  <Plus size={14} aria-hidden="true" />
                  Tambah Kategori
                </Button>
                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => void handleCreateBudgetVersion()}
                >
                  <Plus size={14} aria-hidden="true" />
                  Buat Versi RAB
                </Button>
              </div>
            </div>
            <div className="uc-panel-body" style={{ overflowX: "auto" }}>
              <table className="uc-table" aria-label="Varians Anggaran">
                <thead>
                  <tr>
                    <th>Kategori</th>
                    <th>RAB Disetujui</th>
                    <th>Realisasi</th>
                    <th>Sisa</th>
                  </tr>
                </thead>
                <tbody>
                  {detail.variance.map((v) => (
                    <tr key={v.category_id}>
                      <td>{v.category_label}</td>
                      <td>{fmtIdr(v.approved_rab_idr)}</td>
                      <td>{fmtIdr(v.actual_expense_idr)}</td>
                      <td>{fmtIdr(v.remaining_idr)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </div>
      ) : tab === "cashbook" ? (
        <section className="uc-panel">
          <div className="uc-panel-header">
            <h2>Buku Kas Umum (Saldo Berjalan)</h2>
            <Button
              variant="primary"
              size="sm"
              disabled={detail.categories.length === 0}
              onClick={() => setShowLedgerModal(true)}
            >
              <Plus size={14} aria-hidden="true" />
              Catat Kas
            </Button>
          </div>
          <div className="uc-panel-body" style={{ overflowX: "auto" }}>
            <table className="uc-table" aria-label="Buku Kas">
              <thead>
                <tr>
                  <th>Tanggal</th>
                  <th>Kategori</th>
                  <th>Jenis</th>
                  <th>Nominal</th>
                  <th>Status</th>
                  <th>Saldo Berjalan</th>
                  <th>Aksi</th>
                </tr>
              </thead>
              <tbody>
                {detail.cashbook.map((c) => (
                  <tr key={c.id}>
                    <td>{c.entry_date}</td>
                    <td>{c.category_label}</td>
                    <td>{c.kind}</td>
                    <td>{fmtIdr(c.amount_idr)}</td>
                    <td>{c.state}</td>
                    <td>
                      {c.running_balance_idr !== null
                        ? fmtIdr(c.running_balance_idr)
                        : "-"}
                    </td>
                    <td>
                      {c.state === "draft" && (
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={() => void handlePostLedger(c.id)}
                        >
                          Posting
                        </Button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ) : (
        <section className="uc-panel">
          <div className="uc-panel-header">
            <h2>Daftar Honorarium &amp; Terbilang</h2>
            <Button
              variant="primary"
              size="sm"
              onClick={() => void handleGenerateHonor()}
            >
              <Sparkles size={14} aria-hidden="true" />
              Hitung Honor Aktual
            </Button>
          </div>
          <div className="uc-panel-body" style={{ overflowX: "auto" }}>
            <table className="uc-table" aria-label="Daftar Honorarium">
              <thead>
                <tr>
                  <th>Nama</th>
                  <th>Peran</th>
                  <th>Total</th>
                  <th>Terbilang</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {detail.honor_lines.map((h) => (
                  <tr key={h.id}>
                    <td>{h.person_name}</td>
                    <td>{h.role_code}</td>
                    <td>{fmtIdr(h.amount_idr)}</td>
                    <td>{h.amount_words}</td>
                    <td>{h.state}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      <CRUDModal
        open={showCatModal}
        title="Tambah Kategori Anggaran"
        onClose={() => setShowCatModal(false)}
        onSubmit={() => void handleSaveCategory()}
      >
        <div style={{ display: "grid", gap: 12 }}>
          <label className="uc-field">
            <span className="uc-label">Nama Kategori</span>
            <input
              type="text"
              className="uc-input"
              value={catLabel}
              onChange={(e) => setCatLabel(e.target.value)}
            />
          </label>
          <label className="uc-field">
            <span className="uc-label">Sumber Dana</span>
            <input
              type="text"
              className="uc-input"
              value={catFund}
              onChange={(e) => setCatFund(e.target.value)}
            />
          </label>
        </div>
      </CRUDModal>

      <CRUDModal
        open={showLedgerModal}
        title="Catat Transaksi Kas"
        onClose={() => setShowLedgerModal(false)}
        onSubmit={() => void handleSaveLedger()}
      >
        <div style={{ display: "grid", gap: 12 }}>
          <label className="uc-field">
            <span className="uc-label">Kategori</span>
            <select
              className="uc-input"
              value={ledCatId}
              onChange={(e) => setLedCatId(e.target.value)}
            >
              {(detail?.categories ?? []).map((c) => (
                <option key={c.id} value={c.id}>
                  {c.label}
                </option>
              ))}
            </select>
          </label>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
            <label className="uc-field">
              <span className="uc-label">Jenis</span>
              <select
                className="uc-input"
                value={ledKind}
                onChange={(e) =>
                  setLedKind(e.target.value as "income" | "expense")
                }
              >
                <option value="income">Pemasukan</option>
                <option value="expense">Pengeluaran</option>
              </select>
            </label>
            <label className="uc-field">
              <span className="uc-label">Nominal (IDR)</span>
              <input
                type="number"
                min={1}
                className="uc-input"
                value={ledAmount}
                onChange={(e) => setLedAmount(Number(e.target.value))}
              />
            </label>
          </div>
          <label className="uc-field">
            <span className="uc-label">Tanggal</span>
            <input
              type="date"
              className="uc-input"
              value={ledDate}
              onChange={(e) => setLedDate(e.target.value)}
            />
          </label>
          <label className="uc-field">
            <span className="uc-label">Referensi</span>
            <input
              type="text"
              className="uc-input"
              value={ledRef}
              onChange={(e) => setLedRef(e.target.value)}
            />
          </label>
        </div>
      </CRUDModal>
    </div>
  );
}
