import {
  forwardRef,
  useState,
  type ButtonHTMLAttributes,
  type ReactNode,
} from "react";
import { FileSpreadsheet, FileText, Loader2 } from "lucide-react";

export type ButtonVariant =
  | "primary"
  | "secondary"
  | "neutral"
  | "destructive"
  | "destructive-solid";
export type ButtonSize = "sm" | "md" | "lg";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  iconOnly?: boolean;
  children: ReactNode;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  function Button(
    {
      variant = "neutral",
      size = "md",
      loading = false,
      iconOnly = false,
      disabled,
      type = "button",
      className = "",
      children,
      ...rest
    },
    ref
  ) {
    const variantClass =
      variant === "neutral" ? "" : `uc-btn-${variant}`;
    const sizeClass = `uc-btn-${size}`;
    const iconClass = iconOnly ? "uc-icon-btn" : "";
    const classes = ["uc-btn", variantClass, sizeClass, iconClass, className]
      .filter(Boolean)
      .join(" ");

    return (
      <button
        ref={ref}
        type={type}
        disabled={disabled || loading}
        aria-busy={loading || undefined}
        className={classes}
        {...rest}
      >
        {loading && <Loader2 size={16} aria-hidden="true" />}
        {children}
      </button>
    );
  }
);

export interface IconButtonProps
  extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, "children"> {
  label: string;
  icon: ReactNode;
  variant?: ButtonVariant;
  size?: ButtonSize;
}

export function IconButton({
  label,
  icon,
  variant = "neutral",
  size = "sm",
  className = "",
  onKeyDown,
  ...rest
}: IconButtonProps) {
  const [showTip, setShowTip] = useState(false);

  return (
    <span
      className="uc-tooltip-wrap"
      onMouseEnter={() => setShowTip(true)}
      onMouseLeave={() => setShowTip(false)}
      onFocus={() => setShowTip(true)}
      onBlur={() => setShowTip(false)}
    >
      <Button
        variant={variant}
        size={size}
        iconOnly
        aria-label={label}
        className={className}
        onKeyDown={(e) => {
          if (e.key === "Escape") {
            setShowTip(false);
          }
          onKeyDown?.(e);
        }}
        {...rest}
      >
        {icon}
      </Button>
      {showTip && (
        <span role="tooltip" className="uc-tooltip">
          {label}
        </span>
      )}
    </span>
  );
}

export interface ExportActionGroupProps {
  onExportWord?: () => void;
  onExportPdf?: () => void;
  onExportExcel?: () => void;
  disabled?: boolean;
}

export function ExportActionGroup({
  onExportWord,
  onExportPdf,
  onExportExcel,
  disabled = false,
}: ExportActionGroupProps) {
  return (
    <div className="uc-actions" role="group" aria-label="Ekspor dokumen">
      {onExportWord && (
        <IconButton
          label="Ekspor Word"
          icon={<FileText size={16} aria-hidden="true" />}
          className="uc-export-word"
          disabled={disabled}
          onClick={onExportWord}
        />
      )}
      {onExportPdf && (
        <IconButton
          label="Ekspor PDF"
          icon={<FileText size={16} aria-hidden="true" />}
          className="uc-export-pdf"
          disabled={disabled}
          onClick={onExportPdf}
        />
      )}
      {onExportExcel && (
        <IconButton
          label="Ekspor Excel"
          icon={<FileSpreadsheet size={16} aria-hidden="true" />}
          className="uc-export-excel"
          disabled={disabled}
          onClick={onExportExcel}
        />
      )}
    </div>
  );
}
