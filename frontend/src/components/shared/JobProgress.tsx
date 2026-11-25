import { RotateCcw, XCircle } from "lucide-react";
import { Button } from "../ui/Button";
import { ProgressBar, StatusIndicator, type StatusTone } from "../ui/Feedback";

export type JobState =
  | "queued"
  | "running"
  | "succeeded"
  | "failed"
  | "cancelled"
  | "interrupted";

export interface JobProgressProps {
  title: string;
  status: JobState;
  phase: string;
  current: number;
  total: number;
  errorMessage?: string | null;
  onCancel?: () => void;
  onRetry?: () => void;
}

function mapTone(status: JobState): StatusTone {
  switch (status) {
    case "succeeded":
      return "success";
    case "failed":
    case "interrupted":
      return "destructive";
    case "cancelled":
      return "neutral";
    default:
      return "warning";
  }
}

export function JobProgress({
  title,
  status,
  phase,
  current,
  total,
  errorMessage,
  onCancel,
  onRetry,
}: JobProgressProps) {
  const isActive = status === "queued" || status === "running";
  const canRetry =
    status === "failed" || status === "cancelled" || status === "interrupted";

  return (
    <section className="uc-panel" aria-live="polite">
      <div className="uc-panel-head">
        <h2>{title}</h2>
        <StatusIndicator label={phase} tone={mapTone(status)} />
      </div>
      <div className="uc-panel-body" style={{ display: "grid", gap: 12 }}>
        <ProgressBar current={current} total={total} label="Progres" />
        {errorMessage && (
          <p className="uc-field-error" role="alert">
            {errorMessage}
          </p>
        )}
        <div className="uc-actions">
          {isActive && onCancel && (
            <Button variant="destructive" size="sm" onClick={onCancel}>
              <XCircle size={14} aria-hidden="true" />
              Batalkan
            </Button>
          )}
          {canRetry && onRetry && (
            <Button variant="secondary" size="sm" onClick={onRetry}>
              <RotateCcw size={14} aria-hidden="true" />
              Coba Lagi
            </Button>
          )}
        </div>
      </div>
    </section>
  );
}
