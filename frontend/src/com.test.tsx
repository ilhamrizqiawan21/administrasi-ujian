import "@testing-library/jest-dom/vitest";
import { describe, expect, it } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { ToastProvider } from "./components/ui/Feedback";
import { CommitteePage } from "./features/com/CommitteePage";
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

describe("COM-01..COM-06 Committee & Meetings UI", () => {
  it("renders org tree, program kerja, meetings, and signatories tabs", async () => {
    render(
      <ThemeProvider>
        <ToastProvider>
          <CommitteePage institutionId="inst-mock-1" activeExam={MOCK_EXAM} />
        </ToastProvider>
      </ThemeProvider>
    );

    await waitFor(() => {
      expect(screen.getByText("Bagan Struktur Panitia")).toBeInTheDocument();
    });
    expect(screen.getAllByText("Ketua Panitia").length).toBeGreaterThanOrEqual(1);

    fireEvent.click(screen.getByRole("button", { name: "Program Kerja" }));
    expect(screen.getByText("Program Kerja Panitia")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Rapat & Notulen/i }));
    expect(screen.getByLabelText("Daftar Rapat Panitia")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Penanda Tangan/i }));
    expect(screen.getByLabelText("Daftar Penanda Tangan")).toBeInTheDocument();
  });
});
