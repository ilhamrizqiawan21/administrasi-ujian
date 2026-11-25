import "@testing-library/jest-dom/vitest";
import { describe, expect, it } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { ToastProvider } from "./components/ui/Feedback";
import { LpjPage } from "./features/lpj/LpjPage";
import { ThemeProvider } from "./lib/theme";

const MOCK_EXAM = {
  id: "ex-1",
  institution_id: "inst-1",
  year_id: "yr-1",
  exam_type_id: "et-1",
  title: "PAS Ganjil 2026",
  semester_label: "Ganjil",
  mode: "paper" as const,
  starts_on: "2026-12-01",
  ends_on: "2026-12-05",
  state: "COMPLETED" as const,
  snapshot_revision: 1,
  revision: 1,
  config: {},
};

describe("LPJ-01..LPJ-05 LpjPage", () => {
  it("renders structured sections and readonly derived totals", async () => {
    render(
      <ThemeProvider>
        <ToastProvider>
          <LpjPage institutionId="inst-1" activeExam={MOCK_EXAM} />
        </ToastProvider>
      </ThemeProvider>,
    );

    await waitFor(() => {
      expect(screen.getByText("Peserta Eligible / Hadir")).toBeInTheDocument();
    });
    expect(screen.getByText(/LPJ Kegiatan: PAS Ganjil 2026/)).toBeInTheDocument();
    expect(screen.getByText("1. Bagian & Narasi")).toBeInTheDocument();
    expect(screen.getByText("2. Evaluasi & Rekomendasi")).toBeInTheDocument();
    expect(screen.getByText("3. Daftar Lampiran")).toBeInTheDocument();
  });
});
