import "@testing-library/jest-dom/vitest";
import { describe, expect, it } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { ToastProvider } from "./components/ui/Feedback";
import { BackupPage } from "./features/bak/BackupPage";
import { ThemeProvider } from "./lib/theme";

describe("BAK-01..BAK-04 BackupPage", () => {
  it("renders backup list, schedule tab, and recovery diagnostics tab", async () => {
    render(
      <ThemeProvider>
        <ToastProvider>
          <BackupPage institutionId="inst-1" />
        </ToastProvider>
      </ThemeProvider>,
    );

    await waitFor(() => {
      expect(screen.getByText("backups/backup_manual_1.zip")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("2. Jadwal & Retensi"));
    await waitFor(() => {
      expect(screen.getByText("Simpan Jadwal")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("3. Diagnostik & Pemulihan"));
    await waitFor(() => {
      expect(screen.getByText("Workspace Sehat")).toBeInTheDocument();
    });
  });
});
