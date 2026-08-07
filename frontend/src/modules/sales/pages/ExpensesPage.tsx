import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import {
  CalendarRange,
  Loader2,
  Pencil,
  Plus,
  Search,
  Trash2,
  Wallet,
} from "lucide-react";
import { PageLayout } from "@/components/layout/PageLayout";
import { TabNav } from "@/components/layout/TabNav";
import { ContentSection } from "@/components/layout/ContentSection";
import { KpiCard, KpiGrid } from "@/components/data/KpiCard";
import { DataTable, type Column } from "@/components/data/DataTable";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { appDialog } from "@/components/feedback/AppDialog";
import { usePermissions } from "@/hooks/usePermissions";
import { salesApi, type DailyExpense } from "@/services/api/sales";
import { formatCurrency } from "@/utils/cn";

const EXPENSE_CATEGORIES = [
  { value: "utilities", label: "Utilities" },
  { value: "rent", label: "Rent" },
  { value: "supplies", label: "Supplies" },
  { value: "salaries", label: "Salaries" },
  { value: "transport", label: "Transport" },
  { value: "food", label: "Food & Beverage" },
  { value: "maintenance", label: "Maintenance" },
  { value: "other", label: "Other" },
];

type PeriodTab = "today" | "week" | "month" | "custom";

function isoDate(d: Date) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function todayIso() {
  return isoDate(new Date());
}

function startOfWeekIso() {
  const d = new Date();
  const day = d.getDay();
  const diff = day === 0 ? 6 : day - 1; // Monday start
  d.setDate(d.getDate() - diff);
  return isoDate(d);
}

