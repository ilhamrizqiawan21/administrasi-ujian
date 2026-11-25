import "@testing-library/jest-dom/vitest";
import { describe, expect, it } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { ToastProvider } from "./components/ui/Feedback";
import { TasksPage } from "./features/tsk/TasksPage";
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

describe("TSK-01..TSK-05 Tasks & Timeline UI", () => {
  it("renders task table, missing PIC flag, and timeline view", async () => {
    render(
      <ThemeProvider>
        <ToastProvider>
          <TasksPage institutionId="inst-mock-1" activeExam={MOCK_EXAM} />
        </ToastProvider>
      </ThemeProvider>
    );

    await waitFor(() => {
      expect(screen.getByLabelText("Tabel Tugas Panitia")).toBeInTheDocument();
    });
    expect(screen.getByText("Rapat koordinasi panitia")).toBeInTheDocument();
    expect(screen.getByText("Belum ada PIC")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Timeline" }));
    expect(screen.getByText("2026-11-28")).toBeInTheDocument();
  });
});
