import { useEffect, useState } from "react";
import { Calendar, CheckCircle2, Clock, DoorOpen, Users } from "lucide-react";
import { Button } from "../../components/ui/Button";
import {
  LoadingSkeleton,
  StatePanel,
  StatusIndicator,
} from "../../components/ui/Feedback";
import { invokeBridge } from "../../lib/bridge";
import type { ExamDashboardData, ExamItem } from "./types";

export interface DashboardPageProps {
  institutionId: string;
  activeExam: ExamItem | null;
  onNavigate: (route: string) => void;
}

export function DashboardPage({
  institutionId,
  activeExam,
  onNavigate,
}: DashboardPageProps) {
  const [data, setData] = useState<ExamDashboardData | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!activeExam) {
      setData(null);
      return;
    }
    let active = true;
    setLoading(true);
    invokeBridge<ExamDashboardData>("evt.exams.dashboard", {
      institution_id: institutionId,
      exam_id: activeExam.id,
    })
      .then((res) => {
        if (active) setData(res);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [institutionId, activeExam]);

  if (!activeExam) {
    return (
      <section className="uc-panel">
        <StatePanel
          kind="empty"
          title="Belum ada kegiatan ujian aktif"
          description="Buat kegiatan ujian baru untuk membekukan snapshot peserta, ruang, dan mulai menyusun jadwal."
          actionLabel="Buka Kegiatan Ujian"
          onAction={() => onNavigate("/events")}
        />
      </section>
    );
  }

  if (loading || !data) {
    return (
      <section className="uc-panel">
        <div className="uc-panel-body">
          <LoadingSkeleton rows={4} />
        </div>
      </section>
    );
  }

  return (
    <div style={{ display: "grid", gap: 16 }}>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
          gap: 12,
        }}
      >
        <section className="uc-panel">
          <div className="uc-panel-body">
            <div className="uc-sub" style={{ display: "flex", justifyContent: "space-between" }}>
              <span>Peserta Terdaftar</span>
              <Users size={16} aria-hidden="true" />
            </div>
            <strong style={{ fontSize: 26 }}>{data.counts.participants}</strong>
            <div className="uc-sub">{data.counts.numbered_participants} bernomor</div>
          </div>
        </section>

        <section className="uc-panel">
          <div className="uc-panel-body">
            <div className="uc-sub" style={{ display: "flex", justifyContent: "space-between" }}>
              <span>Ruang &amp; Kapasitas</span>
              <DoorOpen size={16} aria-hidden="true" />
            </div>
            <strong style={{ fontSize: 26 }}>{data.counts.rooms}</strong>
            <div className="uc-sub">{data.counts.total_capacity} kursi tersedia</div>
          </div>
        </section>

        <section className="uc-panel">
          <div className="uc-panel-body">
            <div className="uc-sub" style={{ display: "flex", justifyContent: "space-between" }}>
              <span>Pengawas Tersedia</span>
              <Users size={16} aria-hidden="true" />
            </div>
            <strong style={{ fontSize: 26 }}>{data.counts.staff}</strong>
            <div className="uc-sub">Snapshot staf aktif</div>
          </div>
        </section>

        <section className="uc-panel">
          <div className="uc-panel-body">
            <div className="uc-sub" style={{ display: "flex", justifyContent: "space-between" }}>
              <span>Kelompok &amp; Mapel</span>
              <Calendar size={16} aria-hidden="true" />
            </div>
            <strong style={{ fontSize: 26 }}>{data.counts.requirements}</strong>
            <div className="uc-sub">{data.counts.groups} kelompok ujian</div>
          </div>
        </section>
      </div>

      <section className="uc-panel">
        <div className="uc-panel-head">
          <h2>Kesiapan Pelaksanaan · {data.exam.title}</h2>
          <StatusIndicator
            label={data.exam.state}
            tone={data.blockers.length === 0 ? "success" : "warning"}
          />
        </div>
        <div className="uc-panel-body" style={{ display: "grid", gap: 10 }}>
          {data.checklist.map((item) => (
            <div
              key={item.id}
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                gap: 12,
                paddingBottom: 8,
                borderBottom: "1px solid var(--border)",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                {item.done ? (
                  <CheckCircle2 size={18} aria-hidden="true" style={{ color: "var(--success)" }} />
                ) : (
                  <Clock size={18} aria-hidden="true" style={{ color: "var(--warning)" }} />
                )}
                <div>
                  <strong>{item.label}</strong>
                  <div className="uc-sub">{item.detail}</div>
                </div>
              </div>
              <Button size="sm" onClick={() => onNavigate(item.route)}>
                Buka
              </Button>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
