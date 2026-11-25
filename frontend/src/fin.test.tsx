import "@testing-library/jest-dom/vitest";
import { describe, expect, it } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { ToastProvider } from "./components/ui/Feedback";
import { FinancePage } from "./features/fin/FinancePage";
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

describe("FIN-01..FIN-08 Finance & Honorarium UI", () => {
  it("renders RAB variance, cashbook, and honorarium tabs", async () => {
    render(
      <ThemeProvider>
        <ToastProvider>
          <FinancePage institutionId="inst-mock-1" activeExam={MOCK_EXAM} />
        </ToastProvider>
      </ThemeProvider>
    );

    await waitFor(() => {
      expect(screen.getByLabelText("Varians Anggaran")).toBeInTheDocument();
    });
    expect(screen.getByText("Honorarium")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Buku Kas & Realisasi/i }));
    expect(screen.getByLabelText("Buku Kas")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Honorarium & Kuitansi/i }));
    expect(screen.getByLabelText("Daftar Honorarium")).toBeInTheDocument();
  });
});
