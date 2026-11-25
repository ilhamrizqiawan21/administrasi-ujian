import {
  useEffect,
  useId,
  useRef,
  type ReactNode,
} from "react";
import { AlertTriangle, X } from "lucide-react";
import { Button, IconButton } from "./Button";

function getFocusableElements(container: HTMLElement): HTMLElement[] {
  const selector =
    'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';
  return Array.from(container.querySelectorAll<HTMLElement>(selector));
}

export interface CRUDModalProps {
  open: boolean;
  title: string;
  onClose: () => void;
  onSubmit?: () => void;
  submitLabel?: string;
  cancelLabel?: string;
  submitting?: boolean;
  isDirty?: boolean;
  children: ReactNode;
}

export function CRUDModal({
  open,
  title,
  onClose,
  onSubmit,
  submitLabel = "Simpan",
  cancelLabel = "Batal",
  submitting = false,
  isDirty = false,
  children,
}: CRUDModalProps) {
  const titleId = useId();
  const modalRef = useRef<HTMLDivElement>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!open) {
      return;
    }
    previousFocusRef.current = document.activeElement as HTMLElement | null;
    const container = modalRef.current;
    if (container) {
      const focusables = getFocusableElements(container);
      focusables[0]?.focus();
    }

    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") {
        e.preventDefault();
        if (!submitting) {
          if (!isDirty || window.confirm("Buang perubahan yang belum disimpan?")) {
            onClose();
          }
        }
        return;
      }
      if (e.key === "Tab" && modalRef.current) {
        const focusables = getFocusableElements(modalRef.current);
        if (focusables.length === 0) {
          return;
        }
        const first = focusables[0];
        const last = focusables[focusables.length - 1];
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    }

    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      previousFocusRef.current?.focus();
    };
  }, [open, submitting, isDirty, onClose]);

  if (!open) {
    return null;
  }

  return (
    <div className="uc-modal-backdrop" role="presentation">
      <div
        ref={modalRef}
        className="uc-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
      >
        <div className="uc-modal-head">
          <h2 id={titleId}>{title}</h2>
          <IconButton
            label="Tutup dialog"
            icon={<X size={16} aria-hidden="true" />}
            disabled={submitting}
            onClick={onClose}
          />
        </div>
        <div className="uc-modal-body">{children}</div>
        <div className="uc-modal-foot">
          <Button variant="neutral" disabled={submitting} onClick={onClose}>
            {cancelLabel}
          </Button>
          {onSubmit && (
            <Button variant="primary" loading={submitting} onClick={onSubmit}>
              {submitLabel}
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}

export interface ConfirmDialogProps {
  open: boolean;
  title: string;
  impactMessage: string;
  confirmLabel?: string;
  cancelLabel?: string;
  loading?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export function ConfirmDialog({
  open,
  title,
  impactMessage,
  confirmLabel = "Hapus",
  cancelLabel = "Batal",
  loading = false,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  const titleId = useId();
  const cancelBtnRef = useRef<HTMLButtonElement>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!open) {
      return;
    }
    previousFocusRef.current = document.activeElement as HTMLElement | null;
    cancelBtnRef.current?.focus();

    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape" && !loading) {
        e.preventDefault();
        onCancel();
      }
    }
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("keydown", onKey);
      previousFocusRef.current?.focus();
    };
  }, [open, loading, onCancel]);

  if (!open) {
    return null;
  }

  return (
    <div className="uc-modal-backdrop" role="presentation">
      <div
        className="uc-modal"
        role="alertdialog"
        aria-modal="true"
        aria-labelledby={titleId}
      >
        <div className="uc-modal-head">
          <h2 id={titleId}>{title}</h2>
          <IconButton
            label="Tutup konfirmasi"
            icon={<X size={16} aria-hidden="true" />}
            disabled={loading}
            onClick={onCancel}
          />
        </div>
        <div className="uc-modal-body">
          <div className="uc-callout">
            <AlertTriangle size={18} aria-hidden="true" />
            <div>{impactMessage}</div>
          </div>
        </div>
        <div className="uc-modal-foot">
          <Button
            ref={cancelBtnRef}
            variant="neutral"
            disabled={loading}
            onClick={onCancel}
          >
            {cancelLabel}
          </Button>
          <Button
            variant="destructive-solid"
            loading={loading}
            onClick={onConfirm}
          >
            {confirmLabel}
          </Button>
        </div>
      </div>
    </div>
  );
}
