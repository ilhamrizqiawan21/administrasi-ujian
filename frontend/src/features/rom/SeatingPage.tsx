import { useCallback, useEffect, useMemo, useState } from "react";
import { Layer, Rect, Stage, Text } from "react-konva";
import {
  CheckCircle2,
  Lock,
  Printer,
  Redo2,
  SlidersHorizontal,
  Sparkles,
  Undo2,
  Unlock,
  ZoomIn,
  ZoomOut,
} from "lucide-react";
import { Button } from "../../components/ui/Button";
import { StatusIndicator, useToast } from "../../components/ui/Feedback";
import { CRUDModal } from "../../components/ui/Modal";
import type { ExamItem } from "../evt/types";
import type { PlanItem } from "../ses/types";
import { invokeBridge } from "../../lib/bridge";
import type {
  AllocationPolicy,
  MixMode,
  SeatItem,
  SeatingDetail,
  SeatingPrintContext,
} from "./types";

interface SeatingPageProps {
  institutionId: string;
  activeExam: ExamItem | null;
}

interface SwapHistoryEntry {
  sourceSeatId: string;
  targetSeatId: string;
}

const DEFAULT_POLICY: AllocationPolicy = {
  mode: "mix_grade",
  hard_mix_grade: false,
  hard_mix_class: false,
  diagonal_adjacent: false,
  balance_rooms: true,
  respect_locks: true,
  require_accessible: true,
  soft_same_grade_weight: 10,
  soft_same_class_weight: 5,
};

function readCssToken(name: string, fallback: string): string {
  if (typeof window === "undefined" || typeof document === "undefined") {
    return fallback;
  }
  const val = getComputedStyle(document.documentElement)
    .getPropertyValue(name)
    .trim();
  return val || fallback;
}

function getErrMsg(err: unknown, fallback: string): string {
  return err instanceof Error ? err.message : fallback;
}

