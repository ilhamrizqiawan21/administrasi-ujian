import "@testing-library/jest-dom/vitest";
import { describe, expect, it } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { ToastProvider } from "./components/ui/Feedback";
import { ArchivePage } from "./features/arc/ArchivePage";
import { ThemeProvider } from "./lib/theme";

describe("ARC-01..ARC-04 ArchivePage", () => {
  it("renders archive browser filters, event rows, and retention tab", async () => {
    render(
      <ThemeProvider>
        <ToastProvider>
          <ArchivePage institutionId="inst-1" />
        </ToastProvider>
      </ThemeProvider>,
    );

    await waitFor(() => {
      expect(screen.getByText("PAS Ganjil 2026")).toBeInTheDocument();
    });
    expect(screen.getByText("1. Browser Arsip & Paket")).toBeInTheDocument();
    expect(screen.getByText("2. Retensi & Pembersihan")).toBeInTheDocument();

    fireEvent.click(screen.getByText("2. Retensi & Pembersihan"));
    await waitFor(() => {
      expect(screen.getByText("PAS Ganjil 2024")).toBeInTheDocument();
    });
    expect(screen.getByText("Siap Retensi")).toBeInTheDocument();
  });
});
