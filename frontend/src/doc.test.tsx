import "@testing-library/jest-dom/vitest";
import { describe, expect, it } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { ToastProvider } from "./components/ui/Feedback";
import { DocumentCenterPage } from "./features/doc/DocumentCenterPage";
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

describe("DOC-01..DOC-09 Document Center UI", () => {
  it("renders document generator, format/paper selectors, and version history", async () => {
    render(
      <ThemeProvider>
        <ToastProvider>
          <DocumentCenterPage institutionId="inst-mock-1" activeExam={MOCK_EXAM} />
        </ToastProvider>
      </ThemeProvider>
    );

    await waitFor(() => {
      expect(screen.getByLabelText("Riwayat Dokumen")).toBeInTheDocument();
    });
    expect(screen.getByLabelText("Jenis Dokumen")).toBeInTheDocument();
    expect(screen.getByLabelText("Format Dokumen")).toBeInTheDocument();
    expect(screen.getByText("daftar_hadir")).toBeInTheDocument();
  });
});
