import "@testing-library/jest-dom/vitest";
import { describe, expect, it } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { ToastProvider } from "./components/ui/Feedback";
import { ExpeditionPage } from "./features/exp/ExpeditionPage";
import { ThemeProvider } from "./lib/theme";

const MOCK_EXAM = {
  id: "exam-mock-1",
  institution_id: "inst-mock-1",
  year_id: "yr-1",
  exam_type_id: "et-1",
  title: "SAS Ganjil",
  semester_label: "Ganjil",
  mode: "paper" as const,
  starts_on: "2026-11-30",
  ends_on: "2026-12-08",
  state: "DRAFT" as const,
  snapshot_revision: 1,
  revision: 1,
  config: {},
};

describe("EXP-01..EXP-06 Expedition UI", () => {
  it("renders matrix, print quantities, and handover tabs", async () => {
    render(
      <ThemeProvider>
        <ToastProvider>
          <ExpeditionPage institutionId="inst-mock-1" activeExam={MOCK_EXAM} />
        </ToastProvider>
      </ThemeProvider>
    );

    await waitFor(() => {
      expect(screen.getByLabelText("Matriks Berkas Ujian")).toBeInTheDocument();
    });
    expect(screen.getByText("Matematika")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Jumlah Cetak/i }));
    expect(screen.getByLabelText("Daftar Jumlah Cetak")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Serah Terima/i }));
    expect(screen.getByLabelText("Daftar Serah Terima")).toBeInTheDocument();
  });
});
