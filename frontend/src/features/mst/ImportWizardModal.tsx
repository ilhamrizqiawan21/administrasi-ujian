import { useState, type ChangeEvent } from "react";
import { Button } from "../../components/ui/Button";
import { useToast } from "../../components/ui/Feedback";
import { SelectField } from "../../components/ui/FormFields";
import { CRUDModal } from "../../components/ui/Modal";
import { invokeBridge } from "../../lib/bridge";
import type { ImportPreviewResult } from "./types";

export interface ImportWizardModalProps {
  open: boolean;
  institutionId: string;
  kind: "students" | "staff" | "subjects" | "rooms";
  onClose: () => void;
  onCommitted: () => void;
}

function arrayBufferToBase64(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer);
  let binary = "";
  for (let i = 0; i < bytes.byteLength; i += 1) {
    binary += String.fromCharCode(bytes[i]);
  }
  return window.btoa(binary);
}

export function ImportWizardModal({
  open,
  institutionId,
  kind,
  onClose,
  onCommitted,
}: ImportWizardModalProps) {
  const { pushToast } = useToast();
  const [preview, setPreview] = useState<ImportPreviewResult | null>(null);
  const [duplicatePolicy, setDuplicatePolicy] = useState<"skip" | "update" | "fail">("skip");
  const [skipInvalid, setSkipInvalid] = useState(true);
  const [loading, setLoading] = useState(false);

  async function handleFileChange(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setLoading(true);
    try {
      const buf = await file.arrayBuffer();
      const res = await invokeBridge<ImportPreviewResult>("mst.imports.preview", {
        institution_id: institutionId,
        kind,
        filename: file.name,
        content_base64: arrayBufferToBase64(buf),
      });
      setPreview(res);
    } catch (err: unknown) {
      pushToast(
        err instanceof Error ? err.message : "Gagal membaca berkas XLSX.",
        "error"
      );
    } finally {
      setLoading(false);
    }
  }

  async function handleCommit() {
    if (!preview) return;
    setLoading(true);
    try {
      const res = await invokeBridge<{
        inserted: number;
        updated: number;
        skipped: number;
      }>("mst.imports.commit", {
        institution_id: institutionId,
        preview_id: preview.preview_id,
        duplicate_policy: duplicatePolicy,
        skip_invalid_rows: skipInvalid,
      });
      pushToast(
        `Impor selesai: ${res.inserted} masuk, ${res.updated} diperbarui, ${res.skipped} dilewati.`,
        "success"
      );
      setPreview(null);
      onCommitted();
      onClose();
    } catch (err: unknown) {
      pushToast(err instanceof Error ? err.message : "Gagal komit impor.", "error");
    } finally {
      setLoading(false);
    }
  }

  return (
    <CRUDModal
      open={open}
      title={`Impor XLSX (${kind})`}
      submitLabel="Simpan Impor"
      submitting={loading}
      onClose={() => {
        setPreview(null);
        onClose();
      }}
      onSubmit={preview ? handleCommit : undefined}
    >
      <div className="uc-field">
        <label htmlFor="mst-xlsx-picker">Pilih berkas .xlsx</label>
        <input
          id="mst-xlsx-picker"
          type="file"
          accept=".xlsx"
          onChange={handleFileChange}
        />
        <span className="uc-field-hint">
          Angka nol di depan pada sel teks dipertahankan; sel formula ditolak.
        </span>
      </div>

      {preview && (
        <div style={{ display: "grid", gap: 12 }}>
          <div className="uc-callout">
            <div>
              <strong>Ringkasan Pratinjau:</strong> Total {preview.counts.total} · Valid{" "}
              {preview.counts.valid} · Duplikat {preview.counts.duplicate} · Gagal{" "}
              {preview.counts.invalid}
            </div>
          </div>

          {preview.warnings.map((w, idx) => (
            <p key={idx} className="uc-field-error">
              {w}
            </p>
          ))}

          <SelectField
            label="Kebijakan Duplikat"
            value={duplicatePolicy}
            options={[
              { value: "skip", label: "Lewati baris duplikat (skip)" },
              { value: "update", label: "Perbarui data lama (update)" },
              { value: "fail", label: "Batalkan jika ada duplikat (fail)" },
            ]}
            onChange={(e) =>
              setDuplicatePolicy(e.target.value as "skip" | "update" | "fail")
            }
          />

          <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <input
              type="checkbox"
              checked={skipInvalid}
              onChange={(e) => setSkipInvalid(e.target.checked)}
            />
            <span>Lewati baris gagal dan simpan baris valid saja</span>
          </label>

          {preview.error_rows.length > 0 && (
            <div style={{ display: "grid", gap: 6 }}>
              <strong>Daftar Baris Gagal ({preview.error_rows.length})</strong>
              <ul style={{ margin: 0, paddingLeft: 18 }}>
                {preview.error_rows.slice(0, 8).map((err) => (
                  <li key={err.row_number} className="uc-field-error">
                    Baris {err.row_number}: {err.error}
                  </li>
                ))}
              </ul>
              <Button
                variant="neutral"
                size="sm"
                onClick={() => {
                  const csv = [
                    "row_number,error",
                    ...preview.error_rows.map(
                      (r) => `${r.row_number},"${r.error.replaceAll('"', '""')}"`
                    ),
                  ].join("\n");
                  const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
                  const url = URL.createObjectURL(blob);
                  const a = document.createElement("a");
                  a.href = url;
                  a.download = `laporan-gagal-${kind}.csv`;
                  a.click();
                  URL.revokeObjectURL(url);
                }}
              >
                Unduh Laporan Baris Gagal
              </Button>
            </div>
          )}
        </div>
      )}
    </CRUDModal>
  );
}
