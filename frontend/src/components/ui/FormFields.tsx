import {
  forwardRef,
  useId,
  type InputHTMLAttributes,
  type SelectHTMLAttributes,
} from "react";

interface FieldWrapperProps {
  label: string;
  htmlFor: string;
  hint?: string;
  error?: string;
  required?: boolean;
}

function FieldShell({
  label,
  htmlFor,
  hint,
  error,
  required,
  children,
}: FieldWrapperProps & { children: React.ReactNode }) {
  const hintId = hint ? `${htmlFor}-hint` : undefined;
  const errorId = error ? `${htmlFor}-error` : undefined;
  return (
    <div className="uc-field">
      <label htmlFor={htmlFor}>
        {label}
        {required ? " *" : ""}
      </label>
      {children}
      {hint && !error && (
        <span id={hintId} className="uc-field-hint">
          {hint}
        </span>
      )}
      {error && (
        <span id={errorId} className="uc-field-error" role="alert">
          {error}
        </span>
      )}
    </div>
  );
}

export interface TextFieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  hint?: string;
  error?: string;
}

export const TextField = forwardRef<HTMLInputElement, TextFieldProps>(
  function TextField({ label, hint, error, id, required, ...rest }, ref) {
    const autoId = useId();
    const inputId = id ?? autoId;
    const describedBy = error
      ? `${inputId}-error`
      : hint
        ? `${inputId}-hint`
        : undefined;

    return (
      <FieldShell
        label={label}
        htmlFor={inputId}
        hint={hint}
        error={error}
        required={required}
      >
        <input
          ref={ref}
          id={inputId}
          className="uc-input"
          required={required}
          aria-invalid={Boolean(error) || undefined}
          aria-describedby={describedBy}
          {...rest}
        />
      </FieldShell>
    );
  }
);

export const IdentifierField = forwardRef<HTMLInputElement, TextFieldProps>(
  function IdentifierField(props, ref) {
    return (
      <TextField
        ref={ref}
        type="text"
        inputMode="numeric"
        autoComplete="off"
        spellCheck={false}
        {...props}
      />
    );
  }
);

export interface SelectOption {
  value: string;
  label: string;
}

export interface SelectFieldProps
  extends SelectHTMLAttributes<HTMLSelectElement> {
  label: string;
  options: SelectOption[];
  hint?: string;
  error?: string;
}

export const SelectField = forwardRef<HTMLSelectElement, SelectFieldProps>(
  function SelectField(
    { label, options, hint, error, id, required, ...rest },
    ref
  ) {
    const autoId = useId();
    const selectId = id ?? autoId;
    const describedBy = error
      ? `${selectId}-error`
      : hint
        ? `${selectId}-hint`
        : undefined;

    return (
      <FieldShell
        label={label}
        htmlFor={selectId}
        hint={hint}
        error={error}
        required={required}
      >
        <select
          ref={ref}
          id={selectId}
          className="uc-select"
          required={required}
          aria-invalid={Boolean(error) || undefined}
          aria-describedby={describedBy}
          {...rest}
        >
          {options.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </FieldShell>
    );
  }
);

export const DateField = forwardRef<HTMLInputElement, TextFieldProps>(
  function DateField(props, ref) {
    return <TextField ref={ref} type="date" {...props} />;
  }
);

export interface CurrencyFieldProps {
  label: string;
  value: number;
  onChange: (valueIdr: number) => void;
  hint?: string;
  error?: string;
  required?: boolean;
  disabled?: boolean;
  id?: string;
}

export function formatIdr(amount: number): string {
  return `Rp${Math.trunc(amount).toLocaleString("id-ID")}`;
}

export function CurrencyField({
  label,
  value,
  onChange,
  hint,
  error,
  required,
  disabled,
  id,
}: CurrencyFieldProps) {
  const autoId = useId();
  const inputId = id ?? autoId;
  const describedBy = error
    ? `${inputId}-error`
    : hint
      ? `${inputId}-hint`
      : undefined;

  return (
    <FieldShell
      label={label}
      htmlFor={inputId}
      hint={hint ?? formatIdr(value)}
      error={error}
      required={required}
    >
      <input
        id={inputId}
        type="text"
        inputMode="numeric"
        className="uc-input"
        value={String(Math.trunc(value))}
        disabled={disabled}
        required={required}
        aria-invalid={Boolean(error) || undefined}
        aria-describedby={describedBy}
        onChange={(e) => {
          const digits = e.target.value.replace(/[^\d]/g, "");
          onChange(digits === "" ? 0 : Number.parseInt(digits, 10));
        }}
      />
    </FieldShell>
  );
}
