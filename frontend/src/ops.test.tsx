import "@testing-library/jest-dom/vitest";
import { describe, expect, it } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { ToastProvider } from "./components/ui/Feedback";
import { ExecutionPage } from "./features/ops/ExecutionPage";
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

describe("OPS-01..OPS-08 Exam Execution UI", () => {
  it("renders monitor, student attendance, staff attendance, and incidents tabs", async () => {
    render(
      <ThemeProvider>
        <ToastProvider>
          <ExecutionPage institutionId="inst-mock-1" activeExam={MOCK_EXAM} />
        </ToastProvider>
      </ThemeProvider>
    );

    await waitFor(() => {
      expect(screen.getByLabelText("Monitor Sesi Ruang")).toBeInTheDocument();
    });
    expect(screen.getByText("R01 · Ruang 01")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Presensi Peserta/i }));
    expect(screen.getByLabelText("Presensi Peserta")).toBeInTheDocument();
    expect(screen.getByText("Siswa 1")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Insiden & Susulan/i }));
    expect(screen.getByLabelText("Log Insiden")).toBeInTheDocument();
  });
});
