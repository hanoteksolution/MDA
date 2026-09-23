import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { AlertTriangle, Inbox, RefreshCw, Search } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { cn } from "@/utils/cn";
import { API_LIST_CAP, maybeTruncated, paginate, searchRows } from "../lib";
import type { StatusView } from "../lib";

export function StatusBadge({ view }: { view: StatusView }) {
  return <Badge variant={view.variant}>{view.label}</Badge>;
}

export interface EmptyCopy {
  title: string;
  description?: string;
  action?: ReactNode;
}

interface DataStateProps {
  loading: boolean;
  error: string | null;
  isEmpty: boolean;
  empty: EmptyCopy;
  onRetry?: () => void;
  children: ReactNode;
}

/** One place that decides loading → error → empty → content, so every tab behaves the same. */
export function DataState({ loading, error, isEmpty, empty, onRetry, children }: DataStateProps) {
  if (loading) {
    return (
      <div role="status" aria-label="Loading" className="space-y-3 p-4" data-state="loading">
        {[0, 1, 2].map((i) => (
          <Skeleton key={i} className="h-10 w-full" />
        ))}
      </div>
    );
  }
  if (error) {
    return (
      <div role="alert" data-state="error" className="flex flex-col items-center gap-3 px-4 py-12 text-center">
        <span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-destructive/10 text-destructive">
          <AlertTriangle className="h-5 w-5" />
        </span>
        <div>
          <p className="text-sm font-medium text-foreground">Could not load this data</p>
          <p className="mt-1 text-sm text-muted-foreground">{error}</p>
        </div>
        {onRetry && (
          <Button variant="outline" size="sm" onClick={onRetry}>
            <RefreshCw className="mr-2 h-3.5 w-3.5" /> Try again
          </Button>
        )}
      </div>
    );
  }
  if (isEmpty) {
    return (
      <div role="status" data-state="empty" className="flex flex-col items-center gap-2 px-4 py-12 text-center">
        <span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-muted/70 text-muted-foreground">
          <Inbox className="h-5 w-5" />
        </span>
        <p className="text-sm font-medium text-foreground">{empty.title}</p>
        {empty.description && <p className="max-w-md text-sm text-muted-foreground">{empty.description}</p>}
        {empty.action}
      </div>
    );
  }
  return <>{children}</>;
}

export function Panel({
  title,
  description,
  actions,
  children,
  className,
}: {
  title?: string;
  description?: string;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={cn("overflow-hidden rounded-2xl border border-border bg-card shadow-sm", className)}>
      {(title || actions) && (
        <header className="flex flex-wrap items-center justify-between gap-3 border-b border-border px-4 py-3">
          <div>
            {title && <h3 className="text-sm font-semibold tracking-tight text-foreground">{title}</h3>}
            {description && <p className="mt-0.5 text-xs text-muted-foreground">{description}</p>}
          </div>
          {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
        </header>
      )}
      {children}
    </section>
  );
}

export function Notice({ tone = "info", children }: { tone?: "info" | "warning"; children: ReactNode }) {
  return (
    <p
      className={cn(
        "rounded-xl border px-3 py-2 text-xs",
        tone === "warning"
          ? "border-warning/30 bg-warning/10 text-warning"
          : "border-border bg-muted/40 text-muted-foreground"
      )}
    >
      {children}
    </p>
  );
}

export interface ListColumn<T> {
  key: string;
  header: string;
  cell: (row: T) => ReactNode;
  className?: string;
}

interface ListTableProps<T> {
  rows: T[];
  columns: ListColumn<T>[];
  rowKey: (row: T) => string;
  searchPlaceholder?: string;
  searchText?: (row: T) => (string | null | undefined)[];
  /** Optional status filter, applied client-side over the rows already loaded. */
  statusOptions?: { value: string; label: string }[];
  statusOf?: (row: T) => string;
  pageSize?: number;
}

/** Search + status filter + pagination over an already-loaded list (the API caps lists at 200). */
export function ListTable<T>({
  rows,
  columns,
  rowKey,
  searchPlaceholder = "Search…",
  searchText,
  statusOptions,
  statusOf,
  pageSize = 10,
}: ListTableProps<T>) {
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);

  useEffect(() => setPage(1), [query, status]);

  let filtered = searchText ? searchRows(rows, query, searchText) : rows;
  if (status && statusOf) filtered = filtered.filter((r) => statusOf(r) === status);
  const view = paginate(filtered, page, pageSize);

  return (
    <div>
      {(searchText || statusOptions) && (
        <div className="flex flex-wrap items-center gap-2 border-b border-border px-4 py-3">
          {searchText && (
            <div className="relative min-w-[200px] flex-1 sm:max-w-xs">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                aria-label="Search"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder={searchPlaceholder}
                className="h-9 pl-9"
              />
            </div>
          )}
          {statusOptions && (
            <select
              aria-label="Filter by status"
              value={status}
              onChange={(e) => setStatus(e.target.value)}
              className="h-9 rounded-lg border border-input bg-background px-3 text-sm"
            >
              <option value="">All statuses</option>
              {statusOptions.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          )}
        </div>
      )}
      {maybeTruncated(rows.length) && (
        <div className="px-4 pt-3">
          <Notice tone="warning">
            Showing the most recent {API_LIST_CAP} records — the API does not page beyond that yet.
          </Notice>
        </div>
      )}
      {view.total === 0 ? (
        <p role="status" className="px-4 py-10 text-center text-sm text-muted-foreground">
          No records match your filters.
        </p>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              {columns.map((c) => (
                <TableHead key={c.key} className={c.className}>
                  {c.header}
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {view.rows.map((row) => (
              <TableRow key={rowKey(row)}>
                {columns.map((c) => (
                  <TableCell key={c.key} className={c.className}>
                    {c.cell(row)}
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
      {view.pageCount > 1 && (
        <div className="flex items-center justify-between border-t border-border px-4 py-2 text-xs text-muted-foreground">
          <span>
            Page {view.page} of {view.pageCount} · {view.total} records
          </span>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" disabled={view.page <= 1} onClick={() => setPage(view.page - 1)}>
              Previous
            </Button>
            <Button variant="outline" size="sm" disabled={view.page >= view.pageCount} onClick={() => setPage(view.page + 1)}>
              Next
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
