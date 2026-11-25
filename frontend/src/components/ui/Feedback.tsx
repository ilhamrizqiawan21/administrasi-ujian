import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { AlertCircle, CheckCircle2, Inbox, Lock, X } from "lucide-react";
import { Button, IconButton } from "./Button";

export interface ToastItem {
  id: string;
  message: string;
  kind: "success" | "error" | "info";
}

interface ToastContextValue {
  pushToast: (message: string, kind?: ToastItem["kind"]) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const dismiss = useCallback((id: string) => {
    setToasts((prev) => prev.filter((item) => item.id !== id));
  }, []);

  const pushToast = useCallback(
    (message: string, kind: ToastItem["kind"] = "info") => {
      const id = `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
      setToasts((prev) => [...prev.slice(-3), { id, message, kind }]);
      window.setTimeout(() => dismiss(id), 4000);
    },
    [dismiss]
  );

  const value = useMemo(() => ({ pushToast }), [pushToast]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div
        className="uc-toast-region"
        aria-live="polite"
        aria-relevant="additions"
      >
        {toasts.map((toast) => (
          <div key={toast.id} className="uc-toast" role="status">
            {toast.kind === "success" ? (
              <CheckCircle2 size={16} aria-hidden="true" />
            ) : (
              <AlertCircle size={16} aria-hidden="true" />
            )}
            <span>{toast.message}</span>
            <IconButton
              label="Tutup notifikasi"
              icon={<X size={14} aria-hidden="true" />}
              onClick={() => dismiss(toast.id)}
            />
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) {
    throw new Error("useToast harus dipanggil di dalam ToastProvider.");
  }
  return ctx;
}

export type StatusTone = "success" | "warning" | "destructive" | "neutral";

export function StatusIndicator({
  label,
  tone = "neutral",
}: {
  label: string;
  tone?: StatusTone;
}) {
  return (
    <span className={`uc-status uc-status-${tone}`}>
      <span className="uc-status-dot" aria-hidden="true" />
      <span>{label}</span>
    </span>
  );
}

export function ProgressBar({
  current,
  total,
  label,
}: {
  current: number;
  total: number;
  label?: string;
}) {
  const pct = total > 0 ? Math.min(100, Math.round((current / total) * 100)) : 0;
  return (
    <div>
      {label && (
        <div className="uc-sub" style={{ marginBottom: 4 }}>
          {label}: {total > 0 ? `${current} / ${total} (${pct}%)` : "N/A"}
        </div>
      )}
      <div
        className="uc-progress-track"
        role="progressbar"
        aria-valuenow={total > 0 ? pct : undefined}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuetext={total > 0 ? `${pct}%` : "N/A"}
      >
        <div className="uc-progress-fill" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

export function LoadingSkeleton({ rows = 3 }: { rows?: number }) {
  return (
    <div style={{ display: "grid", gap: 10 }} aria-busy="true">
      {Array.from({ length: rows }, (_, i) => (
        <div
          key={i}
          className="uc-skeleton"
          style={{ width: i === rows - 1 ? "65%" : "100%" }}
        />
      ))}
    </div>
  );
}

export function StatePanel({
  kind,
  title,
  description,
  actionLabel,
  onAction,
}: {
  kind: "empty" | "error" | "permission" | "disabled";
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
}) {
  const icon =
    kind === "permission" || kind === "disabled" ? (
      <Lock size={24} aria-hidden="true" />
    ) : kind === "error" ? (
      <AlertCircle size={24} aria-hidden="true" />
    ) : (
      <Inbox size={24} aria-hidden="true" />
    );

  return (
    <div className="uc-state-panel" role={kind === "error" ? "alert" : "status"}>
      {icon}
      <strong>{title}</strong>
      <p className="uc-sub">{description}</p>
      {actionLabel && onAction && (
        <Button variant="secondary" size="sm" onClick={onAction}>
          {actionLabel}
        </Button>
      )}
    </div>
  );
}