function startOfMonthIso() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-01`;
}

function categoryLabel(value: string) {
  return EXPENSE_CATEGORIES.find((c) => c.value === value)?.label || value;
}

type ExpenseForm = {
  description: string;
  amount: string;
  category: string;
  expense_date: string;
  notes: string;
};

const emptyForm = (): ExpenseForm => ({
  description: "",
  amount: "",
  category: "other",
  expense_date: todayIso(),
  notes: "",
});

export function ExpensesPage() {
  const { hasAnyPermission } = usePermissions();
  const canCreate = hasAnyPermission("finance.create", "sales.create", "sales.view");
  const canUpdate = hasAnyPermission("finance.create", "sales.create", "sales.update");
  const canDelete = hasAnyPermission("finance.create", "sales.create", "sales.delete", "sales.view");

  const [period, setPeriod] = useState<PeriodTab>("today");
  const [dateFrom, setDateFrom] = useState(todayIso);
  const [dateTo, setDateTo] = useState(todayIso);
  const [category, setCategory] = useState("all");
  const [search, setSearch] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [rows, setRows] = useState<DailyExpense[]>([]);
  const [totalAmount, setTotalAmount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState<ExpenseForm>(emptyForm);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (period === "today") {
      const t = todayIso();
      setDateFrom(t);
      setDateTo(t);
    } else if (period === "week") {
      setDateFrom(startOfWeekIso());
      setDateTo(todayIso());
    } else if (period === "month") {
      setDateFrom(startOfMonthIso());
      setDateTo(todayIso());
    }
  }, [period]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await salesApi.expenses({
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
        category: category !== "all" ? category : undefined,
        search: search || undefined,
      });
      setRows(res.data.results || []);
      setTotalAmount(res.data.total_amount || 0);
    } catch (err) {
      setRows([]);
      setTotalAmount(0);
      await appDialog.alert(err instanceof Error ? err.message : "Could not load expenses");
    } finally {
      setLoading(false);
    }
  }, [dateFrom, dateTo, category, search]);

  useEffect(() => {
    void load();
  }, [load]);

  const resetForm = () => {
    setEditingId(null);
    setForm(emptyForm());
  };

  const startEdit = (row: DailyExpense) => {
    setEditingId(row.id);
    setForm({
      description: row.description,
      amount: String(row.amount),
      category: row.category || "other",
      expense_date: row.expense_date,
      notes: row.notes || "",
    });
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!canCreate && !editingId) return;
    const amount = parseFloat(form.amount);
    if (!form.description.trim() || !(amount > 0)) {
      await appDialog.alert("Description and a positive amount are required.");
      return;
    }
    setSaving(true);
    try {
      const payload = {
        description: form.description.trim(),
        amount,
        category: form.category,
        expense_date: form.expense_date,
        notes: form.notes.trim() || undefined,
      };
      if (editingId) {
        if (!canUpdate) return;
        await salesApi.updateExpense(editingId, payload);
      } else {
        await salesApi.createExpense(payload);
      }
      resetForm();
      await load();
    } catch (err) {
      await appDialog.alert(err instanceof Error ? err.message : "Could not save expense");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (row: DailyExpense) => {
    if (!canDelete) return;
    const ok = await appDialog.confirm(`Delete expense "${row.description}"?`, {
      title: "Delete expense",
      tone: "danger",
      confirmLabel: "Delete",
    });
    if (!ok) return;
    try {
      await salesApi.deleteExpense(row.id);
      if (editingId === row.id) resetForm();
      await load();
    } catch (err) {
      await appDialog.alert(err instanceof Error ? err.message : "Could not delete expense");
    }
  };

  const columns: Column<DailyExpense>[] = useMemo(
    () => [
      {
        key: "date",
        header: "Date",
        cell: (r) => <span className="tabular-nums text-sm">{r.expense_date}</span>,
        exportValue: (r) => r.expense_date,
      },
      {
        key: "description",
        header: "Description",
        cell: (r) => (
          <div className="min-w-[160px]">
            <p className="text-sm font-medium">{r.description}</p>
            {r.notes ? <p className="text-[11px] text-muted-foreground">{r.notes}</p> : null}
          </div>
        ),
        exportValue: (r) => r.description,
      },
      {
        key: "category",
        header: "Category",
        cell: (r) => (
          <span className="rounded-full bg-muted px-2.5 py-1 text-[11px] font-semibold">
            {categoryLabel(r.category)}
          </span>
        ),
        exportValue: (r) => categoryLabel(r.category),
      },
      {
        key: "by",
        header: "Recorded by",
        cell: (r) => <span className="text-sm text-muted-foreground">{r.created_by || "—"}</span>,
        exportValue: (r) => r.created_by || "",
      },
      {
        key: "amount",
        header: "Amount",
        className: "text-right",
        cell: (r) => (
          <span className="text-sm font-semibold tabular-nums">{formatCurrency(r.amount)}</span>
        ),
        exportValue: (r) => formatCurrency(r.amount),
      },
      {
        key: "actions",
        header: "",
        exportable: false,
        cell: (r) => (
          <div className="flex justify-end gap-0.5">
            {canUpdate && (
              <Button
                variant="ghost"
                size="sm"
                className="h-8 w-8 p-0"
                title="Edit"
                onClick={() => startEdit(r)}
              >
                <Pencil className="h-4 w-4" />
              </Button>
            )}
            {canDelete && (
              <Button
                variant="ghost"
                size="sm"
                className="h-8 w-8 p-0 text-destructive"
                title="Delete"
                onClick={() => void handleDelete(r)}
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            )}
          </div>
        ),
      },
    ],
    [canUpdate, canDelete]
  );

  const periodLabel =
    period === "today"
      ? "Today"
      : period === "week"
        ? "This week"
        : period === "month"
          ? "This month"
          : "Custom range";

  return (
    <PageLayout
      title="Expenses"
      description="Track daily, weekly, and monthly operating expenses — create, print, download, or delete."
      breadcrumbs={["Home", "Expenses"]}
    >
      <KpiGrid columns={3}>
        <KpiCard title="Period" value={periodLabel} icon={<CalendarRange className="h-5 w-5" />} />
        <KpiCard title="Entries" value={String(rows.length)} icon={<Wallet className="h-5 w-5" />} loading={loading} />
        <KpiCard
          title="Total spent"
          value={formatCurrency(totalAmount)}
          icon={<Wallet className="h-5 w-5" />}
          accent="warning"
          loading={loading}
        />
      </KpiGrid>

      <TabNav
        tabs={[
          { id: "today", label: "Daily" },
          { id: "week", label: "Weekly" },
          { id: "month", label: "Monthly" },
          { id: "custom", label: "Custom" },
        ]}
        active={period}
        onChange={(id) => setPeriod(id as PeriodTab)}
      />

      <div className="rounded-2xl border border-border/70 bg-gradient-to-br from-card via-card to-muted/20 p-4 shadow-sm sm:p-5">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-6">
          <div className="relative lg:col-span-2">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && setSearch(searchInput.trim())}
              placeholder="Search description or notes"
              className="h-11 rounded-xl pl-9"
            />
          </div>
          <Input
            type="date"
            value={dateFrom}
            onChange={(e) => {
              setPeriod("custom");
              setDateFrom(e.target.value);
            }}
            className="h-11 rounded-xl"
          />
          <Input
            type="date"
            value={dateTo}
            onChange={(e) => {
              setPeriod("custom");
              setDateTo(e.target.value);
            }}
            className="h-11 rounded-xl"
          />
          <Select value={category} onValueChange={setCategory}>
            <SelectTrigger className="h-11 rounded-xl">
              <SelectValue placeholder="Category" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All categories</SelectItem>
              {EXPENSE_CATEGORIES.map((c) => (
                <SelectItem key={c.value} value={c.value}>
                  {c.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button className="h-11 rounded-xl font-semibold" onClick={() => setSearch(searchInput.trim())}>
            Apply
          </Button>
        </div>
      </div>

      {(canCreate || editingId) && (
        <ContentSection
          title={editingId ? "Edit expense" : "Add expense"}
          description={editingId ? "Update the selected expense." : "Record a new operating expense."}
        >
          <form onSubmit={handleSubmit} className="grid gap-3 sm:grid-cols-2 lg:grid-cols-6">
            <Input
              value={form.description}
              onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
              placeholder="Description"
              className="h-11 rounded-xl lg:col-span-2"
              required
            />
            <Input
              type="number"
              min="0"
              step="0.01"
              value={form.amount}
              onChange={(e) => setForm((f) => ({ ...f, amount: e.target.value }))}
              placeholder="Amount"
              className="h-11 rounded-xl"
              required
            />
            <Select
              value={form.category}
              onValueChange={(v) => setForm((f) => ({ ...f, category: v }))}
            >
              <SelectTrigger className="h-11 rounded-xl">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {EXPENSE_CATEGORIES.map((c) => (
                  <SelectItem key={c.value} value={c.value}>
                    {c.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Input
              type="date"
              value={form.expense_date}
              onChange={(e) => setForm((f) => ({ ...f, expense_date: e.target.value }))}
              className="h-11 rounded-xl"
              required
            />
            <Input
              value={form.notes}
              onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))}
              placeholder="Notes (optional)"
              className="h-11 rounded-xl lg:col-span-3"
            />
            <div className="flex gap-2 lg:col-span-3">
              <Button type="submit" className="h-11 flex-1 rounded-xl gap-2" disabled={saving}>
                {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : editingId ? <Pencil className="h-4 w-4" /> : <Plus className="h-4 w-4" />}
                {editingId ? "Save changes" : "Add expense"}
              </Button>
              {editingId && (
                <Button type="button" variant="secondary" className="h-11 rounded-xl" onClick={resetForm}>
                  Cancel
                </Button>
              )}
            </div>
          </form>
        </ContentSection>
      )}

      <ContentSection
        title={`${periodLabel} expenses`}
        description={`${dateFrom} → ${dateTo}`}
        noPadding
      >
        <DataTable
          embedded
          exportTitle={`Expenses ${dateFrom} to ${dateTo}`}
          columns={columns}
          data={rows}
          loading={loading}
          emptyMessage="No expenses for this period."
          searchPlaceholder="Filter this page..."
          clientPagination
          defaultPageSize={20}
        />
      </ContentSection>
    </PageLayout>
  );
}
