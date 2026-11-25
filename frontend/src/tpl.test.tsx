import "@testing-library/jest-dom/vitest";
import { describe, expect, it } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { ToastProvider } from "./components/ui/Feedback";
import { TemplatesPage } from "./features/tpl/TemplatesPage";
import { ThemeProvider } from "./lib/theme";

describe("TPL-01..TPL-06 Template & Branding UI", () => {
  it("renders letterheads, template catalog with F4 note, and brand editor", async () => {
    render(
      <ThemeProvider>
        <ToastProvider>
          <TemplatesPage institutionId="inst-mock-1" />
        </ToastProvider>
      </ThemeProvider>
    );

    await waitFor(() => {
      expect(screen.getByLabelText("Daftar Kop Surat")).toBeInTheDocument();
    });
    expect(screen.getByText("Kop Resmi")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Katalog Template/i }));
    expect(screen.getByLabelText("Katalog Template")).toBeInTheDocument();
    expect(screen.getByText(/F4 eksplisit: 215 x 330 mm/i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Branding & Kontras/i }));
    expect(screen.getByText(/WCAG/i)).toBeInTheDocument();
  });
});
