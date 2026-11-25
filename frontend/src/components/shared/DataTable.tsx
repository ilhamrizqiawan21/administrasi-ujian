import { useMemo, useState, type ReactNode } from "react";
import {
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  useReactTable,
  type ColumnDef,
  type RowSelectionState,
  type SortingState,
  type VisibilityState,
} from "@tanstack/react-table";
import { ArrowUpDown, ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "../ui/Button";
import { StatePanel } from "../ui/Feedback";

export type CellAlign = "left" | "center" | "num" | "actions";

export interface DataTableProps<TData extends { id: string }> {
  data: TData[];
  columns: ColumnDef<TData, unknown>[];
  searchPlaceholder?: string;
  toolbarExtra?: ReactNode;
  enableSelection?: boolean;
  onSelectionChange?: (selectedIds: string[]) => void;
  emptyTitle?: string;
  emptyDescription?: string;
  getCellAlign?: (columnId: string) => CellAlign;
}

export function DataTable<TData extends { id: string }>({
  data,
  columns,
  searchPlaceholder = "Cari data...",
  toolbarExtra,
  enableSelection = false,
  onSelectionChange,
  emptyTitle = "Belum ada data",
  emptyDescription = "Tambahkan data baru untuk mulai mengelola daftar ini.",
  getCellAlign,
}: DataTableProps<TData>) {
  const [sorting, setSorting] = useState<SortingState>([]);
  const [globalFilter, setGlobalFilter] = useState("");
  const [columnVisibility, setColumnVisibility] = useState<VisibilityState>({});
  const [rowSelection, setRowSelection] = useState<RowSelectionState>({});

  const tableColumns = useMemo<ColumnDef<TData, unknown>[]>(() => {
    if (!enableSelection) {
      return columns;
    }
    const selectCol: ColumnDef<TData, unknown> = {
      id: "_select",
      header: ({ table }) => (
        <input
          type="checkbox"
          aria-label="Pilih semua baris pada halaman"
          checked={table.getIsAllPageRowsSelected()}
          ref={(el) => {
            if (el) {
              el.indeterminate = table.getIsSomePageRowsSelected();
            }
          }}
          onChange={table.getToggleAllPageRowsSelectedHandler()}
        />
      ),
      cell: ({ row }) => (
        <input
          type="checkbox"
          aria-label={`Pilih baris ${row.original.id}`}
          checked={row.getIsSelected()}
          disabled={!row.getCanSelect()}
          onChange={row.getToggleSelectedHandler()}
        />
      ),
      enableSorting: false,
      enableHiding: false,
    };
    return [selectCol, ...columns];
  }, [columns, enableSelection]);

  const table = useReactTable({
    data,
    columns: tableColumns,
    getRowId: (row) => row.id,
    state: {
      sorting,
      globalFilter,
      columnVisibility,
      rowSelection,
    },
    initialState: {
      pagination: { pageSize: 25 },
    },
    onSortingChange: setSorting,
    onGlobalFilterChange: setGlobalFilter,
    onColumnVisibilityChange: setColumnVisibility,
    onRowSelectionChange: (updater) => {
      const next =
        typeof updater === "function" ? updater(rowSelection) : updater;
      setRowSelection(next);
      onSelectionChange?.(Object.keys(next).filter((k) => next[k]));
    },
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
  });

  const rows = table.getRowModel().rows;
  const selectedCount = Object.values(rowSelection).filter(Boolean).length;

  return (
    <section className="uc-panel">
      <div className="uc-toolbar">
        <input
          type="search"
          className="uc-input"
          style={{ width: 220 }}
          aria-label="Cari tabel"
          placeholder={searchPlaceholder}
          value={globalFilter}
          onChange={(e) => setGlobalFilter(e.target.value)}
        />
        {enableSelection && selectedCount > 0 && (
          <span className="uc-sub">{selectedCount} dipilih</span>
        )}
        {toolbarExtra}
        <div className="uc-toolbar-spacer" />
        <label className="uc-sub" style={{ display: "inline-flex", gap: 6, alignItems: "center" }}>
          Baris
          <select
            className="uc-select"
            style={{ width: "auto", height: 32 }}
            aria-label="Jumlah baris per halaman"
            value={table.getState().pagination.pageSize}
            onChange={(e) => table.setPageSize(Number(e.target.value))}
          >
            {[25, 50, 100].map((size) => (
              <option key={size} value={size}>
                {size}
              </option>
            ))}
          </select>
        </label>
      </div>

      {rows.length === 0 ? (
        <StatePanel
          kind="empty"
          title={emptyTitle}
          description={emptyDescription}
        />
      ) : (
        <div className="uc-table-wrap">
          <table className="uc-table">
            <thead>
              {table.getHeaderGroups().map((hg) => (
                <tr key={hg.id}>
                  {hg.headers.map((header) => {
                    const canSort = header.column.getCanSort();
                    return (
                      <th key={header.id} scope="col">
                        {header.isPlaceholder ? null : canSort ? (
                          <button
                            type="button"
                            className="uc-th-sort"
                            onClick={header.column.getToggleSortingHandler()}
                          >
                            {flexRender(
                              header.column.columnDef.header,
                              header.getContext()
                            )}
                            <ArrowUpDown size={12} aria-hidden="true" />
                          </button>
                        ) : (
                          flexRender(
                            header.column.columnDef.header,
                            header.getContext()
                          )
                        )}
                      </th>
                    );
                  })}
                </tr>
              ))}
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.id}>
                  {row.getVisibleCells().map((cell) => {
                    const colId = cell.column.id;
                    const align =
                      colId === "_select"
                        ? "center"
                        : colId === "actions"
                          ? "actions"
                          : (getCellAlign?.(colId) ?? "left");
                    return (
                      <td key={cell.id} className={`uc-td-${align}`}>
                        {flexRender(
                          cell.column.columnDef.cell,
                          cell.getContext()
                        )}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="uc-table-foot">
        <span>
          {table.getFilteredRowModel().rows.length} baris · Halaman{" "}
          {table.getState().pagination.pageIndex + 1} dari{" "}
          {Math.max(1, table.getPageCount())}
        </span>
        <div className="uc-actions">
          <Button
            size="sm"
            disabled={!table.getCanPreviousPage()}
            onClick={() => table.previousPage()}
          >
            <ChevronLeft size={14} aria-hidden="true" />
            Sebelumnya
          </Button>
          <Button
            size="sm"
            disabled={!table.getCanNextPage()}
            onClick={() => table.nextPage()}
          >
            Berikutnya
            <ChevronRight size={14} aria-hidden="true" />
          </Button>
        </div>
      </div>
    </section>
  );
}
