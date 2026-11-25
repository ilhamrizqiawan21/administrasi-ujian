import "@testing-library/jest-dom/vitest";
import { describe, expect, it } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { App } from "./App";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { ToastProvider } from "./components/ui/Feedback";
import { ThemeProvider } from "./lib/theme";

function Boom(): never {
  throw new Error("Simulated render crash");
}

function renderWithProviders() {
  return render(
    <ThemeProvider>
      <ToastProvider>
        <App />
      </ToastProvider>
    </ThemeProvider>
  );
}

describe("FND-09 Frontend bootstrap", () => {
  it("renders ErrorBoundary fallback when child throws", () => {
    render(
      <ErrorBoundary>
        <Boom />
      </ErrorBoundary>
    );
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Simulated render crash"
    );
  });

  it("navigates via hash routes between Dashboard and Diagnostik", async () => {
    renderWithProviders();
    expect(await screen.findByText(/Kesiapan Pelaksanaan/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Diagnostik" }));
    expect(window.location.hash).toBe("#/diagnostik");
    expect(await screen.findByText("Diagnostik Runtime")).toBeInTheDocument();
  });
});
