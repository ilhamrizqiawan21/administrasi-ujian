import "@testing-library/jest-dom/vitest";
import { describe, expect, it } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { ToastProvider } from "./components/ui/Feedback";
import { InvigilationPage } from "./features/sch/InvigilationPage";
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

describe("SCH-01..SCH-08 Invigilation Scheduling UI", () => {
  it("renders empty state when no active exam is selected", () => {
    render(
      <ThemeProvider>
        <ToastProvider>
          <InvigilationPage institutionId="inst-mock-1" activeExam={null} />
        </ToastProvider>
      </ThemeProvider>
    );
    expect(
      screen.getByText(/Pilih atau buat kegiatan ujian terlebih dahulu/i)
    ).toBeInTheDocument();
  });

  it("renders schedule grid, workload tab, and reserve tab", async () => {
    render(
      <ThemeProvider>
        <ToastProvider>
          <InvigilationPage institutionId="inst-mock-1" activeExam={MOCK_EXAM} />
        </ToastProvider>
      </ThemeProvider>
    );

    await waitFor(() => {
      expect(screen.getByLabelText("Grid Jadwal Pengawas")).toBeInTheDocument();
    });
    expect(screen.getAllByText("Guru Satu").length).toBeGreaterThanOrEqual(1);

    fireEvent.click(screen.getByRole("button", { name: /Beban Kerja & Aturan/i }));
    expect(screen.getByLabelText("Beban Kerja Pengawas")).toBeInTheDocument();
    expect(screen.getByText(/G01 · Guru Satu/i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Cadangan/i }));
    expect(screen.getByLabelText("Daftar Pengawas Cadangan")).toBeInTheDocument();
  });
});
