import { useCallback, useEffect, useMemo, useState } from "react";
import { Loader2, RotateCcw, Search, Trash2 } from "lucide-react";
import { PageLayout } from "@/components/layout/PageLayout";
import { TabNav } from "@/components/layout/TabNav";
import { ContentSection } from "@/components/layout/ContentSection";
import { DataTable, type Column } from "@/components/data/DataTable";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { appDialog } from "@/components/feedback/AppDialog";
import { usePermissions } from "@/hooks/usePermissions";
import { salesApi, type TrashItem } from "@/services/api/sales";
import { cn, formatCurrency } from "@/utils/cn";

type KindTab = "all" | "invoice" | "quotation" | "expense";

function kindLabel(kind: string) {
  if (kind === "invoice" || kind === "receipt") return "Receipt";
  if (kind === "quotation") return "Quotation";
  if (kind === "expense") return "Expense";
  return kind;
}

function formatWhen(iso?: string | null) {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

export function TrashPage() {
  const { hasPermission } = usePermissions();
  const canRestore = hasPermission("trash.restore");

  const [tab, setTab] = useState<KindTab>("all");
  const [search, setSearch] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [rows, setRows] = useState<TrashItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await salesApi.trash({
        kind: tab === "all" ? undefined : tab,
        search: search || undefined,
      });
      setRows(res.data || []);
    } catch (err) {
      setRows([]);
      await appDialog.alert(err instanceof Error ? err.message : "Could not load trash");
    } finally {
      setLoading(false);
    }
  }, [tab, search]);

  useEffect(() => {
    void load();
  }, [load]);

  const restoreKind = (item: TrashItem) =>
    item.kind === "receipt" ? "invoice" : String(item.kind || "invoice");

  const handleRestore = async (item: TrashItem) => {
    if (!canRestore) return;
    const ok = await appDialog.confirm(
      `Restore ${kindLabel(String(item.kind))} "${item.number || item.title}"?`,
      { title: "Restore item", confirmLabel: "Restore" }
    );
    if (!ok) return;
    setBusyId(item.id);
    try {
      await salesApi.restoreTrash(restoreKind(item), item.id);
      await load();
    } catch (err) {
      await appDialog.alert(err instanceof Error ? err.message : "Could not restore");
    } finally {
      setBusyId(null);
    }
  };

  const handlePurge = async (item: TrashItem) => {
    if (!canRestore) return;
    const ok = await appDialog.confirm(
      `Permanently delete ${kindLabel(String(item.kind))} "${item.number || item.title}"? This cannot be undone.`,
      { title: "Delete forever", tone: "danger", confirmLabel: "Delete forever" }
    );
    if (!ok) return;
    setBusyId(item.id);
    try {
      await salesApi.purgeTrash(restoreKind(item), item.id);
      await load();
    } catch (err) {
      await appDialog.alert(err instanceof Error ? err.message : "Could not delete");
    } finally {
      setBusyId(null);
    }
  };

  const columns: Column<TrashItem>[] = useMemo(
    () => [
      {
        key: "kind",
        header: "Type",
        cell: (r) => (
          <span
            className={cn(
              "inline-flex rounded-full px-2.5 py-1 text-[11px] font-semibold",
              r.kind === "expense"
                ? "bg-amber-500/15 text-amber-700"
                : r.kind === "quotation"
                  ? "bg-sky-500/15 text-sky-700"
                  : "bg-violet-500/15 text-violet-700"
            )}
          >
            {kindLabel(String(r.kind))}
          </span>
        ),
        exportValue: (r) => kindLabel(String(r.kind)),
      },
      {
        key: "number",
        header: "Reference",
        cell: (r) => (
          <div className="min-w-[140px]">
            <p className="font-mono text-sm font-semibold">{r.number || r.title}</p>
            <p className="text-[11px] text-muted-foreground">
              {r.customer_name || r.category || r.branch_name || "—"}
            </p>
          </div>
        ),
        exportValue: (r) => r.number || r.title || "",
      },
      {
        key: "date",
        header: "Doc date",
        cell: (r) => (
          <span className="text-sm tabular-nums text-muted-foreground">
            {r.date || r.issue_date || "—"}
          </span>
        ),
        exportValue: (r) => r.date || r.issue_date || "",
      },
      {
        key: "amount",
        header: "Amount",
        className: "text-right",
        cell: (r) => {
          const amt = r.total_amount ?? r.amount;
          return (
            <span className="text-sm font-semibold tabular-nums">
              {amt != null ? formatCurrency(amt) : "—"}
            </span>
          );
        },
        exportValue: (r) => {
          const amt = r.total_amount ?? r.amount;
          return amt != null ? formatCurrency(amt) : "";
        },
      },
      {
        key: "deleted",
        header: "Deleted",
        cell: (r) => (
          <div className="min-w-[140px]">
            <p className="text-sm">{formatWhen(r.deleted_at)}</p>
            <p className="text-[11px] text-muted-foreground">{r.deleted_by || "—"}</p>
          </div>
        ),
        exportValue: (r) => r.deleted_at || "",
      },
      {
        key: "actions",
        header: "",
        exportable: false,
        cell: (r) => {
          if (!canRestore) return null;
          const busy = busyId === r.id;
          return (
            <div className="flex justify-end gap-1">
              <Button
                variant="ghost"
                size="sm"
                className="h-8 gap-1 px-2 text-emerald-700 hover:bg-emerald-500/10"
                disabled={busy}
                onClick={() => void handleRestore(r)}
              >
                {busy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RotateCcw className="h-3.5 w-3.5" />}
                <span className="text-xs font-semibold">Restore</span>
              </Button>
              <Button
                variant="ghost"
                size="sm"
                className="h-8 w-8 p-0 text-destructive"
                title="Delete forever"
                disabled={busy}
                onClick={() => void handlePurge(r)}
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </div>
          );
        },
      },
    ],
    [canRestore, busyId]
  );

  const counts = useMemo(() => {
    const all = rows.length;
    return {
      all,
      invoice: rows.filter((r) => r.kind === "invoice" || r.kind === "receipt").length,
      quotation: rows.filter((r) => r.kind === "quotation").length,
      expense: rows.filter((r) => r.kind === "expense").length,
    };
  }, [rows]);

  return (
    <PageLayout
      title="Trash"
      description="View deleted receipts, quotations, and expenses — restore them or delete permanently."
      breadcrumbs={["Home", "Trash"]}
    >
      <div className="rounded-2xl border border-border/70 bg-gradient-to-br from-card via-card to-muted/20 p-4 shadow-sm sm:p-5">
        <div className="flex flex-col gap-3 sm:flex-row">
          <div className="relative flex-1">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && setSearch(searchInput.trim())}
              placeholder="Search deleted items"
              className="h-11 rounded-xl pl-9"
            />
          </div>
          <Button className="h-11 rounded-xl font-semibold" onClick={() => setSearch(searchInput.trim())}>
            Search
          </Button>
        </div>
      </div>

      <TabNav
        tabs={[
          { id: "all", label: "All", count: tab === "all" ? counts.all : undefined },
          { id: "invoice", label: "Receipts" },
          { id: "quotation", label: "Quotations" },
          { id: "expense", label: "Expenses" },
        ]}
        active={tab}
        onChange={(id) => setTab(id as KindTab)}
      />

      <ContentSection
        title="Deleted records"
        description={
          canRestore
            ? "Listed by receipt number, newest first (…00060, 00059, …). Restore returns the item; Delete forever removes it permanently."
            : "You can view trash. Ask an admin for trash.restore to restore items."
        }
        noPadding
      >
        <DataTable
          embedded
          exportTitle="Trash"
          columns={columns}
          data={rows}
          loading={loading}
          emptyMessage="Trash is empty."
          searchPlaceholder="Filter this page..."
          clientPagination
          defaultPageSize={20}
        />
      </ContentSection>
    </PageLayout>
  );
}
