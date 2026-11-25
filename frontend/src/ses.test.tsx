import "@testing-library/jest-dom/vitest";
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { ToastProvider } from "./components/ui/Feedback";
import { TimetablePage } from "./features/ses/TimetablePage";
import { ThemeProvider } from "./lib/theme";

describe("SES-01..SES-07 Timetable UI", () => {
  it("renders empty state when no active exam is selected", () => {
    render(
      <ThemeProvider>
        <ToastProvider>
          <TimetablePage institutionId="inst-mock-1" activeExam={null} />
        </ToastProvider>
      </ThemeProvider>
    );
    expect(screen.getByText("Belum ada kegiatan ujian")).toBeInTheDocument();
  });

  it("renders timetable grid for active exam", async () => {
    render(
      <ThemeProvider>
        <ToastProvider>
          <TimetablePage
            institutionId="inst-mock-1"
            activeExam={{
              id: "exam-mock-1",
              institution_id: "inst-mock-1",
              year_id: "yr-1",
              exam_type_id: "et-1",
              title: "SAS Ganjil",
              semester_label: "Ganjil",
              mode: "paper",
              starts_on: "2026-11-30",
              ends_on: "2026-12-08",
              state: "PREPARATION",
              config: {},
              revision: 1,
            }}
          />
        </ToastProvider>
      </ThemeProvider>
    );
    expect(
      await screen.findByText(/Kisi Jadwal · Revisi v1/)
    ).toBeInTheDocument();
    expect(screen.getByText(/R01/)).toBeInTheDocument();
  });
});
