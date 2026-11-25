import "@testing-library/jest-dom/vitest";
import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { Button, IconButton } from "./components/ui/Button";
import { CurrencyField, IdentifierField } from "./components/ui/FormFields";
import { ConfirmDialog, CRUDModal } from "./components/ui/Modal";
import { ProgressBar } from "./components/ui/Feedback";
import { DataTable } from "./components/shared/DataTable";
import { JobProgress } from "./components/shared/JobProgress";
import { contrastRatio, OCEAN_LEDGER_PALETTE } from "./lib/contrast";
import { ThemeProvider, ThemeSwitcher } from "./lib/theme";

describe("UI-01..UI-12 Design System & Shared Components", () => {
  it("passes WCAG 2.2 contrast ratios for Ocean Ledger light and dark tokens", () => {
    const { light, dark } = OCEAN_LEDGER_PALETTE;
    expect(contrastRatio(light.text, light.surface)).toBeGreaterThanOrEqual(4.5);
    expect(contrastRatio(light.muted, light.surface)).toBeGreaterThanOrEqual(4.5);
    expect(contrastRatio(light.primaryOn, light.primary)).toBeGreaterThanOrEqual(4.5);
    expect(contrastRatio(light.navText, light.nav)).toBeGreaterThanOrEqual(4.5);
    expect(contrastRatio(light.destructive, light.surface)).toBeGreaterThanOrEqual(4.5);

    expect(contrastRatio(dark.text, dark.surface)).toBeGreaterThanOrEqual(4.5);
    expect(contrastRatio(dark.muted, dark.surface)).toBeGreaterThanOrEqual(4.5);
    expect(contrastRatio(dark.primaryOn, dark.primary)).toBeGreaterThanOrEqual(4.5);
    expect(contrastRatio(dark.navText, dark.nav)).toBeGreaterThanOrEqual(4.5);
    expect(contrastRatio(dark.destructive, dark.surface)).toBeGreaterThanOrEqual(4.5);
  });

  it("disables Button during loading to prevent double-submit", () => {
    const onClick = vi.fn();
    render(
      <Button variant="primary" loading onClick={onClick}>
        Simpan
      </Button>
    );
    const btn = screen.getByRole("button", { name: "Simpan" });
    expect(btn).toBeDisabled();
    fireEvent.click(btn);
    expect(onClick).not.toHaveBeenCalled();
  });

  it("shows tooltip on IconButton focus and dismisses on Escape", () => {
    render(<IconButton label="Edit data" icon={<span>E</span>} />);
    const btn = screen.getByRole("button", { name: "Edit data" });
    fireEvent.focus(btn);
    expect(screen.getByRole("tooltip")).toHaveTextContent("Edit data");
    fireEvent.keyDown(btn, { key: "Escape" });
    expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
  });

  it("preserves leading zeros in IdentifierField and integer IDR in CurrencyField", () => {
    const onCurrency = vi.fn();
    render(
      <div>
        <IdentifierField label="NISN" defaultValue="0071234501" />
        <CurrencyField label="Honor" value={150000} onChange={onCurrency} />
      </div>
    );
    const nisnInput = screen.getByLabelText("NISN") as HTMLInputElement;
    expect(nisnInput.value).toBe("0071234501");

    const honorInput = screen.getByLabelText("Honor");
    fireEvent.change(honorInput, { target: { value: "Rp250.000" } });
    expect(onCurrency).toHaveBeenCalledWith(250000);
  });

  it("focuses Cancel by default in ConfirmDialog and closes on Escape", () => {
    const onCancel = vi.fn();
    const onConfirm = vi.fn();
    render(
      <ConfirmDialog
        open
        title="Hapus siswa?"
        impactMessage="Data akan dihapus."
        onCancel={onCancel}
        onConfirm={onConfirm}
      />
    );
    expect(screen.getByRole("button", { name: "Batal" })).toHaveFocus();
    fireEvent.keyDown(document, { key: "Escape" });
    expect(onCancel).toHaveBeenCalledTimes(1);
    expect(onConfirm).not.toHaveBeenCalled();
  });

  it("traps focus inside CRUDModal", () => {
    render(
      <CRUDModal open title="Tambah" onClose={() => {}} onSubmit={() => {}}>
        <input aria-label="Nama" />
      </CRUDModal>
    );
    const closeBtn = screen.getByRole("button", { name: "Tutup dialog" });
    const saveBtn = screen.getByRole("button", { name: "Simpan" });
    expect(closeBtn).toHaveFocus();
    fireEvent.keyDown(document, { key: "Tab", shiftKey: true });
    expect(saveBtn).toHaveFocus();
  });

  it("filters rows and supports selection in DataTable", () => {
    const onSelection = vi.fn();
    render(
      <DataTable
        data={[
          { id: "1", name: "Nabila" },
          { id: "2", name: "Raka" },
        ]}
        columns={[{ accessorKey: "name", header: "Nama" }]}
        enableSelection
        onSelectionChange={onSelection}
      />
    );
    fireEvent.change(screen.getByLabelText("Cari tabel"), {
      target: { value: "Nabila" },
    });
    expect(screen.getByText("Nabila")).toBeInTheDocument();
    expect(screen.queryByText("Raka")).not.toBeInTheDocument();

    fireEvent.click(screen.getByLabelText("Pilih baris 1"));
    expect(onSelection).toHaveBeenCalledWith(["1"]);
  });

  it("renders N/A when ProgressBar total is 0 and handles JobProgress cancel", () => {
    const onCancel = vi.fn();
    render(
      <div>
        <ProgressBar current={0} total={0} label="Ekspor" />
        <JobProgress
          title="Solver"
          status="running"
          phase="Menghitung"
          current={3}
          total={10}
          onCancel={onCancel}
        />
      </div>
    );
    expect(screen.getByText(/N\/A/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Batalkan" }));
    expect(onCancel).toHaveBeenCalledTimes(1);
  });

  it("cycles theme preference and persists to localStorage", () => {
    window.localStorage.clear();
    render(
      <ThemeProvider>
        <ThemeSwitcher />
      </ThemeProvider>
    );
    const switcher = screen.getByRole("button");
    fireEvent.click(switcher);
    expect(document.documentElement.dataset.theme).toBe("light");
    fireEvent.click(switcher);
    expect(document.documentElement.dataset.theme).toBe("dark");
    expect(window.localStorage.getItem("ujian-cerdas:theme")).toBe("dark");
  });
});
