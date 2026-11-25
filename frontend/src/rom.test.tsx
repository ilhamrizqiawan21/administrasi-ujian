import "@testing-library/jest-dom/vitest";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";

vi.mock("react-konva", () => ({
  Stage: ({ children }: { children?: ReactNode }) => (
    <div data-testid="konva-stage">{children}</div>
  ),
  Layer: ({ children }: { children?: ReactNode }) => <div>{children}</div>,
  Rect: ({ onClick }: { onClick?: () => void }) => (
    <button type="button" onClick={onClick} aria-label="seat-rect" />
  ),
  Text: ({ text }: { text?: string }) => <span>{text}</span>,
}));

import { ToastProvider } from "./components/ui/Feedback";
import { SeatingPage } from "./features/rom/SeatingPage";
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

describe("ROM-01..ROM-08 Seating & Denah UI", () => {
  it("renders empty state when no active exam is selected", () => {
    render(
      <ThemeProvider>
        <ToastProvider>
          <SeatingPage institutionId="inst-mock-1" activeExam={null} />
        </ToastProvider>
      </ThemeProvider>
    );
    expect(
      screen.getByText(/Pilih atau buat kegiatan ujian terlebih dahulu/i)
    ).toBeInTheDocument();
  });

  it("renders room list, konva canvas, diagnostics, and accessible seat table", async () => {
    render(
      <ThemeProvider>
        <ToastProvider>
          <SeatingPage institutionId="inst-mock-1" activeExam={MOCK_EXAM} />
        </ToastProvider>
      </ThemeProvider>
    );

    await waitFor(() => {
      expect(screen.getByText(/Denah R01 · Ruang 01/i)).toBeInTheDocument();
    });

    expect(screen.getByTestId("konva-stage")).toBeInTheDocument();
    expect(screen.getByLabelText("Daftar Kursi Ruang")).toBeInTheDocument();
    expect(screen.getByText("Siswa Satu (001)")).toBeInTheDocument();
    expect(screen.getByText(/Alokasi Otomatis/)).toBeInTheDocument();

    // Open layout editor modal (ROM-01)
    fireEvent.click(screen.getByRole("button", { name: /Atur Grid/i }));
    expect(screen.getByText(/Atur Tata Letak R01/i)).toBeInTheDocument();
  });
});
