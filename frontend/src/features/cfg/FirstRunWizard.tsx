import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Building2 } from "lucide-react";
import { Button } from "../../components/ui/Button";
import { useToast } from "../../components/ui/Feedback";
import {
  IdentifierField,
  SelectField,
  TextField,
} from "../../components/ui/FormFields";
import { invokeBridge } from "../../lib/bridge";
import type { Institution } from "./types";

const firstRunSchema = z
  .object({
    name: z.string().trim().min(2, "Nama lembaga minimal 2 karakter"),
    short_name: z.string().trim().optional(),
    npsn: z
      .string()
      .trim()
      .refine((v) => v === "" || /^\d+$/.test(v), "NPSN harus berupa angka"),
    nsm: z
      .string()
      .trim()
      .refine((v) => v === "" || /^\d+$/.test(v), "NSM harus berupa angka"),
    address: z.string().trim().optional(),
    timezone: z.string().min(1),
    level_preset: z.string().min(1),
    custom_levels_text: z.string().optional(),
    academic_year_label: z
      .string()
      .trim()
      .min(4, "Tahun ajaran wajib diisi (mis. 2026/2027)"),
  })
  .superRefine((val, ctx) => {
    if (
      val.level_preset === "Kustom" &&
      !(val.custom_levels_text ?? "").trim()
    ) {
      ctx.addIssue({
        code: "custom",
        path: ["custom_levels_text"],
        message: "Masukkan minimal satu tingkatan (pisahkan dengan koma)",
      });
    }
  });

type FirstRunFormValues = z.infer<typeof firstRunSchema>;

export interface FirstRunWizardProps {
  workspaceRoot: string;
  levelPresets: Record<string, string[]>;
  allowCancel?: boolean;
  onCancel?: () => void;
  onCompleted: (institution: Institution) => void;
}

export function FirstRunWizard({
  workspaceRoot,
  levelPresets,
  allowCancel = false,
  onCancel,
  onCompleted,
}: FirstRunWizardProps) {
  const { pushToast } = useToast();
  const [submitting, setSubmitting] = useState(false);

  const form = useForm<FirstRunFormValues>({
    resolver: zodResolver(firstRunSchema),
    defaultValues: {
      name: "",
      short_name: "",
      npsn: "",
      nsm: "",
      address: "",
      timezone: "Asia/Jakarta",
      level_preset: "SMP/MTs",
      custom_levels_text: "",
      academic_year_label: "2026/2027",
    },
  });

  const selectedPreset = form.watch("level_preset");

  async function onSubmit(values: FirstRunFormValues) {
    setSubmitting(true);
    try {
      const customLevels =
        values.level_preset === "Kustom"
          ? (values.custom_levels_text ?? "")
              .split(",")
              .map((s) => s.trim())
              .filter(Boolean)
          : [];
      const res = await invokeBridge<{ institution: Institution }>(
        "cfg.first_run.setup",
        {
          name: values.name,
          short_name: values.short_name || null,
          npsn: values.npsn || null,
          nsm: values.nsm || null,
          address: values.address || null,
          timezone: values.timezone,
          level_preset: values.level_preset,
          custom_levels: customLevels,
          academic_year_label: values.academic_year_label,
        }
      );
      pushToast(`Profil lembaga '${res.institution.name}' dibuat.`, "success");
      onCompleted(res.institution);
    } catch (err: unknown) {
      pushToast(
        err instanceof Error ? err.message : "Gagal menyimpan profil awal.",
        "error"
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="uc-panel" style={{ maxWidth: 680, margin: "24px auto" }}>
      <div className="uc-panel-head">
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <Building2 size={18} aria-hidden="true" />
          <h2>Setup Awal Lembaga (Offline)</h2>
        </div>
        <span className="uc-sub">Lokasi data: {workspaceRoot}</span>
      </div>

      <form
        className="uc-panel-body"
        noValidate
        onSubmit={form.handleSubmit(onSubmit)}
        style={{ display: "grid", gap: 14 }}
      >
        <div className="uc-field-grid">
          <TextField
            label="Nama Lembaga"
            required
            error={form.formState.errors.name?.message}
            {...form.register("name")}
          />
          <TextField
            label="Nama Singkat (Opsional)"
            {...form.register("short_name")}
          />
          <IdentifierField
            label="NPSN (Opsional)"
            hint="Dipertahankan sebagai teks"
            error={form.formState.errors.npsn?.message}
            {...form.register("npsn")}
          />
          <IdentifierField
            label="NSM (Opsional)"
            error={form.formState.errors.nsm?.message}
            {...form.register("nsm")}
          />
          <SelectField
            label="Preset Jenjang"
            options={Object.keys(levelPresets).map((k) => ({
              value: k,
              label:
                levelPresets[k].length > 0
                  ? `${k} (${levelPresets[k].join(", ")})`
                  : k,
            }))}
            {...form.register("level_preset")}
          />
          <TextField
            label="Tahun Ajaran Awal"
            required
            error={form.formState.errors.academic_year_label?.message}
            {...form.register("academic_year_label")}
          />
          <SelectField
            label="Zona Waktu"
            options={[
              { value: "Asia/Jakarta", label: "WIB (Asia/Jakarta)" },
              { value: "Asia/Makassar", label: "WITA (Asia/Makassar)" },
              { value: "Asia/Jayapura", label: "WIT (Asia/Jayapura)" },
            ]}
            {...form.register("timezone")}
          />
          <TextField
            label="Alamat (Opsional)"
            {...form.register("address")}
          />
        </div>

        {selectedPreset === "Kustom" && (
          <TextField
            label="Daftar Tingkatan Kustom (pisahkan dengan koma)"
            hint="Contoh: Tahfidz, Wustha, Ulya"
            error={form.formState.errors.custom_levels_text?.message}
            {...form.register("custom_levels_text")}
          />
        )}

        <div className="uc-actions" style={{ justifyContent: "flex-end" }}>
          {allowCancel && onCancel && (
            <Button variant="neutral" disabled={submitting} onClick={onCancel}>
              Batal
            </Button>
          )}
          <Button type="submit" variant="primary" loading={submitting}>
            Selesaikan Setup Lembaga
          </Button>
        </div>
      </form>
    </section>
  );
}
