import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";
import {
  CalendarDays,
  CircleCheck,
  Loader2,
  Package,
  Plus,
  Receipt,
  Trash2,
  Users,
  Wallet,
} from "lucide-react";
import { PageLayout } from "@/components/layout/PageLayout";
import { TabNav } from "@/components/layout/TabNav";
import { KpiCard, KpiGrid } from "@/components/data/KpiCard";
import { ContentSection } from "@/components/layout/ContentSection";
import { DataTable, type Column } from "@/components/data/DataTable";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { formatCurrency } from "@/utils/cn";
import { customersApi } from "@/services/api/partners";
import {
  salesApi,
  type CustomerMonthlyAccount,
  type DailyExpense,
  type DailyOpsData,
  type DailyOpsProduct,
  type DailyOpsUnpaid,
} from "@/services/api/sales";
import { appDialog } from "@/components/feedback/AppDialog";

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

function todayIso() {
  const d = new Date();
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function shiftDate(iso: string, delta: number) {
  const [y, m, d] = iso.split("-").map(Number);
  const dt = new Date(y, m - 1, d);
  dt.setDate(dt.getDate() + delta);
  const yy = dt.getFullYear();
  const mm = String(dt.getMonth() + 1).padStart(2, "0");
  const dd = String(dt.getDate()).padStart(2, "0");
  return `${yy}-${mm}-${dd}`;
}

function formatDisplayDate(iso: string) {
  try {
    const [y, m, d] = iso.split("-").map(Number);
    return new Date(y, m - 1, d).toLocaleDateString(undefined, {
      weekday: "short",
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  } catch {
    return iso;
  }
}

export function DailyOpsPage() {
  const [tab, setTab] = useState("products");
  const [date, setDate] = useState(todayIso);
  const [ops, setOps] = useState<DailyOpsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [markingId, setMarkingId] = useState<string | null>(null);

  const [customers, setCustomers] = useState<{ id: string; name: string }[]>([]);
  const [customerId, setCustomerId] = useState("");
  const [monthYear, setMonthYear] = useState(() => {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
  });
  const [monthly, setMonthly] = useState<CustomerMonthlyAccount | null>(null);
  const [monthlyLoading, setMonthlyLoading] = useState(false);

  const [expenseForm, setExpenseForm] = useState({
    description: "",
    amount: "",
    category: "other",
    notes: "",
  });
  const [savingExpense, setSavingExpense] = useState(false);

  const loadOps = useCallback(async () => {
    setLoading(true);
    try {
      const res = await salesApi.dailyOps(date);
      setOps(res.data);
    } catch {
      setOps(null);
    } finally {
      setLoading(false);
    }
  }, [date]);

  useEffect(() => {
    loadOps();
  }, [loadOps]);

  useEffect(() => {
    customersApi
      .list({ page_size: 200, is_active: "true" })
      .then((res) =>
        setCustomers(res.data.results.map((c) => ({ id: c.id, name: c.full_name })))
      )
      .catch(() => setCustomers([]));
  }, []);

  const loadMonthly = useCallback(async () => {
    if (!customerId) {
      setMonthly(null);
      return;
    }
    const [y, m] = monthYear.split("-").map(Number);
    setMonthlyLoading(true);
    try {
      const res = await salesApi.customerMonthly({
        customer_id: customerId,
        year: y,
        month: m,
      });
      setMonthly(res.data);
    } catch {
      setMonthly(null);
    } finally {
      setMonthlyLoading(false);
    }
  }, [customerId, monthYear]);

  useEffect(() => {
    if (tab === "monthly") loadMonthly();
  }, [tab, loadMonthly]);

  const handleMarkPaid = async (invoiceId: string, number: string, amount: number) => {
    if (!window.confirm(`Mark ${number} as paid for ${formatCurrency(amount)}?`)) return;
    setMarkingId(invoiceId);
    try {
      await salesApi.markInvoicePaid(invoiceId);
      await loadOps();
      if (tab === "monthly") await loadMonthly();
    } catch (err) {
      await appDialog.alert(err instanceof Error ? err.message : "Could not mark as paid");
    } finally {
      setMarkingId(null);
    }
  };

  const handleCreateExpense = async (e: FormEvent) => {
    e.preventDefault();
    const amount = parseFloat(expenseForm.amount);
    if (!expenseForm.description.trim() || !(amount > 0)) {
      await appDialog.alert("Enter a description and amount.");
      return;
    }
    setSavingExpense(true);
    try {
      await salesApi.createExpense({
        description: expenseForm.description.trim(),
        amount,
        category: expenseForm.category,
        expense_date: date,
        notes: expenseForm.notes.trim() || undefined,
      });
      setExpenseForm({ description: "", amount: "", category: "other", notes: "" });
      await loadOps();
    } catch (err) {
      await appDialog.alert(err instanceof Error ? err.message : "Could not save expense");
    } finally {
      setSavingExpense(false);
    }
  };

  const handleDeleteExpense = async (id: string) => {
    if (!window.confirm("Delete this expense?")) return;
    try {
      await salesApi.deleteExpense(id);
      await loadOps();
    } catch (err) {
      await appDialog.alert(err instanceof Error ? err.message : "Could not delete");
    }
  };

  const productColumns: Column<DailyOpsProduct>[] = useMemo(
    () => [
      { key: "name", header: "Product", cell: (r) => <span className="font-medium">{r.name}</span>, exportValue: (r) => r.name },
      { key: "sku", header: "SKU", cell: (r) => <span className="font-mono text-xs">{r.sku}</span>, exportValue: (r) => r.sku },
      { key: "qty", header: "Qty sold", cell: (r) => r.quantity, exportValue: (r) => String(r.quantity) },
      { key: "rev", header: "Revenue", cell: (r) => formatCurrency(r.revenue), exportValue: (r) => formatCurrency(r.revenue) },
    ],
    []
  );

  const unpaidColumns: Column<DailyOpsUnpaid>[] = useMemo(
    () => [
      {
        key: "inv",
        header: "Receipt",
        cell: (r) => <span className="font-mono text-xs font-semibold">{r.invoice_number}</span>,
        exportValue: (r) => r.invoice_number,
      },
      { key: "cust", header: "Customer", cell: (r) => r.customer_name, exportValue: (r) => r.customer_name },
      { key: "waiter", header: "Waiter", cell: (r) => r.waiter_name || "—", exportValue: (r) => r.waiter_name },
      {
        key: "status",
        header: "Status",
        cell: (r) => (
          <Badge variant="warning" className="capitalize">
            {r.status}
          </Badge>
        ),
        exportValue: (r) => r.status,
      },
      { key: "due", header: "Due", cell: (r) => formatCurrency(r.balance_due), exportValue: (r) => formatCurrency(r.balance_due) },
      {
        key: "actions",
        header: "",
        exportable: false,
        cell: (r) => (
          <Button
            size="sm"
            variant="secondary"
            className="h-8 gap-1 text-emerald-700"
            disabled={markingId === r.invoice_id}
            onClick={() => handleMarkPaid(r.invoice_id, r.invoice_number, r.balance_due)}
          >
            {markingId === r.invoice_id ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <CircleCheck className="h-3.5 w-3.5" />
            )}
            Mark paid
          </Button>
        ),
      },
    ],
    [markingId]
  );

  const expenseColumns: Column<DailyExpense>[] = useMemo(
    () => [
      { key: "desc", header: "Description", cell: (r) => r.description, exportValue: (r) => r.description },
      {
        key: "cat",
        header: "Category",
        cell: (r) => <Badge variant="secondary" className="capitalize">{r.category}</Badge>,
        exportValue: (r) => r.category,
      },
      { key: "amt", header: "Amount", cell: (r) => formatCurrency(r.amount), exportValue: (r) => formatCurrency(r.amount) },
      {
        key: "actions",
        header: "",
        exportable: false,
        cell: (r) => (
          <Button
            variant="ghost"
            size="sm"
            className="h-8 w-8 p-0 text-destructive"
            onClick={() => handleDeleteExpense(r.id)}
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        ),
      },
    ],
    []
  );

  const summary = ops?.summary;
  const hasDayActivity =
    (summary?.invoices_count ?? 0) > 0 ||
    (summary?.expense_total ?? 0) > 0 ||
    (ops?.products_sold.length ?? 0) > 0;
  const activityDates = (ops?.activity_dates ?? []).filter((d) => d !== date);

  return (
    <PageLayout
      title="Daily Ops"
      description="Products sold, unpaid receipts, monthly customer accounts, and daily expenses."
      breadcrumbs={["Home", "Daily Ops"]}
      actions={
        <div className="flex items-center gap-2">
          <Button
            type="button"
            variant="secondary"
            size="sm"
            className="h-10 rounded-xl px-3"
            onClick={() => setDate((d) => shiftDate(d, -1))}
          >
            Prev
          </Button>
          <div className="flex items-center gap-2">
            <CalendarDays className="h-4 w-4 text-muted-foreground" />
            <Input
              type="date"
              value={date}
              onChange={(e) => setDate(e.target.value)}
              className="h-10 w-[160px] rounded-xl"
            />
          </div>
          <Button
            type="button"
            variant="secondary"
            size="sm"
            className="h-10 rounded-xl px-3"
            onClick={() => setDate((d) => shiftDate(d, 1))}
            disabled={date >= todayIso()}
          >
            Next
          </Button>
          {date !== todayIso() && (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="h-10 rounded-xl"
              onClick={() => setDate(todayIso())}
            >
              Today
            </Button>
          )}
        </div>
      }
    >
      {!loading && !hasDayActivity && (
        <div className="rounded-2xl border border-amber-500/25 bg-amber-500/5 px-5 py-4">
          <p className="text-sm font-medium text-foreground">
            No sales or expenses on {formatDisplayDate(date)}.
          </p>
          <p className="mt-1 text-xs text-muted-foreground">
            Daily Ops only shows receipts for the selected calendar day. Your recent POS sales may be on an earlier date.
          </p>
          {activityDates.length > 0 && (
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <span className="text-xs font-medium text-muted-foreground">Jump to a day with activity:</span>
              {activityDates.slice(0, 6).map((d) => (
                <Button
                  key={d}
                  type="button"
                  size="sm"
                  variant="secondary"
                  className="h-8 rounded-full"
                  onClick={() => setDate(d)}
                >
                  {formatDisplayDate(d)}
                </Button>
              ))}
            </div>
          )}
        </div>
      )}

      <KpiGrid>
        <KpiCard
          title="Paid sales"
          value={formatCurrency(summary?.paid_total ?? 0)}
          icon={<Receipt className="h-5 w-5" />}
          loading={loading}
        />
        <KpiCard
          title="Unpaid due"
          value={formatCurrency(summary?.unpaid_total ?? 0)}
          icon={<Users className="h-5 w-5" />}
          loading={loading}
        />
        <KpiCard
          title="Products sold"
          value={String(summary?.products_count ?? 0)}
          icon={<Package className="h-5 w-5" />}
          loading={loading}
        />
        <KpiCard
          title="Day expenses"
          value={formatCurrency(summary?.expense_total ?? 0)}
          icon={<Wallet className="h-5 w-5" />}
          loading={loading}
        />
      </KpiGrid>

      <TabNav
        tabs={[
          { id: "products", label: "Products sold", count: ops?.products_sold.length },
          { id: "unpaid", label: "Unpaid receipts", count: ops?.unpaid_receipts.length },
          { id: "monthly", label: "Customer monthly" },
          { id: "expenses", label: "Daily expenses", count: ops?.expenses.length },
        ]}
        active={tab}
        onChange={setTab}
      />

      {tab === "products" && (
        <ContentSection
          title="Products sold"
          description={`Items sold on ${date}`}
          noPadding
        >
          <DataTable
            embedded
            columns={productColumns}
            data={ops?.products_sold ?? []}
            loading={loading}
            emptyMessage="No products sold on this day."
            exportTitle={`Products Sold ${date}`}
          />
        </ContentSection>
      )}

      {tab === "unpaid" && (
        <ContentSection
          title="Unpaid receipts"
          description="Pay-later and open invoices for this day — mark paid when collected."
          noPadding
        >
          <DataTable
            embedded
            columns={unpaidColumns}
            data={ops?.unpaid_receipts ?? []}
            loading={loading}
            emptyMessage="No unpaid receipts for this day."
            exportTitle={`Unpaid ${date}`}
          />
        </ContentSection>
      )}

      {tab === "monthly" && (
        <div className="space-y-4">
          <ContentSection title="Customer monthly account" description="What the customer took, waiters who served, and amount still due.">
            <div className="flex flex-wrap gap-3">
              <Select value={customerId || "none"} onValueChange={(v) => setCustomerId(v === "none" ? "" : v)}>
                <SelectTrigger className="h-11 w-full max-w-xs rounded-xl">
                  <SelectValue placeholder="Select customer" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">Select customer</SelectItem>
                  {customers.map((c) => (
                    <SelectItem key={c.id} value={c.id}>
                      {c.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Input
                type="month"
                value={monthYear}
                onChange={(e) => setMonthYear(e.target.value)}
                className="h-11 w-[180px] rounded-xl"
              />
              <Button className="h-11 rounded-xl" onClick={loadMonthly} disabled={!customerId || monthlyLoading}>
                {monthlyLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : "Load"}
              </Button>
            </div>
          </ContentSection>

          {monthly && (
            <>
              <KpiGrid>
                <KpiCard title="Period" value={monthly.period_label} />
                <KpiCard title="Total taken" value={formatCurrency(monthly.summary.total_amount)} />
                <KpiCard title="Paid" value={formatCurrency(monthly.summary.total_paid)} />
                <KpiCard title="Still due" value={formatCurrency(monthly.summary.total_due)} />
              </KpiGrid>

              <div className="grid gap-4 lg:grid-cols-2">
                <ContentSection title="Products taken" description={monthly.customer_name} noPadding>
                  <DataTable
                    embedded
                    columns={[
                      { key: "n", header: "Product", cell: (r) => r.name, exportValue: (r) => r.name },
                      { key: "q", header: "Qty", cell: (r) => r.quantity, exportValue: (r) => String(r.quantity) },
                      { key: "a", header: "Amount", cell: (r) => formatCurrency(r.amount), exportValue: (r) => formatCurrency(r.amount) },
                    ]}
                    data={monthly.products}
                    emptyMessage="No products this month."
                  />
                </ContentSection>
                <ContentSection title="Waiters (unpaid)" description="Amounts still due by waiter" noPadding>
                  <DataTable
                    embedded
                    columns={[
                      { key: "n", header: "Waiter", cell: (r) => r.name, exportValue: (r) => r.name },
                      { key: "a", header: "Due", cell: (r) => formatCurrency(r.amount_due), exportValue: (r) => formatCurrency(r.amount_due) },
                    ]}
                    data={monthly.waiters}
                    emptyMessage="No unpaid waiter amounts."
                  />
                </ContentSection>
              </div>

              <ContentSection title="Receipts" description="All invoices in this month" noPadding>
                <DataTable
                  embedded
                  columns={[
                    {
                      key: "inv",
                      header: "Receipt",
                      cell: (r) => <span className="font-mono text-xs">{r.invoice_number}</span>,
                      exportValue: (r) => r.invoice_number,
                    },
                    { key: "d", header: "Date", cell: (r) => r.issue_date, exportValue: (r) => r.issue_date },
                    { key: "w", header: "Waiter", cell: (r) => r.waiter_name, exportValue: (r) => r.waiter_name },
                    {
                      key: "s",
                      header: "Status",
                      cell: (r) => (
                        <Badge variant={r.status === "paid" ? "success" : "warning"} className="capitalize">
                          {r.status}
                        </Badge>
                      ),
                      exportValue: (r) => r.status,
                    },
                    { key: "t", header: "Total", cell: (r) => formatCurrency(r.total_amount), exportValue: (r) => formatCurrency(r.total_amount) },
                    { key: "due", header: "Due", cell: (r) => formatCurrency(r.balance_due), exportValue: (r) => formatCurrency(r.balance_due) },
                    {
                      key: "act",
                      header: "",
                      exportable: false,
                      cell: (r) =>
                        r.status !== "paid" && r.balance_due > 0 ? (
                          <Button
                            size="sm"
                            variant="secondary"
                            className="h-8 gap-1"
                            disabled={markingId === r.invoice_id}
                            onClick={() => handleMarkPaid(r.invoice_id, r.invoice_number, r.balance_due)}
                          >
                            <CircleCheck className="h-3.5 w-3.5" />
                            Paid
                          </Button>
                        ) : null,
                    },
                  ]}
                  data={monthly.receipts}
                  emptyMessage="No receipts for this customer in the selected month."
                />
              </ContentSection>
            </>
          )}
        </div>
      )}

      {tab === "expenses" && (
        <div className="space-y-4">
          <ContentSection title="Add daily expense" description={`Record an expense for ${date}`}>
            <form onSubmit={handleCreateExpense} className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <Input
                value={expenseForm.description}
                onChange={(e) => setExpenseForm((f) => ({ ...f, description: e.target.value }))}
                placeholder="Description"
                className="h-11 rounded-xl sm:col-span-2"
                required
              />
              <Input
                type="number"
                min={0}
                step="0.01"
                value={expenseForm.amount}
                onChange={(e) => setExpenseForm((f) => ({ ...f, amount: e.target.value }))}
                placeholder="Amount"
                className="h-11 rounded-xl"
                required
              />
              <Select
                value={expenseForm.category}
                onValueChange={(v) => setExpenseForm((f) => ({ ...f, category: v }))}
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
                value={expenseForm.notes}
                onChange={(e) => setExpenseForm((f) => ({ ...f, notes: e.target.value }))}
                placeholder="Notes (optional)"
                className="h-11 rounded-xl sm:col-span-2 lg:col-span-3"
              />
              <Button type="submit" className="h-11 rounded-xl gap-2" disabled={savingExpense}>
                {savingExpense ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
                Add expense
              </Button>
            </form>
          </ContentSection>

          <ContentSection title="Expenses today" description={`Expenses on ${date}`} noPadding>
            <DataTable
              embedded
              columns={expenseColumns}
              data={ops?.expenses ?? []}
              loading={loading}
              emptyMessage="No expenses recorded for this day."
              exportTitle={`Expenses ${date}`}
            />
          </ContentSection>
        </div>
      )}
    </PageLayout>
  );
}
