import "@testing-library/jest-dom/vitest";
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { ToastProvider } from "./components/ui/Feedback";
import { DashboardPage } from "./features/evt/DashboardPage";
import { ThemeProvider } from "./lib/theme";

describe("EVT-01..EVT-07 Dashboard & Exam Workspace UI", () => {
  it("handles zero/empty active exam state cleanly without fake KPI", () => {
    render(
      <ThemeProvider>
        <ToastProvider>
          <DashboardPage
            institutionId="inst-mock-1"
            activeExam={null}
            onNavigate={vi.fn()}
          />
        </ToastProvider>
      </ThemeProvider>
    );
    expect(
      screen.getByText("Belum ada kegiatan ujian aktif")
    ).toBeInTheDocument();
  });

  it("renders derived counts and readiness checklist for active exam", async () => {
    render(
      <ThemeProvider>
        <ToastProvider>
          <DashboardPage
            institutionId="inst-mock-1"
            activeExam={{
              id: "exam-mock-1",
              institution_id: "inst-mock-1",
              year_id: "yr-1",
              exam_type_id: "et-1",
              title: "SAS Ganjil 2026/2027",
              semester_label: "Ganjil",
              mode: "paper",
              starts_on: "2026-11-30",
              ends_on: "2026-12-08",
              state: "PREPARATION",
              config: {},
              revision: 1,
            }}
            onNavigate={vi.fn()}
          />
        </ToastProvider>
      </ThemeProvider>
    );
    expect(
      await screen.findByText(/Kesiapan Pelaksanaan · SAS Ganjil 2026\/2027/)
    ).toBeInTheDocument();
    expect(screen.getByText("Peserta kegiatan")).toBeInTheDocument();
  });
});
