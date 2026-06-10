import { useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { motion } from "framer-motion";
import { cn } from "@/utils/cn";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { FilterBar, type FilterConfig } from "./FilterBar";
import { Pagination } from "./Pagination";
import { downloadTablePdf, printTable } from "@/utils/tableExport";

export interface Column<T> {
  key: string;
  header: string;
  cell: (row: T) => ReactNode;
  className?: string;
  /** Plain-text value for print/PDF export. Omit for action columns. */
  exportValue?: (row: T) => string;
  exportable?: boolean;
}

interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  loading?: boolean;
  emptyMessage?: string;
  searchPlaceholder?: string;
  searchValue?: string;
  onSearchChange?: (value: string) => void;
  filters?: FilterConfig[];
  onExport?: () => void;
  onPrint?: () => void;
  onPdfDownload?: () => void;
  exportTitle?: string;
  actions?: ReactNode;
  className?: string;
  embedded?: boolean;
  /** Server-side pagination */
  page?: number;
  pageSize?: number;
  total?: number;
  onPageChange?: (page: number) => void;
  onPageSizeChange?: (size: number) => void;
  /** Client-side pagination when no server props provided */
  clientPagination?: boolean;
  defaultPageSize?: number;
}

function getExportColumns<T>(columns: Column<T>[]) {
  return columns
    .filter((col) => col.key !== "actions" && col.exportable !== false && col.exportValue)
    .map((col) => ({
      header: col.header,
      exportValue: col.exportValue!,
    }));
}

export function DataTable<T>({
  columns,
  data,
  loading,
  emptyMessage = "No records found.",
  searchPlaceholder,
  searchValue,
  onSearchChange,
  filters,
  onExport,
  onPrint,
  onPdfDownload,
  exportTitle,
  actions,
  className,
  embedded,
  page,
  pageSize,
  total,
  onPageChange,
  onPageSizeChange,
  clientPagination = true,
  defaultPageSize = 10,
}: DataTableProps<T>) {
  const isServerPagination = page !== undefined && total !== undefined && onPageChange !== undefined;
  const effectivePageSize = pageSize ?? defaultPageSize;
  const [clientPage, setClientPage] = useState(1);

  useEffect(() => {
    setClientPage(1);
  }, [data.length, searchValue, JSON.stringify(filters)]);

  const clientSlice = useMemo(() => {
    if (isServerPagination || !clientPagination) {
      return { rows: data, total: data.length };
    }
    const start = (clientPage - 1) * effectivePageSize;
    return {
      rows: data.slice(start, start + effectivePageSize),
      total: data.length,
    };
  }, [data, isServerPagination, clientPagination, effectivePageSize, clientPage]);

  const displayData = isServerPagination ? data : clientSlice.rows;
  const paginationPage = isServerPagination ? page! : clientPage;
  const paginationTotal = isServerPagination ? total! : clientSlice.total;
  const showClientPagination = !isServerPagination && clientPagination && data.length > effectivePageSize;

  const exportColumns = getExportColumns(columns);
  const canExport = exportColumns.length > 0 && exportTitle;

  const handlePrint =
    onPrint ??
    (canExport
      ? () => printTable({ title: exportTitle!, columns: exportColumns, data })
      : undefined);

  const handlePdf =
    onPdfDownload ??
    (canExport
      ? () => downloadTablePdf({ title: exportTitle!, columns: exportColumns, data })
      : undefined);

  const showFilterBar =
    searchPlaceholder ||
    onSearchChange !== undefined ||
    filters?.length ||
    onExport ||
    handlePrint ||
    handlePdf ||
    actions;

  const MotionTableRow = motion.create(TableRow);

  return (
    <div className={cn(!embedded && "ds-card-premium overflow-hidden", className)}>
      {showFilterBar && (
        <div className="border-b border-border/70 px-4 py-3">
          <FilterBar
            variant="inline"
            searchPlaceholder={searchPlaceholder}
            searchValue={searchValue}
            onSearchChange={onSearchChange}
            filters={filters}
            onExport={onExport}
            onPrint={handlePrint}
            onPdfDownload={handlePdf}
            actions={actions}
          />
        </div>
      )}
      <div className="overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow className="border-border/70 bg-muted/40 hover:bg-muted/40">
              {columns.map((col) => (
                <TableHead
                  key={col.key}
                  className={cn("text-xs font-semibold uppercase tracking-wide text-muted-foreground", col.className)}
                >
                  {col.header}
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              [...Array(5)].map((_, i) => (
                <TableRow key={i}>
                  {columns.map((col) => (
                    <TableCell key={col.key}>
                      <Skeleton className="h-4 w-full max-w-[120px]" />
                    </TableCell>
                  ))}
                </TableRow>
              ))
            ) : displayData.length === 0 ? (
              <TableRow>
                <TableCell
                  colSpan={columns.length}
                  className="h-36 text-center text-sm text-muted-foreground"
                >
                  {emptyMessage}
                </TableCell>
              </TableRow>
            ) : (
              displayData.map((row, i) => (
                <MotionTableRow
                  key={i}
                  initial={{ opacity: 0, x: -6 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.25, delay: i * 0.03 }}
                  className="border-border/60 transition-colors hover:bg-muted/40"
                >
                  {columns.map((col) => (
                    <TableCell key={col.key} className={col.className}>
                      {col.cell(row)}
                    </TableCell>
                  ))}
                </MotionTableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {(isServerPagination || showClientPagination) && paginationTotal > 0 && (
        <Pagination
          page={paginationPage}
          pageSize={effectivePageSize}
          total={paginationTotal}
          onPageChange={(p) => {
            if (isServerPagination) onPageChange!(p);
            else setClientPage(p);
          }}
          onPageSizeChange={onPageSizeChange}
        />
      )}
    </div>
  );
}
