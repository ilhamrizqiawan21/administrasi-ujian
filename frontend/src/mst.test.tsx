import "@testing-library/jest-dom/vitest";
import { describe, expect, it } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { ToastProvider } from "./components/ui/Feedback";
import { MasterDataPage } from "./features/mst/MasterDataPage";
import { ThemeProvider } from "./lib/theme";

describe("MST-01..MST-08 Master Data UI", () => {
  it("renders students with leading zeros and switches tabs", async () => {
    render(
      <ThemeProvider>
        <ToastProvider>
          <MasterDataPage institutionId="inst-mock-1" />
        </ToastProvider>
      </ThemeProvider>
    );

    expect(await screen.findByText("0001")).toBeInTheDocument();
    expect(screen.getByText("Nabila Putri")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("tab", { name: /Staf & Guru/ }));
    expect(await screen.findByText("Ahmad Fauzi")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("tab", { name: /Kualitas Data/ }));
    expect(
      await screen.findByText("Tidak ada temuan kualitas data")
    ).toBeInTheDocument();
  });
});
