import { useCallback, useEffect, useMemo, useState } from "react";
import { ArrowLeftRight, FileUp, Package, Plus, Printer, Sparkles } from "lucide-react";
import { Button } from "../../components/ui/Button";
import { StatusIndicator, useToast } from "../../components/ui/Feedback";
import { CRUDModal } from "../../components/ui/Modal";
import { invokeBridge } from "../../lib/bridge";
import type { ExamItem } from "../evt/types";
import type { PlanItem } from "../ses/types";
import type { ExpeditionDetail, SubmissionMatrixItem } from "./types";

interface ExpeditionPageProps {
  institutionId: string;
  activeExam: ExamItem | null;
}

function getErrMsg(err: unknown, fallback: string): string {
  return err instanceof Error ? err.message : fallback;
}

export function ExpeditionPage({
  institutionId,
  activeExam,
}: ExpeditionPageProps) {
  const { pushToast } = useToast();
  const [detail, setDetail] = useState<ExpeditionDetail | null>(null);
  const [plans, setPlans] = useState<PlanItem[]>([]);
  const [selectedPlanId, setSelectedPlanId] = useState("");
  const [loading, setLoading] = useState(false);
  const [tab, setTab] = useState<"matrix" | "print" | "handover">("matrix");
  const [filterState, setFilterState] = useState("");
  const [onlyLate, setOnlyLate] = useState(false);

  // Custom item modal
  const [showItemModal, setShowItemModal] = useState(false);
  const [itemSubj, setItemSubj] = useState("");
  const [itemClass, setItemClass] = useState("");
  const [itemType, setItemType] = useState("naskah");

  // Receive modal
  const [receiveItem, setReceiveItem] = useState<SubmissionMatrixItem | null>(
    null
  );
  const [assetId, setAssetId] = useState("");
  const [receiveNote, setReceiveNote] = useState("");

  // Review modal
  const [reviewItem, setReviewItem] = useState<SubmissionMatrixItem | null>(
    null
  );
  const [reviewState, setReviewState] = useState<
    "received" | "revision" | "valid" | "ready"
  >("valid");
  const [reviewNote, setReviewNote] = useState("");

  // Print compute
  const [reservePerRoom, setReservePerRoom] = useState(2);
  const [excludeCbt, setExcludeCbt] = useState(true);

  // Handover modal
  const [showHoModal, setShowHoModal] = useState(false);
  const [hoMaterial, setHoMaterial] = useState("Naskah Ujian");
  const [hoExpected, setHoExpected] = useState(10);
  const [hoActual, setHoActual] = useState(10);
  const [hoFrom, setHoFrom] = useState("Panitia");
  const [hoTo, setHoTo] = useState("Pengawas");

  const loadAll = useCallback(async () => {
    if (!activeExam) {
      setDetail(null);
      setPlans([]);
      return;
    }
    setLoading(true);
    try {
      const [expData, planData] = await Promise.all([
        invokeBridge<ExpeditionDetail>("exp.detail", {
          institution_id: institutionId,
          exam_id: activeExam.id,
        }),
        invokeBridge<{ items: PlanItem[] }>("ses.plans.list", {
          institution_id: institutionId,
          exam_id: activeExam.id,
        }),
      ]);
      setDetail(expData);
      setPlans(planData.items);
      if (planData.items.length > 0 && !selectedPlanId) {
        setSelectedPlanId(planData.items[0].id);
      }
    } catch (err) {
      pushToast(getErrMsg(err, "Gagal memuat data ekspedisi."), "error");
    } finally {
      setLoading(false);
    }
  }, [institutionId, activeExam, pushToast, selectedPlanId]);

  useEffect(() => {
    void loadAll();
  }, [loadAll]);

  const filteredItems = useMemo(() => {
    return (detail?.items ?? []).filter((it) => {
      if (filterState && it.state !== filterState) return false;
      if (onlyLate && !it.is_late) return false;
      return true;
    });
  }, [detail, filterState, onlyLate]);

  const handleGenerateMatrix = async () => {
    if (!activeExam) return;
    try {
      const res = await invokeBridge<{ created_count: number }>(
        "exp.matrix.generate",
        {
          institution_id: institutionId,
          exam_id: activeExam.id,
        }
      );
      pushToast(`${res.created_count} item matriks dibuat.`, "success");
      await loadAll();
    } catch (err) {
      pushToast(getErrMsg(err, "Gagal membuat matriks berkas."), "error");
    }
  };

  const handleSaveCustomItem = async () => {
    if (!activeExam || !itemSubj.trim() || !itemClass.trim()) return;
    try {
      await invokeBridge("exp.items.save", {
        institution_id: institutionId,
        exam_id: activeExam.id,
        subject_label: itemSubj.trim(),
        class_label: itemClass.trim(),
        type_code: itemType.trim() || "custom",
      });
      setShowItemModal(false);
      setItemSubj("");
      setItemClass("");
      pushToast("Item ekspedisi ditambahkan.", "success");
      await loadAll();
    } catch (err) {
      pushToast(getErrMsg(err, "Gagal menambah item ekspedisi."), "error");
    }
  };

  const handleReceive = async () => {
    if (!activeExam || !receiveItem || !assetId.trim()) return;
    try {
      await invokeBridge("exp.submissions.receive", {
        institution_id: institutionId,
        exam_id: activeExam.id,
        item_id: receiveItem.id,
        asset_id: assetId.trim(),
        received_at: new Date().toISOString(),
        note: receiveNote,
      });
      setReceiveItem(null);
      setAssetId("");
      setReceiveNote("");
      pushToast("Berkas diterima dan versi baru dicatat.", "success");
      await loadAll();
    } catch (err) {
      pushToast(getErrMsg(err, "Gagal mencatat penerimaan berkas."), "error");
    }
  };

  const handleReview = async () => {
    if (!activeExam || !reviewItem) return;
    try {
      await invokeBridge("exp.submissions.review", {
        institution_id: institutionId,
        exam_id: activeExam.id,
        item_id: reviewItem.id,
        new_state: reviewState,
        note: reviewNote,
      });
      setReviewItem(null);
      setReviewNote("");
      pushToast("Status tinjauan diperbarui.", "success");
      await loadAll();
    } catch (err) {
      pushToast(getErrMsg(err, "Gagal memperbarui status tinjauan."), "error");
    }
  };

  const handleComputePrint = async () => {
    if (!activeExam || !selectedPlanId) return;
    try {
      const res = await invokeBridge<{ computed_count: number }>(
        "exp.print.compute",
        {
          institution_id: institutionId,
          exam_id: activeExam.id,
          plan_id: selectedPlanId,
          reserve_per_room: reservePerRoom,
          exclude_cbt: excludeCbt,
        }
      );
      pushToast(`${res.computed_count} baris cetak dihitung.`, "success");
      await loadAll();
    } catch (err) {
      pushToast(getErrMsg(err, "Gagal menghitung jumlah cetak."), "error");
    }
  };

  const handleRecordHandover = async () => {
    if (!activeExam) return;
    try {
      const res = await invokeBridge<{ mismatch: boolean }>(
        "exp.handovers.record",
        {
          institution_id: institutionId,
          exam_id: activeExam.id,
          kind: "out",
          material_type: hoMaterial,
          expected_qty: hoExpected,
          actual_qty: hoActual,
          from_person_name: hoFrom,
          to_person_name: hoTo,
          handed_at: new Date().toISOString(),
        }
      );
      setShowHoModal(false);
      pushToast(
        res.mismatch
          ? "Serah terima dicatat dengan selisih jumlah."
          : "Serah terima dicatat.",
        res.mismatch ? "info" : "success"
      );
      await loadAll();
    } catch (err) {
      pushToast(getErrMsg(err, "Gagal mencatat serah terima."), "error");
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
          <div style={{ display: "flex", gap: 8 }}>
            <Button
              variant={tab === "matrix" ? "primary" : "secondary"}
              onClick={() => setTab("matrix")}
            >
              <Package size={16} aria-hidden="true" />
              Matriks Berkas ({detail?.counts.total ?? 0})
            </Button>
            <Button
              variant={tab === "print" ? "primary" : "secondary"}
              onClick={() => setTab("print")}
            >
              <Printer size={16} aria-hidden="true" />
              Jumlah Cetak
            </Button>
            <Button
              variant={tab === "handover" ? "primary" : "secondary"}
              onClick={() => setTab("handover")}
            >
              <ArrowLeftRight size={16} aria-hidden="true" />
              Serah Terima ({detail?.handovers.length ?? 0})
            </Button>
          </div>
          {detail && (
            <div style={{ display: "flex", gap: 8 }}>
              <StatusIndicator
                tone={detail.counts.missing > 0 ? "warning" : "success"}
                label={`Belum Masuk: ${detail.counts.missing}`}
              />
              <StatusIndicator
                tone={detail.counts.late > 0 ? "destructive" : "neutral"}
                label={`Terlambat: ${detail.counts.late}`}
              />
            </div>
          )}
        </div>
      </section>

      {!detail ? (
        <section className="uc-panel">
          <div className="uc-panel-body">
            <p className="uc-sub">
              {loading ? "Memuat data ekspedisi..." : "Tidak ada data."}
            </p>
          </div>
        </section>
      ) : tab === "matrix" ? (
        <section className="uc-panel">
          <div className="uc-panel-header">
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8, alignItems: "center" }}>
              <select
                className="uc-input"
                aria-label="Filter Status Berkas"
                value={filterState}
                onChange={(e) => setFilterState(e.target.value)}
              >
                <option value="">Semua Status</option>
                <option value="missing">Belum Masuk</option>
                <option value="received">Diterima</option>
                <option value="revision">Revisi</option>
                <option value="valid">Valid</option>
                <option value="ready">Siap Cetak</option>
              </select>
              <label style={{ display: "flex", gap: 6, alignItems: "center" }}>
                <input
                  type="checkbox"
                  checked={onlyLate}
                  onChange={(e) => setOnlyLate(e.target.checked)}
                />
                <span>Hanya terlambat</span>
              </label>
            </div>
            <div style={{ display: "flex", gap: 8 }}>
              <Button variant="secondary" size="sm" onClick={() => setShowItemModal(true)}>
                <Plus size={14} aria-hidden="true" />
                Item Kustom
              </Button>
              <Button variant="primary" size="sm" onClick={() => void handleGenerateMatrix()}>
                <Sparkles size={14} aria-hidden="true" />
                Generate Matriks
              </Button>
            </div>
          </div>
          <div className="uc-panel-body" style={{ overflowX: "auto" }}>
            <table className="uc-table" aria-label="Matriks Berkas Ujian">
              <thead>
                <tr>
                  <th>Mapel</th>
                  <th>Kelompok</th>
                  <th>Jenis</th>
                  <th>Versi</th>
                  <th>Status</th>
                  <th>Aksi</th>
                </tr>
              </thead>
              <tbody>
                {filteredItems.map((it) => (
                  <tr key={it.id}>
                    <td>{it.subject_label}</td>
                    <td>{it.class_label}</td>
                    <td>{it.type_code}</td>
                    <td>v{it.current_version}</td>
                    <td>
                      <StatusIndicator
                        tone={
                          it.state === "ready" || it.state === "valid"
                            ? "success"
                            : it.state === "missing"
                              ? "warning"
                              : "neutral"
                        }
                        label={it.state}
                      />
                    </td>
                    <td style={{ display: "flex", gap: 6 }}>
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => {
                          setReceiveItem(it);
                          setAssetId("");
                        }}
                      >
                        <FileUp size={14} aria-hidden="true" />
                        Terima
                      </Button>
                      <Button
                        variant="secondary"
                        size="sm"
                        disabled={it.state === "missing"}
                        onClick={() => {
                          setReviewItem(it);
                          setReviewState("valid");
                        }}
                      >
                        Tinjau
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ) : tab === "print" ? (
        <section className="uc-panel">
          <div className="uc-panel-header">
            <div style={{ display: "flex", flexWrap: "wrap", gap: 10, alignItems: "center" }}>
              <select
                className="uc-input"
                aria-label="Pilih Rencana Cetak"
                value={selectedPlanId}
                onChange={(e) => setSelectedPlanId(e.target.value)}
              >
                {plans.map((p) => (
                  <option key={p.id} value={p.id}>
                    v{p.version} ({p.state})
                  </option>
                ))}
              </select>
              <label style={{ display: "flex", gap: 6, alignItems: "center" }}>
                <span>Cadangan/Ruang:</span>
                <input
                  type="number"
                  min={0}
                  max={20}
                  className="uc-input"
                  style={{ width: 70 }}
                  value={reservePerRoom}
                  onChange={(e) => setReservePerRoom(Number(e.target.value))}
                />
              </label>
              <label style={{ display: "flex", gap: 6, alignItems: "center" }}>
                <input
                  type="checkbox"
                  checked={excludeCbt}
                  onChange={(e) => setExcludeCbt(e.target.checked)}
                />
                <span>Kecualikan CBT</span>
              </label>
            </div>
            <Button
              variant="primary"
              size="sm"
              disabled={!selectedPlanId}
              onClick={() => void handleComputePrint()}
            >
              Hitung Jumlah Cetak
            </Button>
          </div>
          <div className="uc-panel-body" style={{ overflowX: "auto" }}>
            <table className="uc-table" aria-label="Daftar Jumlah Cetak">
              <thead>
                <tr>
                  <th>ID Sesi Ruang</th>
                  <th>Roster</th>
                  <th>Cadangan</th>
                  <th>Total Efektif</th>
                </tr>
              </thead>
              <tbody>
                {detail.print_quantities.map((pq) => (
                  <tr key={pq.id}>
                    <td>{pq.room_session_id}</td>
                    <td>{pq.roster_count}</td>
                    <td>{pq.reserve_count}</td>
                    <td>
                      <strong>{pq.effective_qty}</strong>
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
            <h2>Catatan Serah Terima Bahan</h2>
            <Button variant="primary" size="sm" onClick={() => setShowHoModal(true)}>
              <Plus size={14} aria-hidden="true" />
              Catat Serah Terima
            </Button>
          </div>
          <div className="uc-panel-body" style={{ overflowX: "auto" }}>
            <table className="uc-table" aria-label="Daftar Serah Terima">
              <thead>
                <tr>
                  <th>Bahan</th>
                  <th>Dari → Ke</th>
                  <th>Target / Aktual</th>
                  <th>Selisih</th>
                </tr>
              </thead>
              <tbody>
                {detail.handovers.map((ho) => (
                  <tr key={ho.id}>
                    <td>{ho.material_type}</td>
                    <td>
                      {ho.from_person_name} → {ho.to_person_name}
                    </td>
                    <td>
                      {ho.expected_qty} / {ho.actual_qty}
                    </td>
                    <td>
                      <StatusIndicator
                        tone={ho.mismatch ? "destructive" : "success"}
                        label={ho.mismatch ? `Selisih ${ho.discrepancy}` : "Cocok"}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      <CRUDModal
        open={showItemModal}
        title="Tambah Item Ekspedisi Kustom"
        onClose={() => setShowItemModal(false)}
        onSubmit={() => void handleSaveCustomItem()}
      >
        <div style={{ display: "grid", gap: 12 }}>
          <label className="uc-field">
            <span className="uc-label">Mata Pelajaran</span>
            <input
              type="text"
              className="uc-input"
              value={itemSubj}
              onChange={(e) => setItemSubj(e.target.value)}
            />
          </label>
          <label className="uc-field">
            <span className="uc-label">Kelompok / Tingkat</span>
            <input
              type="text"
              className="uc-input"
              value={itemClass}
              onChange={(e) => setItemClass(e.target.value)}
            />
          </label>
          <label className="uc-field">
            <span className="uc-label">Jenis Dokumen</span>
            <input
              type="text"
              className="uc-input"
              value={itemType}
              onChange={(e) => setItemType(e.target.value)}
            />
          </label>
        </div>
      </CRUDModal>

      <CRUDModal
        open={receiveItem !== null}
        title={`Terima Berkas · ${receiveItem?.subject_label ?? ""}`}
        onClose={() => setReceiveItem(null)}
        onSubmit={() => void handleReceive()}
      >
        <div style={{ display: "grid", gap: 12 }}>
          <label className="uc-field">
            <span className="uc-label">Nama / Referensi Berkas</span>
            <input
              type="text"
              className="uc-input"
              value={assetId}
              onChange={(e) => setAssetId(e.target.value)}
            />
          </label>
          <label className="uc-field">
            <span className="uc-label">Catatan</span>
            <textarea
              rows={2}
              className="uc-input"
              value={receiveNote}
              onChange={(e) => setReceiveNote(e.target.value)}
            />
          </label>
        </div>
      </CRUDModal>

      <CRUDModal
        open={reviewItem !== null}
        title={`Tinjau Berkas · ${reviewItem?.subject_label ?? ""}`}
        onClose={() => setReviewItem(null)}
        onSubmit={() => void handleReview()}
      >
        <div style={{ display: "grid", gap: 12 }}>
          <label className="uc-field">
            <span className="uc-label">Status Baru</span>
            <select
              className="uc-input"
              value={reviewState}
              onChange={(e) =>
                setReviewState(
                  e.target.value as "received" | "revision" | "valid" | "ready"
                )
              }
            >
              <option value="revision">Perlu Revisi</option>
              <option value="valid">Valid</option>
              <option value="ready">Siap Cetak</option>
            </select>
          </label>
          <label className="uc-field">
            <span className="uc-label">Catatan Tinjauan</span>
            <textarea
              rows={2}
              className="uc-input"
              value={reviewNote}
              onChange={(e) => setReviewNote(e.target.value)}
            />
          </label>
        </div>
      </CRUDModal>

      <CRUDModal
        open={showHoModal}
        title="Catat Serah Terima Bahan"
        onClose={() => setShowHoModal(false)}
        onSubmit={() => void handleRecordHandover()}
      >
        <div style={{ display: "grid", gap: 12 }}>
          <label className="uc-field">
            <span className="uc-label">Jenis Bahan</span>
            <input
              type="text"
              className="uc-input"
              value={hoMaterial}
              onChange={(e) => setHoMaterial(e.target.value)}
            />
          </label>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
            <label className="uc-field">
              <span className="uc-label">Jumlah Target</span>
              <input
                type="number"
                min={0}
                className="uc-input"
                value={hoExpected}
                onChange={(e) => setHoExpected(Number(e.target.value))}
              />
            </label>
            <label className="uc-field">
              <span className="uc-label">Jumlah Aktual</span>
              <input
                type="number"
                min={0}
                className="uc-input"
                value={hoActual}
                onChange={(e) => setHoActual(Number(e.target.value))}
              />
            </label>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
            <label className="uc-field">
              <span className="uc-label">Penyerah</span>
              <input
                type="text"
                className="uc-input"
                value={hoFrom}
                onChange={(e) => setHoFrom(e.target.value)}
              />
            </label>
            <label className="uc-field">
              <span className="uc-label">Penerima</span>
              <input
                type="text"
                className="uc-input"
                value={hoTo}
                onChange={(e) => setHoTo(e.target.value)}
              />
            </label>
          </div>
        </div>
      </CRUDModal>
    </div>
  );
}