export function SeatingPage({ institutionId, activeExam }: SeatingPageProps) {
  const { pushToast } = useToast();
  const [plans, setPlans] = useState<PlanItem[]>([]);
  const [activePlanId, setActivePlanId] = useState<string>("");
  const [detail, setDetail] = useState<SeatingDetail | null>(null);
  const [activeRoomId, setActiveRoomId] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [solving, setSolving] = useState(false);
  const [solveReason, setSolveReason] = useState<string | null>(null);
  const [policy, setPolicy] = useState<AllocationPolicy>(DEFAULT_POLICY);

  // Canvas & interaction state
  const [zoom, setZoom] = useState(1);
  const [selectedSeatId, setSelectedSeatId] = useState<string | null>(null);
  const [undoStack, setUndoStack] = useState<SwapHistoryEntry[]>([]);
  const [redoStack, setRedoStack] = useState<SwapHistoryEntry[]>([]);

  // Room Layout Editor modal state (ROM-01)
  const [showLayoutModal, setShowLayoutModal] = useState(false);
  const [layoutRows, setLayoutRows] = useState(4);
  const [layoutCols, setLayoutCols] = useState(5);
  const [layoutSeatsPerDesk, setLayoutSeatsPerDesk] = useState(1);
  const [layoutCapacity, setLayoutCapacity] = useState(20);
  const [layoutBoardPos, setLayoutBoardPos] = useState<"top" | "bottom">("top");
  const [layoutDisabled, setLayoutDisabled] = useState("");
  const [layoutAccessible, setLayoutAccessible] = useState("");

  // Print preview modal state (ROM-08)
  const [printCtx, setPrintCtx] = useState<SeatingPrintContext | null>(null);
  const [includeNames, setIncludeNames] = useState(true);

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
        const data = await invokeBridge<SeatingDetail>("rom.seating.detail", {
          institution_id: institutionId,
          exam_id: activeExam.id,
          plan_id: planId,
        });
        setDetail(data);
        setActiveRoomId((prev) =>
          data.rooms.some((r) => r.id === prev)
            ? prev
            : (data.rooms[0]?.id ?? "")
        );
      } catch (err) {
        pushToast(getErrMsg(err, "Gagal memuat denah ruang."), "error");
      } finally {
        setLoading(false);
      }
    },
    [institutionId, activeExam, pushToast]
  );

  useEffect(() => {
    void loadPlans();
  }, [loadPlans]);

  useEffect(() => {
    if (activePlanId) {
      void loadDetail(activePlanId);
      setSelectedSeatId(null);
      setUndoStack([]);
      setRedoStack([]);
      setSolveReason(null);
    }
  }, [activePlanId, loadDetail]);

  const activeRoom = useMemo(
    () => detail?.rooms.find((r) => r.id === activeRoomId) ?? null,
    [detail, activeRoomId]
  );

  const roomSeats = useMemo(
    () =>
      (detail?.seats ?? []).filter((s) => s.exam_room_id === activeRoomId),
    [detail, activeRoomId]
  );

  const isReadOnly =
    detail?.plan_state === "published" || detail?.plan_state === "superseded";

  const handleOpenLayoutEditor = () => {
    if (!activeRoom) return;
    const disabled = roomSeats
      .filter((s) => s.enabled === 0)
      .map((s) => s.seat_code);
    const accessible = roomSeats
      .filter((s) => s.accessible === 1)
      .map((s) => s.seat_code);
    setLayoutRows(activeRoom.rows);
    setLayoutCols(activeRoom.cols);
    setLayoutSeatsPerDesk(activeRoom.seats_per_desk);
    setLayoutCapacity(activeRoom.capacity_limit);
    setLayoutBoardPos(activeRoom.board_position);
    setLayoutDisabled(disabled.join(", "));
    setLayoutAccessible(accessible.join(", "));
    setShowLayoutModal(true);
  };

  const handleSaveLayout = async () => {
    if (!activeExam || !activePlanId || !activeRoom) return;
    const disabledList = layoutDisabled
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
    const accessibleList = layoutAccessible
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);

    try {
      await invokeBridge<{ room_id: string; plan_revision: number }>(
        "rom.rooms.update_layout",
        {
          institution_id: institutionId,
          exam_id: activeExam.id,
          plan_id: activePlanId,
          exam_room_id: activeRoom.id,
          rows: layoutRows,
          cols: layoutCols,
          seats_per_desk: layoutSeatsPerDesk,
          capacity_limit: layoutCapacity,
          disabled_cells: disabledList,
          accessible_seats: accessibleList,
          board_position: layoutBoardPos,
        }
      );
      setShowLayoutModal(false);
      pushToast("Tata letak ruang diperbarui.", "success");
      await loadDetail(activePlanId);
    } catch (err) {
      pushToast(getErrMsg(err, "Gagal menyimpan tata letak ruang."), "error");
    }
  };

  const handleSolve = async () => {
    if (!activeExam || !detail) return;
    setSolving(true);
    setSolveReason(null);
    try {
      const data = await invokeBridge<{
        ok: boolean;
        status: string;
        diagnostics?: { reason?: string };
      }>("rom.seating.solve", {
        institution_id: institutionId,
        exam_id: activeExam.id,
        plan_id: detail.plan_id,
        expected_revision: detail.plan_revision,
        policy,
      });
      if (!data.ok) {
        setSolveReason(
          data.diagnostics?.reason ??
            "Alokasi otomatis tidak menemukan solusi valid."
        );
        pushToast("Alokasi otomatis tidak memenuhi aturan keras.", "error");
        return;
      }
      setUndoStack([]);
      setRedoStack([]);
      setSelectedSeatId(null);
      pushToast("Alokasi denah kursi selesai.", "success");
      await loadDetail(detail.plan_id);
    } catch (err) {
      pushToast(getErrMsg(err, "Gagal menjalankan solver kursi."), "error");
    } finally {
      setSolving(false);
    }
  };

  const performSwap = async (
    sourceId: string,
    targetId: string,
    recordMode: "push" | "undo" | "redo"
  ) => {
    if (!activeExam || !detail) return;
    try {
      await invokeBridge<{ plan_revision: number }>("rom.seats.swap", {
        institution_id: institutionId,
        exam_id: activeExam.id,
        plan_id: detail.plan_id,
        expected_revision: detail.plan_revision,
        source_seat_id: sourceId,
        target_seat_id: targetId,
        policy,
      });
      if (recordMode === "push") {
        setUndoStack((prev) => [
          ...prev,
          { sourceSeatId: sourceId, targetSeatId: targetId },
        ]);
        setRedoStack([]);
      } else if (recordMode === "undo") {
        setUndoStack((prev) => prev.slice(0, -1));
        setRedoStack((prev) => [
          ...prev,
          { sourceSeatId: sourceId, targetSeatId: targetId },
        ]);
      } else if (recordMode === "redo") {
        setRedoStack((prev) => prev.slice(0, -1));
        setUndoStack((prev) => [
          ...prev,
          { sourceSeatId: sourceId, targetSeatId: targetId },
        ]);
      }
      setSelectedSeatId(null);
      await loadDetail(detail.plan_id);
    } catch (err) {
      pushToast(getErrMsg(err, "Gagal menukar posisi kursi."), "error");
      setSelectedSeatId(null);
    }
  };

  const handleSeatAction = (seat: SeatItem) => {
    if (isReadOnly || seat.enabled === 0) return;
    if (!selectedSeatId) {
      setSelectedSeatId(seat.id);
      return;
    }
    if (selectedSeatId === seat.id) {
      setSelectedSeatId(null);
      return;
    }
    void performSwap(selectedSeatId, seat.id, "push");
  };

  const handleToggleLock = async (seat: SeatItem) => {
    if (!activeExam || !detail || isReadOnly || !seat.participant) return;
    try {
      const data = await invokeBridge<{ locked: boolean }>("rom.seats.lock", {
        institution_id: institutionId,
        exam_id: activeExam.id,
        plan_id: detail.plan_id,
        seat_id: seat.id,
        locked: !seat.locked,
      });
      pushToast(
        data.locked ? "Kursi dikunci." : "Kunci kursi dibuka.",
        "info"
      );
      await loadDetail(detail.plan_id);
    } catch (err) {
      pushToast(getErrMsg(err, "Gagal mengubah kunci kursi."), "error");
    }
  };

  const handlePublish = async () => {
    if (!activeExam || !detail) return;
    try {
      await invokeBridge<{ plan: PlanItem }>("ses.plans.publish", {
        institution_id: institutionId,
        exam_id: activeExam.id,
        plan_id: detail.plan_id,
        expected_revision: detail.plan_revision,
      });
      pushToast("Versi rencana & denah diterbitkan.", "success");
      await loadPlans();
      await loadDetail(detail.plan_id);
    } catch (err) {
      pushToast(getErrMsg(err, "Gagal menerbitkan rencana."), "error");
    }
  };

  const handleOpenPrintPreview = async (withNames: boolean) => {
    if (!activeExam || !detail || !activeRoom) return;
    try {
      const data = await invokeBridge<SeatingPrintContext>(
        "rom.seating.print_context",
        {
          institution_id: institutionId,
          exam_id: activeExam.id,
          plan_id: detail.plan_id,
          exam_room_id: activeRoom.id,
          include_names: withNames,
        }
      );
      setPrintCtx(data);
    } catch (err) {
      pushToast(getErrMsg(err, "Gagal memuat pratinjau cetak."), "error");
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

  // Konva canvas sizing & theme tokens
  const tileW = 136;
  const tileH = 68;
  const gapX = 14;
  const gapY = 14;
  const pad = 20;
  const stageW = activeRoom
    ? pad * 2 +
      activeRoom.cols *
        (activeRoom.seats_per_desk * tileW +
          (activeRoom.seats_per_desk - 1) * 6 +
          gapX)
    : 500;
  const stageH = activeRoom
    ? pad * 2 + activeRoom.rows * (tileH + gapY) + 44
    : 300;

  const surfaceBg = readCssToken("--bg-elevated", "#ffffff");
  const disabledBg = readCssToken("--bg-muted", "#eef2f6");
  const accentColor = readCssToken("--accent-primary", "#0f766e");
  const borderSubtle = readCssToken("--border-subtle", "#cbd5e1");
  const textPrimary = readCssToken("--text-primary", "#0f172a");
  const textMuted = readCssToken("--text-secondary", "#475569");
  const warnBg = readCssToken("--status-warning-bg", "#fef3c7");
  const warnBorder = readCssToken("--status-warning-text", "#b45309");

  return (
    <div style={{ display: "grid", gap: "var(--space-4)" }}>
      {/* Top Toolbar: Plan switcher + actions */}
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
          <div
            style={{
              display: "flex",
              flexWrap: "wrap",
              gap: "var(--space-3)",
              alignItems: "center",
            }}
          >
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
                      : "Perlu Penyesuaian"
                }
              />
            )}
          </div>

          <div
            style={{ display: "flex", flexWrap: "wrap", gap: "var(--space-2)" }}
          >
            <Button
              variant="secondary"
              disabled={!detail || isReadOnly || undoStack.length === 0}
              onClick={() => {
                const last = undoStack[undoStack.length - 1];
                if (last)
                  void performSwap(last.targetSeatId, last.sourceSeatId, "undo");
              }}
            >
              <Undo2 size={16} aria-hidden="true" />
              Urungkan
            </Button>
            <Button
              variant="secondary"
              disabled={!detail || isReadOnly || redoStack.length === 0}
              onClick={() => {
                const next = redoStack[redoStack.length - 1];
                if (next)
                  void performSwap(next.sourceSeatId, next.targetSeatId, "redo");
              }}
            >
              <Redo2 size={16} aria-hidden="true" />
              Ulangi
            </Button>
            <Button
              variant="secondary"
              disabled={!activeRoom || !detail}
              onClick={() => void handleOpenPrintPreview(includeNames)}
            >
              <Printer size={16} aria-hidden="true" />
              Pratinjau Cetak
            </Button>
            <Button
              variant="primary"
              disabled={!detail || isReadOnly || solving}
              onClick={() => void handleSolve()}
            >
              <Sparkles size={16} aria-hidden="true" />
              {solving ? "Mengalokasi..." : "Alokasi Otomatis"}
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
                ? "Memuat denah ruang..."
                : "Buat draf rencana terlebih dahulu di menu Jadwal Ujian."}
            </p>
          </div>
        </section>
      ) : (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "minmax(240px, 280px) minmax(0, 1fr)",
            gap: "var(--space-4)",
            alignItems: "start",
          }}
        >
          {/* Left Column: UIX-27 RoomList + Policy & Diagnostics */}
          <div style={{ display: "grid", gap: "var(--space-4)" }}>
            <section className="uc-panel" aria-label="Daftar Ruang Ujian">
              <div className="uc-panel-header">
                <h2>Daftar Ruang</h2>
                <Button
                  variant="secondary"
                  size="sm"
                  disabled={!activeRoom || isReadOnly}
                  onClick={handleOpenLayoutEditor}
                >
                  <SlidersHorizontal size={14} aria-hidden="true" />
                  Atur Grid
                </Button>
              </div>
              <div className="uc-panel-body" style={{ display: "grid", gap: 8 }}>
                {detail.rooms.map((rm) => {
                  const occupied = detail.seats.filter(
                    (s) => s.exam_room_id === rm.id && s.participant !== null
                  ).length;
                  const active = rm.id === activeRoomId;
                  return (
                    <button
                      key={rm.id}
                      type="button"
                      className={
                        active ? "uc-btn uc-btn-primary" : "uc-btn uc-btn-secondary"
                      }
                      style={{
                        justifyContent: "space-between",
                        width: "100%",
                        textAlign: "left",
                      }}
                      onClick={() => {
                        setActiveRoomId(rm.id);
                        setSelectedSeatId(null);
                      }}
                    >
                      <span>
                        {rm.code} · {rm.name}
                      </span>
                      <span>
                        {occupied}/{rm.capacity_limit}
                      </span>
                    </button>
                  );
                })}
              </div>
            </section>

            <section className="uc-panel" aria-label="Kebijakan Alokasi">
              <div className="uc-panel-header">
                <h2>Kebijakan Alokasi</h2>
              </div>
              <div className="uc-panel-body" style={{ display: "grid", gap: 10 }}>
                <label className="uc-field">
                  <span className="uc-label">Mode Acak</span>
                  <select
                    className="uc-input"
                    value={policy.mode}
                    disabled={isReadOnly}
                    onChange={(e) =>
                      setPolicy((p) => ({
                        ...p,
                        mode: e.target.value as MixMode,
                      }))
                    }
                  >
                    <option value="mix_grade">Campur Tingkat</option>
                    <option value="mix_class">Campur Rombel</option>
                    <option value="ordered">Berurutan Nomor</option>
                    <option value="custom">Kustom</option>
                  </select>
                </label>

                <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
                  <input
                    type="checkbox"
                    checked={policy.hard_mix_grade}
                    disabled={isReadOnly}
                    onChange={(e) =>
                      setPolicy((p) => ({
                        ...p,
                        hard_mix_grade: e.target.checked,
                      }))
                    }
                  />
                  <span>Wajib pisah tingkat (aturan keras)</span>
                </label>

                <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
                  <input
                    type="checkbox"
                    checked={policy.hard_mix_class}
                    disabled={isReadOnly}
                    onChange={(e) =>
                      setPolicy((p) => ({
                        ...p,
                        hard_mix_class: e.target.checked,
                      }))
                    }
                  />
                  <span>Wajib pisah rombel (aturan keras)</span>
                </label>

                <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
                  <input
                    type="checkbox"
                    checked={policy.require_accessible}
                    disabled={isReadOnly}
                    onChange={(e) =>
                      setPolicy((p) => ({
                        ...p,
                        require_accessible: e.target.checked,
                      }))
                    }
                  />
                  <span>Prioritas kursi aksesibel</span>
                </label>

                <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
                  <input
                    type="checkbox"
                    checked={policy.diagonal_adjacent}
                    disabled={isReadOnly}
                    onChange={(e) =>
                      setPolicy((p) => ({
                        ...p,
                        diagonal_adjacent: e.target.checked,
                      }))
                    }
                  />
                  <span>Hitung tetangga diagonal</span>
                </label>
              </div>
            </section>

            <section className="uc-panel" aria-label="Diagnostik Alokasi">
              <div className="uc-panel-header">
                <h2>Diagnostik</h2>
              </div>
              <div className="uc-panel-body" style={{ display: "grid", gap: 6 }}>
                <div>
                  Terisi:{" "}
                  <strong>
                    {detail.validation.diagnostics.total_seated} /{" "}
                    {detail.validation.diagnostics.total_eligible}
                  </strong>
                </div>
                <div>
                  Kekurangan kapasitas:{" "}
                  <strong>
                    {detail.validation.diagnostics.capacity_shortfall}
                  </strong>
                </div>
                <div>
                  Bersebelahan tingkat sama:{" "}
                  <strong>
                    {detail.validation.diagnostics.same_grade_adjacent}
                  </strong>
                </div>
                <div>
                  Bersebelahan rombel sama:{" "}
                  <strong>
                    {detail.validation.diagnostics.same_class_adjacent}
                  </strong>
                </div>
                <div>
                  Konflik akomodasi:{" "}
                  <strong>
                    {detail.validation.diagnostics.accommodation_conflicts}
                  </strong>
                </div>

                {solveReason && (
                  <p className="uc-field-error" role="alert">
                    {solveReason}
                  </p>
                )}

                {detail.validation.hard_conflicts.map((hc, i) => (
                  <p
                    key={`${hc.code}-${i}`}
                    className="uc-field-error"
                    role="alert"
                  >
                    {hc.message}
                  </p>
                ))}
              </div>
            </section>
          </div>

          {/* Right Column: UIX-28 Konva SeatCanvas + Accessible Table */}
          <div style={{ display: "grid", gap: "var(--space-4)" }}>
            <section className="uc-panel">
              <div className="uc-panel-header">
                <div>
                  <h2>
                    Denah {activeRoom?.code ?? ""} · {activeRoom?.name ?? ""}
                  </h2>
                  <p className="uc-sub">
                    {selectedSeatId
                      ? "Pilih kursi tujuan untuk menukar posisi."
                      : "Klik dua kursi pada kanvas atau gunakan tabel di bawah untuk menukar posisi."}
                  </p>
                </div>
                <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
                  <Button
                    variant="secondary"
                    size="sm"
                    aria-label="Perkecil kanvas"
                    onClick={() =>
                      setZoom((z) => Math.max(0.6, +(z - 0.1).toFixed(2)))
                    }
                  >
                    <ZoomOut size={14} aria-hidden="true" />
                  </Button>
                  <span style={{ minWidth: 48, textAlign: "center" }}>
                    {Math.round(zoom * 100)}%
                  </span>
                  <Button
                    variant="secondary"
                    size="sm"
                    aria-label="Perbesar kanvas"
                    onClick={() =>
                      setZoom((z) => Math.min(1.6, +(z + 0.1).toFixed(2)))
                    }
                  >
                    <ZoomIn size={14} aria-hidden="true" />
                  </Button>
                </div>
              </div>

              <div
                className="uc-panel-body"
                style={{ overflowX: "auto", paddingBottom: "var(--space-4)" }}
              >
                {activeRoom && (
                  <Stage
                    width={stageW * zoom}
                    height={stageH * zoom}
                    scaleX={zoom}
                    scaleY={zoom}
                  >
                    <Layer>
                      {/* Board orientation indicator */}
                      <Rect
                        x={pad}
                        y={
                          activeRoom.board_position === "top" ? 10 : stageH - 34
                        }
                        width={Math.max(200, stageW - pad * 2)}
                        height={24}
                        cornerRadius={6}
                        fill={disabledBg}
                        stroke={borderSubtle}
                        strokeWidth={1}
                      />
                      <Text
                        x={pad}
                        y={
                          activeRoom.board_position === "top" ? 16 : stageH - 28
                        }
                        width={Math.max(200, stageW - pad * 2)}
                        align="center"
                        text="PAPAN TULIS / PENGAWAS"
                        fontSize={11}
                        fontStyle="bold"
                        fill={textMuted}
                      />

                      {roomSeats.map((seat) => {
                        const topOffset =
                          activeRoom.board_position === "top" ? 44 : 10;
                        const deskBlockW =
                          activeRoom.seats_per_desk * tileW +
                          (activeRoom.seats_per_desk - 1) * 6 +
                          gapX;
                        const x =
                          pad +
                          (seat.desk_col - 1) * deskBlockW +
                          (seat.seat_index - 1) * (tileW + 6);
                        const y =
                          topOffset + (seat.desk_row - 1) * (tileH + gapY);

                        const isSelected = selectedSeatId === seat.id;
                        const isDisabled = seat.enabled === 0;
                        const hasPart = seat.participant !== null;
                        const bgFill = isDisabled
                          ? disabledBg
                          : isSelected
                            ? warnBg
                            : surfaceBg;
                        const strokeColor = isSelected
                          ? warnBorder
                          : hasPart
                            ? accentColor
                            : borderSubtle;

                        return (
                          <Rect
                            key={`rect-${seat.id}`}
                            x={x}
                            y={y}
                            width={tileW}
                            height={tileH}
                            cornerRadius={8}
                            fill={bgFill}
                            stroke={strokeColor}
                            strokeWidth={isSelected ? 2.5 : 1.5}
                            onClick={() => handleSeatAction(seat)}
                            onTap={() => handleSeatAction(seat)}
                          />
                        );
                      })}

                      {roomSeats.map((seat) => {
                        const topOffset =
                          activeRoom.board_position === "top" ? 44 : 10;
                        const deskBlockW =
                          activeRoom.seats_per_desk * tileW +
                          (activeRoom.seats_per_desk - 1) * 6 +
                          gapX;
                        const x =
                          pad +
                          (seat.desk_col - 1) * deskBlockW +
                          (seat.seat_index - 1) * (tileW + 6);
                        const y =
                          topOffset + (seat.desk_row - 1) * (tileH + gapY);

                        const markers = [
                          seat.accessible ? "[A]" : "",
                          seat.locked ? "[K]" : "",
                        ]
                          .filter(Boolean)
                          .join(" ");

                        const primaryLine =
                          seat.enabled === 0
                            ? "Nonaktif"
                            : seat.participant
                              ? seat.participant.display_name
                              : "Kosong";
                        const secondaryLine =
                          seat.enabled === 0
                            ? ""
                            : seat.participant
                              ? `${seat.participant.participant_number ?? "-"} · ${seat.participant.level_label}/${seat.participant.class_label}`
                              : "Siap diisi";

                        return (
                          <Text
                            key={`txt-${seat.id}`}
                            x={x + 8}
                            y={y + 8}
                            width={tileW - 16}
                            height={tileH - 12}
                            text={`${seat.seat_code} ${markers}\n${primaryLine}\n${secondaryLine}`}
                            fontSize={11}
                            lineHeight={1.35}
                            fill={seat.enabled === 0 ? textMuted : textPrimary}
                            listening={false}
                          />
                        );
                      })}
                    </Layer>
                  </Stage>
                )}
              </div>
            </section>

            {/* ROM-06 Accessible keyboard/table alternate */}
            <section className="uc-panel">
              <div className="uc-panel-header">
                <h2>Daftar Kursi (Akses Keyboard)</h2>
              </div>
              <div className="uc-panel-body" style={{ overflowX: "auto" }}>
                <table className="uc-table" aria-label="Daftar Kursi Ruang">
                  <thead>
                    <tr>
                      <th>Kursi</th>
                      <th>Peserta</th>
                      <th>Tingkat / Rombel</th>
                      <th>Status</th>
                      <th>Aksi</th>
                    </tr>
                  </thead>
                  <tbody>
                    {roomSeats.map((seat) => {
                      const isSelected = selectedSeatId === seat.id;
                      return (
                        <tr key={seat.id}>
                          <td>
                            <strong>{seat.seat_code}</strong>{" "}
                            {seat.accessible ? <span>[Aksesibel]</span> : null}
                          </td>
                          <td>
                            {seat.enabled === 0
                              ? "Nonaktif"
                              : seat.participant
                                ? `${seat.participant.display_name} (${seat.participant.participant_number ?? "-"})`
                                : "Kosong"}
                          </td>
                          <td>
                            {seat.participant
                              ? `${seat.participant.level_label} / ${seat.participant.class_label}`
                              : "-"}
                          </td>
                          <td>
                            {seat.locked
                              ? "Terkunci"
                              : seat.enabled
                                ? "Aktif"
                                : "Nonaktif"}
                          </td>
                          <td style={{ display: "flex", gap: 6 }}>
                            <Button
                              variant={isSelected ? "primary" : "secondary"}
                              size="sm"
                              disabled={isReadOnly || seat.enabled === 0}
                              onClick={() => handleSeatAction(seat)}
                            >
                              {isSelected
                                ? "Batal Pilih"
                                : selectedSeatId
                                  ? "Pindah ke Sini"
                                  : "Tukar"}
                            </Button>
                            {seat.participant && (
                              <Button
                                variant="secondary"
                                size="sm"
                                disabled={isReadOnly}
                                aria-label={
                                  seat.locked
                                    ? `Buka kunci ${seat.seat_code}`
                                    : `Kunci ${seat.seat_code}`
                                }
                                onClick={() => void handleToggleLock(seat)}
                              >
                                {seat.locked ? (
                                  <Unlock size={14} aria-hidden="true" />
                                ) : (
                                  <Lock size={14} aria-hidden="true" />
                                )}
                              </Button>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </section>
          </div>
        </div>
      )}

      {/* ROM-01 Room Layout Editor Modal */}
      <CRUDModal
        open={showLayoutModal}
        title={`Atur Tata Letak ${activeRoom?.code ?? ""}`}
        onClose={() => setShowLayoutModal(false)}
        onSubmit={() => void handleSaveLayout()}
        submitLabel="Simpan Tata Letak"
      >
        <div style={{ display: "grid", gap: 12 }}>
          <div
            style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}
          >
            <label className="uc-field">
              <span className="uc-label">Baris</span>
              <input
                type="number"
                min={1}
                max={30}
                className="uc-input"
                value={layoutRows}
                onChange={(e) => setLayoutRows(Number(e.target.value))}
              />
            </label>
            <label className="uc-field">
              <span className="uc-label">Kolom</span>
              <input
                type="number"
                min={1}
                max={30}
                className="uc-input"
                value={layoutCols}
                onChange={(e) => setLayoutCols(Number(e.target.value))}
              />
            </label>
          </div>

          <div
            style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}
          >
            <label className="uc-field">
              <span className="uc-label">Kursi per Meja</span>
              <select
                className="uc-input"
                value={layoutSeatsPerDesk}
                onChange={(e) => setLayoutSeatsPerDesk(Number(e.target.value))}
              >
                <option value={1}>1 Kursi / Meja</option>
                <option value={2}>2 Kursi / Meja</option>
              </select>
            </label>
            <label className="uc-field">
              <span className="uc-label">Batas Kapasitas</span>
              <input
                type="number"
                min={1}
                max={1000}
                className="uc-input"
                value={layoutCapacity}
                onChange={(e) => setLayoutCapacity(Number(e.target.value))}
              />
            </label>
          </div>

          <label className="uc-field">
            <span className="uc-label">Posisi Papan Tulis</span>
            <select
              className="uc-input"
              value={layoutBoardPos}
              onChange={(e) =>
                setLayoutBoardPos(e.target.value as "top" | "bottom")
              }
            >
              <option value="top">Atas (Depan)</option>
              <option value="bottom">Bawah (Belakang)</option>
            </select>
          </label>

          <label className="uc-field">
            <span className="uc-label">
              Sel Nonaktif (pisahkan koma, mis. R2C3)
            </span>
            <input
              type="text"
              className="uc-input"
              value={layoutDisabled}
              onChange={(e) => setLayoutDisabled(e.target.value)}
            />
          </label>

          <label className="uc-field">
            <span className="uc-label">
              Kursi Aksesibel (pisahkan koma, mis. R1C1S1)
            </span>
            <input
              type="text"
              className="uc-input"
              value={layoutAccessible}
              onChange={(e) => setLayoutAccessible(e.target.value)}
            />
          </label>
        </div>
      </CRUDModal>

      {/* ROM-08 Print Preview Modal */}
      <CRUDModal
        open={printCtx !== null}
        title={
          printCtx
            ? `Pratinjau Denah ${printCtx.room_code} · v${printCtx.plan_version}`
            : "Pratinjau Denah"
        }
        onClose={() => setPrintCtx(null)}
        onSubmit={() => window.print()}
        submitLabel="Cetak"
        cancelLabel="Tutup"
      >
        {printCtx && (
          <div style={{ display: "grid", gap: 10 }}>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                gap: 8,
              }}
            >
              <p className="uc-sub">
                {printCtx.exam_title} · {printCtx.room_name} (
                {printCtx.plan_state}) · Papan:{" "}
                {printCtx.board_position === "top" ? "Atas" : "Bawah"}
              </p>
              <label style={{ display: "flex", gap: 6, alignItems: "center" }}>
                <input
                  type="checkbox"
                  checked={includeNames}
                  onChange={(e) => {
                    const checked = e.target.checked;
                    setIncludeNames(checked);
                    void handleOpenPrintPreview(checked);
                  }}
                />
                <span>Tampilkan nama</span>
              </label>
            </div>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: `repeat(${printCtx.cols}, minmax(0, 1fr))`,
                gap: 8,
              }}
            >
              {printCtx.desks.map((d) => (
                <div
                  key={d.seat_code}
                  style={{
                    border: "1px solid var(--border-subtle)",
                    borderRadius: 6,
                    padding: 8,
                    fontSize: 12,
                  }}
                >
                  <div>
                    <strong>{d.seat_code}</strong> {d.accessible ? "[A]" : ""}
                  </div>
                  <div>
                    {d.enabled ? (d.participant_number ?? "Kosong") : "Nonaktif"}
                  </div>
                  {d.display_name && <div>{d.display_name}</div>}
                </div>
              ))}
            </div>
          </div>
        )}
      </CRUDModal>
    </div>
  );
}
