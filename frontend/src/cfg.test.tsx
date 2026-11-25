import "@testing-library/jest-dom/vitest";
import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { ToastProvider } from "./components/ui/Feedback";
import { FirstRunWizard } from "./features/cfg/FirstRunWizard";
import { SettingsPage } from "./features/cfg/SettingsPage";
import { ThemeProvider } from "./lib/theme";

describe("CFG-01..CFG-06 Onboarding & Settings UI", () => {
  it("validates FirstRunWizard and submits without network", async () => {
    const onCompleted = vi.fn();
    render(
      <ThemeProvider>
        <ToastProvider>
          <FirstRunWizard
            workspaceRoot="/local/UjianCerdas"
            levelPresets={{
              "SMP/MTs": ["VII", "VIII", "IX"],
              Kustom: [],
            }}
            onCompleted={onCompleted}
          />
        </ToastProvider>
      </ThemeProvider>
    );

    fireEvent.click(
      screen.getByRole("button", { name: "Selesaikan Setup Lembaga" })
    );
    expect(
      await screen.findByText("Nama lembaga minimal 2 karakter")
    ).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Nama Lembaga *"), {
      target: { value: "MTs Harapan" },
    });
    fireEvent.change(screen.getByLabelText("NPSN (Opsional)"), {
      target: { value: "00123456" },
    });
    fireEvent.click(
      screen.getByRole("button", { name: "Selesaikan Setup Lembaga" })
    );

    await vi.waitFor(() => {
      expect(onCompleted).toHaveBeenCalledTimes(1);
    });
    expect(onCompleted.mock.calls[0][0].npsn).toBe("00123456");
  });

  it("renders SettingsPage tabs and number policy preview", async () => {
    render(
      <ThemeProvider>
        <ToastProvider>
          <SettingsPage
            institution={{
              id: "inst-mock-1",
              name: "MTs Nusantara",
              short_name: "MTsN",
              npsn: "00112233",
              nsm: null,
              address: null,
              timezone: "Asia/Jakarta",
              logo_asset_id: null,
              logo_relative_path: null,
              revision: 1,
            }}
            levelPresets={{ "SMP/MTs": ["VII", "VIII", "IX"] }}
            onInstitutionUpdated={() => {}}
            onAddInstitution={() => {}}
          />
        </ToastProvider>
      </ThemeProvider>
    );

    fireEvent.click(screen.getByRole("tab", { name: "Penomoran" }));
    expect(
      await screen.findByText(/Kebijakan Penomoran/)
    ).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Pratinjau Nomor" }));
    expect(await screen.findByText(/UC-0001/)).toBeInTheDocument();
  });
});
