import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowUpRight,
  ArrowDownRight,
  Plus,
  Loader2,
} from "lucide-react";
import { PageLayout } from "@/components/layout/PageLayout";
import { TabNav } from "@/components/layout/TabNav";
import { KpiCard, KpiGrid } from "@/components/data/KpiCard";
import { ContentSection } from "@/components/layout/ContentSection";
import { ChartCard } from "@/components/data/ChartCard";
import { ProfitChart } from "@/components/data/charts/DashboardCharts";
import { DataTable, type Column } from "@/components/data/DataTable";
import { EmptyState } from "@/components/layout/EmptyState";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { formatCurrency } from "@/utils/cn";
import {
  financeApi,
  type AccountingEquationReport,
  type AccountingHealthReport,
  type BalanceSheetReport,
  type CashFlowReport,
  type FinanceAccount,
  type FinanceExpense,
  type FinanceJournalEntry,
  type FinanceSummary,
  type FinancialPeriod,
  type GeneralLedgerReport,
  type ProfitLossReport,
  type TrialBalanceReport,
  type AgingReport,
  type BankReconciliation,
  type TaxReport,
} from "@/services/api/finance";

const EXPENSE_STATUS: Record<string, "warning" | "secondary" | "success"> = {
  pending: "warning",
  approved: "secondary",
  paid: "success",
};

const PERIOD_STATUS: Record<string, "success" | "warning" | "secondary" | "destructive"> = {
  open: "success",
  soft_closed: "warning",
  closed: "secondary",
  locked: "destructive",
};

function DateRangeFilters({
  dateFrom,
  dateTo,
  onFrom,
  onTo,
  onRefresh,
  loading,
}: {
  dateFrom: string;
  dateTo: string;
  onFrom: (v: string) => void;
  onTo: (v: string) => void;
  onRefresh: () => void;
  loading?: boolean;
}) {
  return (
    <div className="flex flex-wrap items-end gap-3 mb-4">
      <div>
        <label className="text-xs text-muted-foreground mb-1 block">From</label>
        <Input type="date" value={dateFrom} onChange={(e) => onFrom(e.target.value)} className="w-auto" />
      </div>
      <div>
        <label className="text-xs text-muted-foreground mb-1 block">To</label>
        <Input type="date" value={dateTo} onChange={(e) => onTo(e.target.value)} className="w-auto" />
      </div>
      <Button type="button" variant="secondary" onClick={onRefresh} disabled={loading}>
        {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
        Refresh
      </Button>
    </div>
  );
}

export function FinancePage() {
  const [tab, setTab] = useState("overview");
  const [data, setData] = useState<FinanceSummary | null>(null);
  const [loading, setLoading] = useState(true);

  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [businessUnitId, setBusinessUnitId] = useState("");
  const [businessUnits, setBusinessUnits] = useState<
    { id: string; code: string; name: string }[]
  >([]);
  const [reportLoading, setReportLoading] = useState(false);
  const [trialBalance, setTrialBalance] = useState<TrialBalanceReport | null>(null);
  const [profitLoss, setProfitLoss] = useState<ProfitLossReport | null>(null);
  const [balanceSheet, setBalanceSheet] = useState<BalanceSheetReport | null>(null);
  const [cashFlow, setCashFlow] = useState<CashFlowReport | null>(null);
  const [periods, setPeriods] = useState<FinancialPeriod[]>([]);
  const [health, setHealth] = useState<AccountingHealthReport | null>(null);
  const [equation, setEquation] = useState<AccountingEquationReport | null>(null);
  const [ledgerReport, setLedgerReport] = useState<GeneralLedgerReport | null>(null);
  const [ledgerAccountId, setLedgerAccountId] = useState("");
  const [journalEntries, setJournalEntries] = useState<FinanceJournalEntry[]>([]);
  const [journalBusy, setJournalBusy] = useState<string | null>(null);
  const [journalMsg, setJournalMsg] = useState<string | null>(null);
  const [backfillPreview, setBackfillPreview] = useState<Record<string, unknown> | null>(null);
  const [backfillBusy, setBackfillBusy] = useState(false);
  const [backfillMsg, setBackfillMsg] = useState<string | null>(null);
  const [cutover, setCutover] = useState<Record<string, unknown> | null>(null);
  const [cutoverBusy, setCutoverBusy] = useState(false);
  const [cutoverMsg, setCutoverMsg] = useState<string | null>(null);
  const [arAging, setArAging] = useState<AgingReport | null>(null);
  const [apAging, setApAging] = useState<AgingReport | null>(null);
  const [periodBusy, setPeriodBusy] = useState<string | null>(null);
  const [voucherMsg, setVoucherMsg] = useState<string | null>(null);
  const [voucherBusy, setVoucherBusy] = useState(false);
  const [receiptForm, setReceiptForm] = useState({
    invoice_id: "",
    amount: "",
    method: "cash",
    reference: "",
  });
  const [supplierForm, setSupplierForm] = useState({
    purchase_order_id: "",
    amount: "",
    method: "cash",
    reference: "",
  });
  const [cashAccounts, setCashAccounts] = useState<
    { id: string; code: string; name: string; balance: number }[]
  >([]);
  const [recList, setRecList] = useState<BankReconciliation[]>([]);
  const [activeRec, setActiveRec] = useState<BankReconciliation | null>(null);
  const [recForm, setRecForm] = useState({
    account_id: "",
    statement_date: "",
    statement_balance: "",
  });
  const [stmtForm, setStmtForm] = useState({
    line_date: "",
    amount: "",
    description: "",
    reference: "",
  });
  const [recMsg, setRecMsg] = useState<string | null>(null);
  const [recBusy, setRecBusy] = useState(false);
  const [taxReport, setTaxReport] = useState<TaxReport | null>(null);

  useEffect(() => {
    setLoading(true);
    financeApi
      .summary("month")
      .then((res) => setData(res.data))
      .catch(() => setData(null))
      .finally(() => setLoading(false));
    financeApi
      .equation()
      .then((r) => setEquation(r.data))
      .catch(() => setEquation(null));
    financeApi
      .businessUnits({ is_active: "true" })
      .then((r) => setBusinessUnits(r.data.results ?? []))
      .catch(() => setBusinessUnits([]));
  }, []);

  const loadLedgerReports = useCallback(() => {
    setReportLoading(true);
    const params = {
      date_from: dateFrom || undefined,
      date_to: dateTo || undefined,
      business_unit_id: businessUnitId || undefined,
    };
    Promise.all([
      financeApi.trialBalance({ date_from: params.date_from, date_to: params.date_to }).then((r) => setTrialBalance(r.data)).catch(() => setTrialBalance(null)),
      financeApi.profitLoss(params).then((r) => setProfitLoss(r.data)).catch(() => setProfitLoss(null)),
      financeApi
        .balanceSheet({ as_of: dateTo || undefined })
        .then((r) => setBalanceSheet(r.data))
        .catch(() => setBalanceSheet(null)),
      financeApi.cashFlow({ date_from: params.date_from, date_to: params.date_to }).then((r) => setCashFlow(r.data)).catch(() => setCashFlow(null)),
    ]).finally(() => setReportLoading(false));
  }, [dateFrom, dateTo, businessUnitId]);

  const loadPeriods = useCallback(() => {
    financeApi
      .periods()
      .then((r) => setPeriods(r.data ?? []))
      .catch(() => setPeriods([]));
  }, []);

  const loadHealth = useCallback(() => {
    financeApi
      .health()
      .then((r) => setHealth(r.data))
      .catch(() => setHealth(null));
    financeApi
      .cutoverStatus()
      .then((r) => setCutover(r.data))
      .catch(() => setCutover(null));
  }, []);

  const runBackfillPreview = async () => {
    setBackfillBusy(true);
    setBackfillMsg(null);
    try {
      const res = await financeApi.backfillPreview();
      setBackfillPreview(res.data);
      const counts = (res.data.counts as Record<string, number>) || {};
      setBackfillMsg(`Dry-run: ${counts.total ?? 0} document(s) missing journals.`);
    } catch (err) {
      setBackfillMsg(err instanceof Error ? err.message : "Backfill preview failed.");
    } finally {
      setBackfillBusy(false);
    }
  };

  const runCutoverAction = async (action: "prepare" | "activate" | "disable_posting") => {
    setCutoverBusy(true);
    setCutoverMsg(null);
    try {
      const res = await financeApi.cutoverAction({ action });
      setCutover(res.data);
      setCutoverMsg(
        action === "prepare"
          ? "Cutover prepared."
          : action === "activate"
            ? "Cutover activated."
            : "Posting disabled."
      );
      loadHealth();
    } catch (err) {
      setCutoverMsg(err instanceof Error ? err.message : "Cutover action failed.");
    } finally {
      setCutoverBusy(false);
    }
  };

  const loadAging = useCallback(() => {
    setReportLoading(true);
    const asOf = dateTo || undefined;
    Promise.all([
      financeApi.arAging({ as_of: asOf }).then((r) => setArAging(r.data)).catch(() => setArAging(null)),
      financeApi.apAging({ as_of: asOf }).then((r) => setApAging(r.data)).catch(() => setApAging(null)),
    ]).finally(() => setReportLoading(false));
  }, [dateTo]);

  const loadBankRec = useCallback(() => {
    setReportLoading(true);
    Promise.all([
      financeApi.bankBook().then((r) => setCashAccounts(r.data.cash_accounts ?? [])).catch(() => setCashAccounts([])),
      financeApi.reconciliations().then((r) => setRecList(r.data ?? [])).catch(() => setRecList([])),
    ]).finally(() => setReportLoading(false));
  }, []);

  const loadTaxReport = useCallback(() => {
    setReportLoading(true);
    financeApi
      .taxReport({ date_from: dateFrom || undefined, date_to: dateTo || undefined })
      .then((r) => setTaxReport(r.data))
      .catch(() => setTaxReport(null))
      .finally(() => setReportLoading(false));
  }, [dateFrom, dateTo]);

  const loadGeneralLedger = useCallback(() => {
    if (!ledgerAccountId) {
      setLedgerReport(null);
      return;
    }
    setReportLoading(true);
    financeApi
      .generalLedger({
        account_id: ledgerAccountId,
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
      })
      .then((r) => setLedgerReport(r.data))
      .catch(() => setLedgerReport(null))
      .finally(() => setReportLoading(false));
  }, [ledgerAccountId, dateFrom, dateTo]);

  const loadJournals = useCallback(() => {
    financeApi
      .journal({})
      .then((r) => setJournalEntries(r.data.results ?? []))
      .catch(() => setJournalEntries(data?.journal ?? []));
  }, [data?.journal]);

  const postDraftJournal = async (entryId: string, allowSelf = false) => {
    setJournalBusy(entryId);
    setJournalMsg(null);
    try {
      await financeApi.postJournal(entryId, { allow_self_approve: allowSelf });
      setJournalMsg("Journal approved and posted.");
      loadJournals();
    } catch (err) {
      setJournalMsg(err instanceof Error ? err.message : "Could not post journal.");
    } finally {
      setJournalBusy(null);
    }
  };

  const discardDraftJournal = async (entryId: string) => {
    setJournalBusy(entryId);
    setJournalMsg(null);
    try {
      await financeApi.discardJournal(entryId);
      setJournalMsg("Draft discarded.");
      loadJournals();
    } catch (err) {
      setJournalMsg(err instanceof Error ? err.message : "Could not discard draft.");
    } finally {
      setJournalBusy(null);
    }
  };

  useEffect(() => {
    if (["trial", "pl", "bs", "cash"].includes(tab)) {
      loadLedgerReports();
    } else if (tab === "periods") {
      loadPeriods();
    } else if (tab === "health") {
      loadHealth();
    } else if (tab === "ar" || tab === "ap") {
      loadAging();
    } else if (tab === "bank") {
      loadBankRec();
    } else if (tab === "tax") {
      loadTaxReport();
    } else if (tab === "ledger") {
      loadGeneralLedger();
    } else if (tab === "journal") {
      loadJournals();
    }
  }, [
    tab,
    loadLedgerReports,
    loadPeriods,
    loadHealth,
    loadAging,
    loadBankRec,
    loadTaxReport,
    loadGeneralLedger,
    loadJournals,
  ]);

  const runPeriodAction = async (
    periodId: string,
    action: "soft-close" | "close" | "reopen" | "lock"
  ) => {
    setPeriodBusy(`${periodId}:${action}`);
    try {
      await financeApi.periodAction(periodId, action);
      loadPeriods();
    } catch {
      /* toast optional */
    } finally {
      setPeriodBusy(null);
    }
  };

  const submitReceipt = async () => {
    setVoucherBusy(true);
    setVoucherMsg(null);
    try {
      const res = await financeApi.createReceipt({
        invoice_id: receiptForm.invoice_id.trim(),
        amount: receiptForm.amount,
        method: receiptForm.method,
        reference: receiptForm.reference || undefined,
      });
      setVoucherMsg(`Receipt posted for ${String(res.data.invoice_number ?? "invoice")}.`);
      setReceiptForm({ invoice_id: "", amount: "", method: "cash", reference: "" });
      loadAging();
    } catch (err) {
      setVoucherMsg(err instanceof Error ? err.message : "Could not post receipt.");
    } finally {
      setVoucherBusy(false);
    }
  };

  const submitSupplierPayment = async () => {
    setVoucherBusy(true);
    setVoucherMsg(null);
    try {
      const res = await financeApi.createSupplierPayment({
        purchase_order_id: supplierForm.purchase_order_id.trim(),
        amount: supplierForm.amount,
        method: supplierForm.method,
        reference: supplierForm.reference || undefined,
      });
      setVoucherMsg(`Supplier payment posted for ${String(res.data.order_number ?? "PO")}.`);
      setSupplierForm({ purchase_order_id: "", amount: "", method: "cash", reference: "" });
      loadAging();
    } catch (err) {
      setVoucherMsg(err instanceof Error ? err.message : "Could not post supplier payment.");
    } finally {
      setVoucherBusy(false);
    }
  };

  const startReconciliation = async () => {
    setRecBusy(true);
    setRecMsg(null);
    try {
      const res = await financeApi.createReconciliation({
        account_id: recForm.account_id,
        statement_date: recForm.statement_date,
        statement_balance: recForm.statement_balance,
      });
      setActiveRec(res.data);
      setRecMsg("Reconciliation started.");
      loadBankRec();
    } catch (err) {
      setRecMsg(err instanceof Error ? err.message : "Could not start reconciliation.");
    } finally {
      setRecBusy(false);
    }
  };

  const openReconciliation = async (id: string) => {
    setRecBusy(true);
    try {
      const res = await financeApi.getReconciliation(id);
      setActiveRec(res.data);
    } catch (err) {
      setRecMsg(err instanceof Error ? err.message : "Could not load reconciliation.");
    } finally {
      setRecBusy(false);
    }
  };

  const addStmtLine = async () => {
    if (!activeRec) return;
    setRecBusy(true);
    setRecMsg(null);
    try {
      await financeApi.addStatementLine(activeRec.id, {
        line_date: stmtForm.line_date || activeRec.statement_date,
        amount: stmtForm.amount,
        description: stmtForm.description || undefined,
        reference: stmtForm.reference || undefined,
      });
      const res = await financeApi.getReconciliation(activeRec.id);
      setActiveRec(res.data);
      setStmtForm({ line_date: "", amount: "", description: "", reference: "" });
      setRecMsg("Statement line added.");
    } catch (err) {
      setRecMsg(err instanceof Error ? err.message : "Could not add statement line.");
    } finally {
      setRecBusy(false);
    }
  };

  const runAutoMatch = async () => {
    if (!activeRec) return;
    setRecBusy(true);
    setRecMsg(null);
    try {
      const res = await financeApi.autoMatchReconciliation(activeRec.id);
      setActiveRec(res.data.reconciliation);
      setRecMsg(`Auto-matched ${res.data.result.matched} line(s).`);
    } catch (err) {
      setRecMsg(err instanceof Error ? err.message : "Auto-match failed.");
    } finally {
      setRecBusy(false);
    }
  };

  const completeRec = async () => {
    if (!activeRec) return;
    setRecBusy(true);
    setRecMsg(null);
    try {
      const res = await financeApi.completeReconciliation(activeRec.id);
      setActiveRec(res.data);
      setRecMsg("Reconciliation completed.");
      loadBankRec();
    } catch (err) {
      setRecMsg(err instanceof Error ? err.message : "Could not complete reconciliation.");
    } finally {
      setRecBusy(false);
    }
  };

  const accountColumns: Column<FinanceAccount>[] = [
    {
      key: "name",
      header: "Account",
      cell: (r) => (
        <div>
          <p className="font-medium">{r.name}</p>
          {r.code && <p className="text-xs font-mono text-muted-foreground">{r.code}</p>}
        </div>
      ),
      exportValue: (r) => r.name,
    },
    { key: "type", header: "Type", cell: (r) => <Badge variant="secondary">{r.type}</Badge>, exportValue: (r) => r.type },
    {
      key: "balance",
      header: "Balance",
      cell: (r) => formatCurrency(r.balance),
      exportValue: (r) => formatCurrency(r.balance),
    },
    {
      key: "ledger",
      header: "",
      cell: (r) => (
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={() => {
            setLedgerAccountId(r.id);
            setTab("ledger");
          }}
        >
          Ledger
        </Button>
      ),
    },
  ];

  const expenseColumns: Column<FinanceExpense>[] = [
    { key: "desc", header: "Description", cell: (r) => r.description, exportValue: (r) => r.description },
    { key: "category", header: "Category", cell: (r) => r.category, exportValue: (r) => r.category },
    { key: "date", header: "Date", cell: (r) => r.date, exportValue: (r) => r.date },
    { key: "amount", header: "Amount", cell: (r) => formatCurrency(r.amount), exportValue: (r) => formatCurrency(r.amount) },
    {
      key: "status",
      header: "Status",
      cell: (r) => (
        <Badge variant={EXPENSE_STATUS[r.status] ?? "secondary"} className="capitalize">
          {r.status}
        </Badge>
      ),
      exportValue: (r) => r.status,
    },
  ];

  const kpis = data?.kpis;

  return (
    <PageLayout
      title="Finance"
      description="Ledger, journals, periods, and financial statements."
      breadcrumbs={["Home", "Finance"]}
      backTo="/dashboard"
      backLabel="Dashboard"
      actions={
        <Button asChild>
          <Link to="/expenses">
            <Plus className="h-4 w-4" />
            Expenses
          </Link>
        </Button>
      }
    >
      <KpiGrid>
        <KpiCard title="Total Revenue" value={formatCurrency(kpis?.revenue ?? 0)} loading={loading} />
        <KpiCard title="Total Expenses" value={formatCurrency(kpis?.expenses ?? 0)} trendUp={false} loading={loading} />
        <KpiCard title="Net Profit" value={formatCurrency(kpis?.net_profit ?? 0)} loading={loading} />
        <KpiCard title="Cash Balance" value={formatCurrency(kpis?.cash_balance ?? 0)} loading={loading} />
      </KpiGrid>

      {equation ? (
        <div className="mb-4 flex flex-wrap items-center gap-3 rounded-xl border border-border/60 px-4 py-3">
          <Badge variant={equation.ok ? "success" : "destructive"}>
            {equation.ok ? "Equation OK" : "Equation broken"}
          </Badge>
          <span className="text-sm text-muted-foreground">
            A {formatCurrency(equation.assets)} = L {formatCurrency(equation.liabilities)} + E{" "}
            {formatCurrency(equation.equity_with_earnings)}
            {!equation.ok
              ? ` · Δ ${formatCurrency(equation.difference_balance_sheet)}`
              : ""}
          </span>
          <span className="text-xs text-muted-foreground font-mono">as of {equation.as_of}</span>
        </div>
      ) : null}

      <TabNav
        tabs={[
          { id: "overview", label: "Overview" },
          { id: "accounts", label: "Accounts" },
          { id: "ledger", label: "GL Ledger" },
          { id: "expenses", label: "Expenses" },
          { id: "journal", label: "Journal" },
          { id: "trial", label: "Trial Balance" },
          { id: "pl", label: "P&L" },
          { id: "bs", label: "Balance Sheet" },
          { id: "cash", label: "Cash Flow" },
          { id: "ar", label: "AR Aging" },
          { id: "ap", label: "AP Aging" },
          { id: "vouchers", label: "Vouchers" },
          { id: "bank", label: "Bank Rec" },
          { id: "tax", label: "Tax" },
          { id: "periods", label: "Periods" },
          { id: "health", label: "Health" },
        ]}
        active={tab}
        onChange={setTab}
      />

      {tab === "overview" && (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <ChartCard title="Revenue vs Expenses" description="Monthly from invoices & purchases" height={280}>
            <ProfitChart data={data?.chart ?? []} />
          </ChartCard>
          <ContentSection title="Recent Activity">
            {loading ? (
              <div className="h-40 animate-pulse rounded-xl bg-muted" />
            ) : !data?.activity.length ? (
              <p className="text-sm text-muted-foreground py-4">No financial activity recorded yet.</p>
            ) : (
              <div className="space-y-3">
                {data.activity.map((item) => (
                  <div key={item.id} className="flex items-center justify-between rounded-xl bg-muted/40 px-4 py-3">
                    <div className="flex items-center gap-3 min-w-0">
                      <div
                        className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${
                          item.type === "in" ? "bg-primary/10 text-primary" : "bg-destructive/10 text-destructive"
                        }`}
                      >
                        {item.type === "in" ? <ArrowUpRight className="h-4 w-4" /> : <ArrowDownRight className="h-4 w-4" />}
                      </div>
                      <span className="text-sm font-medium truncate">{item.label}</span>
                    </div>
                    <span
                      className={`text-sm font-semibold shrink-0 ${
                        item.type === "in" ? "text-primary" : "text-destructive"
                      }`}
                    >
                      {item.type === "in" ? "+" : "-"}
                      {formatCurrency(item.amount)}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </ContentSection>
        </div>
      )}

      {tab === "accounts" && (
        <ContentSection
          title="Chart of Accounts"
          description={
            data?.has_ledger
              ? "Live ledger balances from posted journal entries"
              : "Derived from live sales, purchases, and inventory"
          }
          noPadding
        >
          <DataTable
            embedded
            exportTitle="Finance Accounts"
            columns={accountColumns}
            data={data?.accounts ?? []}
            loading={loading}
            emptyMessage="No account data available."
            defaultPageSize={10}
          />
        </ContentSection>
      )}

      {tab === "ledger" && (
        <ContentSection title="General Ledger" description="Account statement with running balance">
          <DateRangeFilters
            dateFrom={dateFrom}
            dateTo={dateTo}
            onFrom={setDateFrom}
            onTo={setDateTo}
            onRefresh={loadGeneralLedger}
            loading={reportLoading}
          />
          <div className="mb-4 flex flex-wrap items-end gap-3">
            <label className="text-sm">
              <span className="mb-1 block text-muted-foreground">Account</span>
              <select
                className="h-9 rounded-md border border-input bg-background px-3 text-sm"
                value={ledgerAccountId}
                onChange={(e) => setLedgerAccountId(e.target.value)}
              >
                <option value="">Select account…</option>
                {(data?.accounts ?? []).map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.code ? `${a.code} — ` : ""}
                    {a.name}
                  </option>
                ))}
              </select>
            </label>
            <Button type="button" variant="secondary" size="sm" onClick={loadGeneralLedger} disabled={!ledgerAccountId}>
              Load
            </Button>
          </div>
          {!ledgerAccountId ? (
            <EmptyState title="Pick an account" description="Choose an account to view posted movements." />
          ) : reportLoading ? (
            <div className="h-32 animate-pulse rounded-xl bg-muted" />
          ) : !ledgerReport?.account ? (
            <EmptyState title="No ledger data" description="Could not load this account statement." />
          ) : (
            <>
              <div className="mb-4 flex flex-wrap gap-4 text-sm">
                <span>
                  Opening <strong>{formatCurrency(ledgerReport.opening_balance)}</strong>
                </span>
                <span>
                  Debits <strong>{formatCurrency(ledgerReport.period_debit)}</strong>
                </span>
                <span>
                  Credits <strong>{formatCurrency(ledgerReport.period_credit)}</strong>
                </span>
                <span>
                  Closing <strong>{formatCurrency(ledgerReport.closing_balance)}</strong>
                </span>
              </div>
              <DataTable
                embedded
                exportTitle={`GL ${ledgerReport.account.code}`}
                columns={[
                  {
                    key: "date",
                    header: "Date",
                    cell: (r) => r.entry_date ?? "—",
                    exportValue: (r) => r.entry_date ?? "",
                  },
                  {
                    key: "entry",
                    header: "Entry",
                    cell: (r) => (
                      <div>
                        <p className="font-mono text-xs">{r.entry_number}</p>
                        <p className="text-sm truncate max-w-xs">{r.description}</p>
                      </div>
                    ),
                    exportValue: (r) => r.entry_number,
                  },
                  {
                    key: "debit",
                    header: "Debit",
                    cell: (r) => (r.debit ? formatCurrency(r.debit) : "—"),
                    exportValue: (r) => String(r.debit ?? ""),
                  },
                  {
                    key: "credit",
                    header: "Credit",
                    cell: (r) => (r.credit ? formatCurrency(r.credit) : "—"),
                    exportValue: (r) => String(r.credit ?? ""),
                  },
                  {
                    key: "bal",
                    header: "Balance",
                    cell: (r) => formatCurrency(r.running_balance),
                    exportValue: (r) => String(r.running_balance ?? ""),
                  },
                ]}
                data={ledgerReport.lines}
                emptyMessage="No movements in this period."
                defaultPageSize={20}
              />
            </>
          )}
        </ContentSection>
      )}

      {tab === "expenses" && (
        <ContentSection title="Expenses" description="Operating expenses (journal-backed) and purchase orders" noPadding>
          {!loading && !data?.expenses.length ? (
            <EmptyState
              title="No expenses recorded"
              description="Received and ordered purchase orders appear here as expenses."
            />
          ) : (
            <DataTable
              embedded
              exportTitle="Expenses"
              columns={expenseColumns}
              data={data?.expenses ?? []}
              loading={loading}
              defaultPageSize={10}
            />
          )}
        </ContentSection>
      )}

      {tab === "journal" && (
        <ContentSection
          title="Journal Entries"
          description="Posted ledgers and draft manuals awaiting maker-checker approval"
        >
          <div className="mb-3 flex flex-wrap items-center gap-3">
            <Button type="button" variant="secondary" size="sm" onClick={loadJournals}>
              Refresh
            </Button>
            {journalMsg ? <p className="text-sm text-muted-foreground">{journalMsg}</p> : null}
          </div>
          {!loading && !journalEntries.length && !(data?.journal?.length ?? 0) ? (
            <EmptyState
              title="No journal entries yet"
              description="POS sales, expenses, purchases, and gym memberships post automatically. Manual drafts need approval."
            />
          ) : (
            <div className="space-y-4">
              {(journalEntries.length ? journalEntries : data?.journal ?? []).map((entry) => (
                <div key={entry.id} className="rounded-xl border border-border/60 p-4">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div>
                      <p className="font-medium">{entry.description}</p>
                      <p className="text-xs text-muted-foreground font-mono">
                        {entry.entry_number} · {entry.entry_date} · {entry.source_type}
                      </p>
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge
                        variant={
                          entry.status === "posted"
                            ? "success"
                            : entry.status === "draft"
                              ? "warning"
                              : "secondary"
                        }
                        className="capitalize"
                      >
                        {entry.status}
                      </Badge>
                      <Badge variant={entry.is_balanced ? "success" : "warning"}>
                        {formatCurrency(entry.total_debit)}
                      </Badge>
                      {entry.status === "draft" ? (
                        <>
                          <Button
                            type="button"
                            size="sm"
                            disabled={journalBusy === entry.id}
                            onClick={() => postDraftJournal(entry.id, false)}
                          >
                            {journalBusy === entry.id ? (
                              <Loader2 className="h-4 w-4 animate-spin" />
                            ) : null}
                            Approve
                          </Button>
                          <Button
                            type="button"
                            size="sm"
                            variant="secondary"
                            disabled={journalBusy === entry.id}
                            onClick={() => postDraftJournal(entry.id, true)}
                          >
                            Self-approve
                          </Button>
                          <Button
                            type="button"
                            size="sm"
                            variant="ghost"
                            disabled={journalBusy === entry.id}
                            onClick={() => discardDraftJournal(entry.id)}
                          >
                            Discard
                          </Button>
                        </>
                      ) : null}
                    </div>
                  </div>
                  <div className="mt-3 overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="text-left text-muted-foreground">
                          <th className="pb-2 pr-4">Account</th>
                          <th className="pb-2 pr-4 text-right">Debit</th>
                          <th className="pb-2 text-right">Credit</th>
                        </tr>
                      </thead>
                      <tbody>
                        {entry.lines.map((line) => (
                          <tr key={line.id} className="border-t border-border/40">
                            <td className="py-2 pr-4">
                              <span className="font-mono text-xs">{line.account_code}</span> {line.account_name}
                            </td>
                            <td className="py-2 pr-4 text-right">{line.debit ? formatCurrency(line.debit) : "—"}</td>
                            <td className="py-2 text-right">{line.credit ? formatCurrency(line.credit) : "—"}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              ))}
            </div>
          )}
        </ContentSection>
      )}

      {tab === "trial" && (
        <ContentSection title="Trial Balance" description="Posted journal debit and credit totals by account">
          <DateRangeFilters
            dateFrom={dateFrom}
            dateTo={dateTo}
            onFrom={setDateFrom}
            onTo={setDateTo}
            onRefresh={loadLedgerReports}
            loading={reportLoading}
          />
          {!reportLoading && !trialBalance?.rows.length ? (
            <EmptyState title="No ledger activity" description="Post sales or expenses to populate the trial balance." />
          ) : (
            <>
              <div className="mb-3 flex flex-wrap gap-3 text-sm">
                <Badge variant={trialBalance?.is_balanced ? "success" : "warning"}>
                  {trialBalance?.is_balanced ? "Balanced" : "Out of balance"}
                </Badge>
                <span className="text-muted-foreground">
                  Debits {formatCurrency(trialBalance?.totals.debit ?? 0)} · Credits{" "}
                  {formatCurrency(trialBalance?.totals.credit ?? 0)}
                </span>
              </div>
              <DataTable
                embedded
                exportTitle="Trial Balance"
                loading={reportLoading}
                columns={[
                  { key: "code", header: "Code", cell: (r) => <span className="font-mono text-xs">{r.code}</span>, exportValue: (r) => r.code },
                  { key: "name", header: "Account", cell: (r) => r.name, exportValue: (r) => r.name },
                  { key: "type", header: "Type", cell: (r) => r.type, exportValue: (r) => r.type },
                  { key: "debit", header: "Debit", cell: (r) => formatCurrency(r.debit), exportValue: (r) => formatCurrency(r.debit) },
                  { key: "credit", header: "Credit", cell: (r) => formatCurrency(r.credit), exportValue: (r) => formatCurrency(r.credit) },
                  { key: "balance", header: "Balance", cell: (r) => formatCurrency(r.balance), exportValue: (r) => formatCurrency(r.balance) },
                ]}
                data={trialBalance?.rows ?? []}
                defaultPageSize={20}
              />
            </>
          )}
        </ContentSection>
      )}

      {tab === "pl" && (
        <ContentSection title="Profit & Loss" description="Revenue and expenses from the general ledger">
          <div className="flex flex-wrap items-end gap-3 mb-4">
            <div>
              <label className="text-xs text-muted-foreground mb-1 block">From</label>
              <Input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} className="w-auto" />
            </div>
            <div>
              <label className="text-xs text-muted-foreground mb-1 block">To</label>
              <Input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} className="w-auto" />
            </div>
            <div>
              <label className="text-xs text-muted-foreground mb-1 block">Business unit</label>
              <select
                className="flex h-10 w-auto min-w-[10rem] rounded-md border border-input bg-background px-3 py-2 text-sm"
                value={businessUnitId}
                onChange={(e) => setBusinessUnitId(e.target.value)}
              >
                <option value="">All units</option>
                {businessUnits.map((bu) => (
                  <option key={bu.id} value={bu.id}>
                    {bu.code} — {bu.name}
                  </option>
                ))}
              </select>
            </div>
            <Button type="button" variant="secondary" onClick={loadLedgerReports} disabled={reportLoading}>
              {reportLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
              Refresh
            </Button>
          </div>
          <KpiGrid className="mb-4">
            <KpiCard title="Revenue" value={formatCurrency(profitLoss?.totals.revenue ?? 0)} loading={reportLoading} />
            <KpiCard title="Expenses" value={formatCurrency(profitLoss?.totals.expenses ?? 0)} loading={reportLoading} trendUp={false} />
            <KpiCard title="Net Profit" value={formatCurrency(profitLoss?.totals.net_profit ?? 0)} loading={reportLoading} />
          </KpiGrid>
          <div className="grid gap-6 lg:grid-cols-2">
            <ContentSection title="Revenue" noPadding>
              <DataTable
                embedded
                loading={reportLoading}
                columns={[
                  { key: "code", header: "Code", cell: (r) => r.code, exportValue: (r) => r.code },
                  { key: "name", header: "Account", cell: (r) => r.name, exportValue: (r) => r.name },
                  { key: "amount", header: "Amount", cell: (r) => formatCurrency(r.amount), exportValue: (r) => formatCurrency(r.amount) },
                ]}
                data={profitLoss?.revenue ?? []}
                emptyMessage="No revenue accounts with activity."
              />
            </ContentSection>
            <ContentSection title="Expenses" noPadding>
              <DataTable
                embedded
                loading={reportLoading}
                columns={[
                  { key: "code", header: "Code", cell: (r) => r.code, exportValue: (r) => r.code },
                  { key: "name", header: "Account", cell: (r) => r.name, exportValue: (r) => r.name },
                  { key: "amount", header: "Amount", cell: (r) => formatCurrency(r.amount), exportValue: (r) => formatCurrency(r.amount) },
                ]}
                data={profitLoss?.expenses ?? []}
                emptyMessage="No expense accounts with activity."
              />
            </ContentSection>
          </div>
        </ContentSection>
      )}

      {tab === "bs" && (
        <ContentSection title="Balance Sheet" description="Assets, liabilities, and equity from posted journals">
          <DateRangeFilters
            dateFrom={dateFrom}
            dateTo={dateTo}
            onFrom={setDateFrom}
            onTo={setDateTo}
            onRefresh={loadLedgerReports}
            loading={reportLoading}
          />
          <div className="mb-3 flex flex-wrap gap-3 text-sm">
            <Badge variant={balanceSheet?.totals.is_balanced ? "success" : "warning"}>
              {balanceSheet?.totals.is_balanced ? "Assets = L+E" : "Out of balance"}
            </Badge>
            <span className="text-muted-foreground">
              Assets {formatCurrency(balanceSheet?.totals.assets ?? 0)} · L+E{" "}
              {formatCurrency(balanceSheet?.totals.liabilities_plus_equity ?? 0)}
            </span>
          </div>
          <div className="grid gap-6 lg:grid-cols-3">
            {(
              [
                ["Assets", balanceSheet?.assets ?? []],
                ["Liabilities", balanceSheet?.liabilities ?? []],
                ["Equity", balanceSheet?.equity ?? []],
              ] as const
            ).map(([title, rows]) => (
              <ContentSection key={title} title={title} noPadding>
                <DataTable
                  embedded
                  loading={reportLoading}
                  columns={[
                    { key: "code", header: "Code", cell: (r) => r.code, exportValue: (r) => r.code },
                    { key: "name", header: "Account", cell: (r) => r.name, exportValue: (r) => r.name },
                    { key: "balance", header: "Balance", cell: (r) => formatCurrency(r.balance), exportValue: (r) => formatCurrency(r.balance) },
                  ]}
                  data={rows}
                  emptyMessage={`No ${title.toLowerCase()} balances.`}
                />
              </ContentSection>
            ))}
          </div>
        </ContentSection>
      )}

      {tab === "cash" && (
        <ContentSection title="Cash Flow" description="Cash and bank movements from the ledger">
          <DateRangeFilters
            dateFrom={dateFrom}
            dateTo={dateTo}
            onFrom={setDateFrom}
            onTo={setDateTo}
            onRefresh={loadLedgerReports}
            loading={reportLoading}
          />
          <KpiGrid className="mb-4">
            <KpiCard title="Opening Cash" value={formatCurrency(cashFlow?.opening_cash ?? 0)} loading={reportLoading} />
            <KpiCard title="Net Change" value={formatCurrency(cashFlow?.net_change ?? 0)} loading={reportLoading} />
            <KpiCard title="Closing Cash" value={formatCurrency(cashFlow?.closing_cash ?? 0)} loading={reportLoading} />
            <KpiCard title="Operating Net" value={formatCurrency(cashFlow?.operating.net ?? 0)} loading={reportLoading} />
          </KpiGrid>
          {(["operating", "investing", "financing"] as const).map((section) => {
            const block = cashFlow?.[section];
            return (
              <ContentSection key={section} title={section.charAt(0).toUpperCase() + section.slice(1)} className="mb-4">
                {!block || (block.inflows.length === 0 && block.outflows.length === 0) ? (
                  <p className="text-sm text-muted-foreground py-2">No {section} cash movements in this period.</p>
                ) : (
                  <div className="grid gap-4 sm:grid-cols-2 text-sm">
                    <div>
                      <p className="font-medium mb-2 text-primary">Inflows</p>
                      <ul className="space-y-1">
                        {block.inflows.map((row) => (
                          <li key={row.label} className="flex justify-between gap-2">
                            <span className="truncate">{row.label}</span>
                            <span className="shrink-0 font-medium">{formatCurrency(row.amount)}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                    <div>
                      <p className="font-medium mb-2 text-destructive">Outflows</p>
                      <ul className="space-y-1">
                        {block.outflows.map((row) => (
                          <li key={row.label} className="flex justify-between gap-2">
                            <span className="truncate">{row.label}</span>
                            <span className="shrink-0 font-medium">{formatCurrency(row.amount)}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>
                )}
              </ContentSection>
            );
          })}
        </ContentSection>
      )}

      {tab === "ar" && (
        <ContentSection title="Accounts Receivable Aging" description="Open invoices vs AR control account (1100)">
          <div className="flex flex-wrap items-end gap-3 mb-4">
            <div>
              <label className="text-xs text-muted-foreground mb-1 block">As of</label>
              <Input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} className="w-auto" />
            </div>
            <Button type="button" variant="secondary" onClick={loadAging} disabled={reportLoading}>
              {reportLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
              Refresh
            </Button>
          </div>
          <div className="mb-3 flex flex-wrap gap-3 text-sm items-center">
            <Badge variant={arAging?.reconciled ? "success" : "warning"}>
              {arAging?.reconciled ? "Reconciled to AR control" : "Out of sync with AR control"}
            </Badge>
            <span className="text-muted-foreground">
              Outstanding {formatCurrency(arAging?.totals.outstanding ?? 0)} · Control{" "}
              {formatCurrency(arAging?.totals.control_balance ?? 0)} · Diff{" "}
              {formatCurrency(arAging?.totals.difference ?? 0)}
            </span>
          </div>
          <KpiGrid className="mb-4">
            {Object.entries(arAging?.buckets ?? {}).map(([key, amount]) => (
              <KpiCard
                key={key}
                title={arAging?.bucket_labels?.[key] ?? key}
                value={formatCurrency(amount)}
                loading={reportLoading}
              />
            ))}
          </KpiGrid>
          <DataTable
            embedded
            exportTitle="AR Aging"
            loading={reportLoading}
            emptyMessage="No open receivables."
            columns={[
              {
                key: "invoice",
                header: "Invoice",
                cell: (r) => String(r.invoice_number ?? ""),
                exportValue: (r) => String(r.invoice_number ?? ""),
              },
              {
                key: "customer",
                header: "Customer",
                cell: (r) => String(r.customer_name ?? ""),
                exportValue: (r) => String(r.customer_name ?? ""),
              },
              {
                key: "due",
                header: "Due",
                cell: (r) => String(r.due_date ?? ""),
                exportValue: (r) => String(r.due_date ?? ""),
              },
              {
                key: "days",
                header: "Days",
                cell: (r) => String(r.days_overdue ?? 0),
                exportValue: (r) => String(r.days_overdue ?? 0),
              },
              {
                key: "balance",
                header: "Balance",
                cell: (r) => formatCurrency(Number(r.balance ?? 0)),
                exportValue: (r) => formatCurrency(Number(r.balance ?? 0)),
              },
            ]}
            data={(arAging?.rows ?? []) as Record<string, unknown>[]}
            defaultPageSize={15}
          />
        </ContentSection>
      )}

      {tab === "ap" && (
        <ContentSection title="Accounts Payable Aging" description="Goods received less payments vs AP control (2000)">
          <div className="flex flex-wrap items-end gap-3 mb-4">
            <div>
              <label className="text-xs text-muted-foreground mb-1 block">As of</label>
              <Input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} className="w-auto" />
            </div>
            <Button type="button" variant="secondary" onClick={loadAging} disabled={reportLoading}>
              {reportLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
              Refresh
            </Button>
          </div>
          {apAging?.note ? <p className="text-xs text-muted-foreground mb-3">{apAging.note}</p> : null}
          <div className="mb-3 flex flex-wrap gap-3 text-sm items-center">
            <Badge variant={apAging?.reconciled ? "success" : "warning"}>
              {apAging?.reconciled ? "Reconciled to AP control" : "Out of sync with AP control"}
            </Badge>
            <span className="text-muted-foreground">
              Outstanding {formatCurrency(apAging?.totals.outstanding ?? 0)} · Control{" "}
              {formatCurrency(apAging?.totals.control_balance ?? 0)} · Diff{" "}
              {formatCurrency(apAging?.totals.difference ?? 0)}
            </span>
          </div>
          <KpiGrid className="mb-4">
            {Object.entries(apAging?.buckets ?? {}).map(([key, amount]) => (
              <KpiCard
                key={key}
                title={apAging?.bucket_labels?.[key] ?? key}
                value={formatCurrency(amount)}
                loading={reportLoading}
              />
            ))}
          </KpiGrid>
          <DataTable
            embedded
            exportTitle="AP Aging"
            loading={reportLoading}
            emptyMessage="No open payables from goods receipt."
            columns={[
              {
                key: "po",
                header: "PO",
                cell: (r) => String(r.order_number ?? ""),
                exportValue: (r) => String(r.order_number ?? ""),
              },
              {
                key: "supplier",
                header: "Supplier",
                cell: (r) => String(r.supplier_name ?? ""),
                exportValue: (r) => String(r.supplier_name ?? ""),
              },
              {
                key: "date",
                header: "Order date",
                cell: (r) => String(r.order_date ?? ""),
                exportValue: (r) => String(r.order_date ?? ""),
              },
              {
                key: "days",
                header: "Days",
                cell: (r) => String(r.days_outstanding ?? 0),
                exportValue: (r) => String(r.days_outstanding ?? 0),
              },
              {
                key: "balance",
                header: "Balance",
                cell: (r) => formatCurrency(Number(r.balance ?? 0)),
                exportValue: (r) => formatCurrency(Number(r.balance ?? 0)),
              },
            ]}
            data={(apAging?.rows ?? []) as Record<string, unknown>[]}
            defaultPageSize={15}
          />
        </ContentSection>
      )}

      {tab === "vouchers" && (
        <ContentSection
          title="Payment & receipt vouchers"
          description="Settle customer AR and supplier AP through the ledger"
        >
          {voucherMsg ? (
            <p className="mb-4 text-sm text-muted-foreground">{voucherMsg}</p>
          ) : null}
          <div className="grid gap-6 lg:grid-cols-2">
            <div className="space-y-3 rounded-xl border border-border/60 p-4">
              <h3 className="font-medium">Customer receipt</h3>
              <p className="text-xs text-muted-foreground">Dr Cash · Cr Accounts Receivable</p>
              <div>
                <label className="text-xs text-muted-foreground mb-1 block">Invoice ID</label>
                <Input
                  value={receiptForm.invoice_id}
                  onChange={(e) => setReceiptForm((f) => ({ ...f, invoice_id: e.target.value }))}
                  placeholder="UUID"
                />
              </div>
              <div>
                <label className="text-xs text-muted-foreground mb-1 block">Amount</label>
                <Input
                  type="number"
                  step="0.01"
                  value={receiptForm.amount}
                  onChange={(e) => setReceiptForm((f) => ({ ...f, amount: e.target.value }))}
                />
              </div>
              <div>
                <label className="text-xs text-muted-foreground mb-1 block">Method</label>
                <select
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                  value={receiptForm.method}
                  onChange={(e) => setReceiptForm((f) => ({ ...f, method: e.target.value }))}
                >
                  <option value="cash">Cash</option>
                  <option value="mobile">Mobile</option>
                  <option value="card">Card</option>
                  <option value="other">Other</option>
                </select>
              </div>
              <div>
                <label className="text-xs text-muted-foreground mb-1 block">Reference</label>
                <Input
                  value={receiptForm.reference}
                  onChange={(e) => setReceiptForm((f) => ({ ...f, reference: e.target.value }))}
                />
              </div>
              <Button
                type="button"
                onClick={submitReceipt}
                disabled={voucherBusy || !receiptForm.invoice_id || !receiptForm.amount}
              >
                {voucherBusy ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                Post receipt
              </Button>
            </div>
            <div className="space-y-3 rounded-xl border border-border/60 p-4">
              <h3 className="font-medium">Supplier payment</h3>
              <p className="text-xs text-muted-foreground">Dr Accounts Payable · Cr Cash/Bank</p>
              <div>
                <label className="text-xs text-muted-foreground mb-1 block">Purchase order ID</label>
                <Input
                  value={supplierForm.purchase_order_id}
                  onChange={(e) =>
                    setSupplierForm((f) => ({ ...f, purchase_order_id: e.target.value }))
                  }
                  placeholder="UUID"
                />
              </div>
              <div>
                <label className="text-xs text-muted-foreground mb-1 block">Amount</label>
                <Input
                  type="number"
                  step="0.01"
                  value={supplierForm.amount}
                  onChange={(e) => setSupplierForm((f) => ({ ...f, amount: e.target.value }))}
                />
              </div>
              <div>
                <label className="text-xs text-muted-foreground mb-1 block">Method</label>
                <select
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                  value={supplierForm.method}
                  onChange={(e) => setSupplierForm((f) => ({ ...f, method: e.target.value }))}
                >
                  <option value="cash">Cash</option>
                  <option value="bank">Bank</option>
                  <option value="mobile">Mobile</option>
                  <option value="card">Card</option>
                  <option value="other">Other</option>
                </select>
              </div>
              <div>
                <label className="text-xs text-muted-foreground mb-1 block">Reference</label>
                <Input
                  value={supplierForm.reference}
                  onChange={(e) => setSupplierForm((f) => ({ ...f, reference: e.target.value }))}
                />
              </div>
              <Button
                type="button"
                onClick={submitSupplierPayment}
                disabled={
                  voucherBusy || !supplierForm.purchase_order_id || !supplierForm.amount
                }
              >
                {voucherBusy ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                Post payment
              </Button>
            </div>
          </div>
        </ContentSection>
      )}

      {tab === "bank" && (
        <ContentSection
          title="Bank reconciliation"
          description="Match statement lines to cash/bank journal entries"
        >
          {recMsg ? <p className="mb-4 text-sm text-muted-foreground">{recMsg}</p> : null}

          <div className="mb-6 grid gap-4 sm:grid-cols-3">
            {cashAccounts.map((a) => (
              <KpiCard
                key={a.id}
                title={`${a.code} ${a.name}`}
                value={formatCurrency(a.balance)}
                loading={reportLoading}
              />
            ))}
          </div>

          <div className="mb-6 grid gap-6 lg:grid-cols-2">
            <div className="space-y-3 rounded-xl border border-border/60 p-4">
              <h3 className="font-medium">Start reconciliation</h3>
              <div>
                <label className="text-xs text-muted-foreground mb-1 block">Account</label>
                <select
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                  value={recForm.account_id}
                  onChange={(e) => setRecForm((f) => ({ ...f, account_id: e.target.value }))}
                >
                  <option value="">Select…</option>
                  {cashAccounts.map((a) => (
                    <option key={a.id} value={a.id}>
                      {a.code} — {a.name}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-xs text-muted-foreground mb-1 block">Statement date</label>
                <Input
                  type="date"
                  value={recForm.statement_date}
                  onChange={(e) => setRecForm((f) => ({ ...f, statement_date: e.target.value }))}
                />
              </div>
              <div>
                <label className="text-xs text-muted-foreground mb-1 block">Statement balance</label>
                <Input
                  type="number"
                  step="0.01"
                  value={recForm.statement_balance}
                  onChange={(e) =>
                    setRecForm((f) => ({ ...f, statement_balance: e.target.value }))
                  }
                />
              </div>
              <Button
                type="button"
                onClick={startReconciliation}
                disabled={
                  recBusy || !recForm.account_id || !recForm.statement_date || !recForm.statement_balance
                }
              >
                {recBusy ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                Start
              </Button>
            </div>

            <div className="space-y-3 rounded-xl border border-border/60 p-4">
              <h3 className="font-medium">Recent reconciliations</h3>
              {!recList.length ? (
                <p className="text-sm text-muted-foreground">No reconciliations yet.</p>
              ) : (
                <ul className="space-y-2">
                  {recList.slice(0, 8).map((r) => (
                    <li key={r.id} className="flex items-center justify-between gap-2 text-sm">
                      <button
                        type="button"
                        className="text-left hover:underline"
                        onClick={() => openReconciliation(r.id)}
                      >
                        {r.account_code} · {r.statement_date}
                      </button>
                      <Badge
                        variant={r.status === "completed" ? "success" : "warning"}
                        className="capitalize"
                      >
                        {r.status.replace("_", " ")}
                      </Badge>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>

          {activeRec ? (
            <div className="space-y-4 rounded-xl border border-border/60 p-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="font-medium">
                    {activeRec.account_code} {activeRec.account_name} · {activeRec.statement_date}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Statement {formatCurrency(activeRec.statement_balance)} · Book{" "}
                    {formatCurrency(activeRec.book_balance)} · Diff{" "}
                    {formatCurrency(activeRec.summary?.difference ?? 0)}
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Badge variant={activeRec.summary?.is_balanced ? "success" : "warning"}>
                    {activeRec.summary?.is_balanced ? "Balanced" : "Out of balance"}
                  </Badge>
                  <Badge variant={activeRec.status === "completed" ? "success" : "secondary"}>
                    {activeRec.status.replace("_", " ")}
                  </Badge>
                </div>
              </div>

              {activeRec.status !== "completed" ? (
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5 items-end">
                  <div>
                    <label className="text-xs text-muted-foreground mb-1 block">Line date</label>
                    <Input
                      type="date"
                      value={stmtForm.line_date}
                      onChange={(e) => setStmtForm((f) => ({ ...f, line_date: e.target.value }))}
                    />
                  </div>
                  <div>
                    <label className="text-xs text-muted-foreground mb-1 block">Amount (+in / −out)</label>
                    <Input
                      type="number"
                      step="0.01"
                      value={stmtForm.amount}
                      onChange={(e) => setStmtForm((f) => ({ ...f, amount: e.target.value }))}
                    />
                  </div>
                  <div>
                    <label className="text-xs text-muted-foreground mb-1 block">Description</label>
                    <Input
                      value={stmtForm.description}
                      onChange={(e) => setStmtForm((f) => ({ ...f, description: e.target.value }))}
                    />
                  </div>
                  <div>
                    <label className="text-xs text-muted-foreground mb-1 block">Reference</label>
                    <Input
                      value={stmtForm.reference}
                      onChange={(e) => setStmtForm((f) => ({ ...f, reference: e.target.value }))}
                    />
                  </div>
                  <Button type="button" onClick={addStmtLine} disabled={recBusy || !stmtForm.amount}>
                    Add line
                  </Button>
                </div>
              ) : null}

              <div className="flex flex-wrap gap-2">
                {activeRec.status !== "completed" ? (
                  <>
                    <Button type="button" variant="secondary" onClick={runAutoMatch} disabled={recBusy}>
                      Auto-match
                    </Button>
                    <Button
                      type="button"
                      onClick={completeRec}
                      disabled={recBusy || !activeRec.summary?.is_balanced}
                    >
                      Complete
                    </Button>
                  </>
                ) : null}
              </div>

              <DataTable
                embedded
                exportTitle="Statement lines"
                emptyMessage="No statement lines yet."
                columns={[
                  {
                    key: "date",
                    header: "Date",
                    cell: (r) => String(r.line_date ?? ""),
                    exportValue: (r) => String(r.line_date ?? ""),
                  },
                  {
                    key: "desc",
                    header: "Description",
                    cell: (r) => String(r.description ?? ""),
                    exportValue: (r) => String(r.description ?? ""),
                  },
                  {
                    key: "amt",
                    header: "Amount",
                    cell: (r) => formatCurrency(Number(r.amount ?? 0)),
                    exportValue: (r) => formatCurrency(Number(r.amount ?? 0)),
                  },
                  {
                    key: "match",
                    header: "Matched",
                    cell: (r) => (r.is_matched ? String(r.matched_entry_number ?? "Yes") : "—"),
                    exportValue: (r) => (r.is_matched ? "Yes" : "No"),
                  },
                ]}
                data={(activeRec.statement_lines ?? []) as Record<string, unknown>[]}
                defaultPageSize={10}
              />
            </div>
          ) : null}
        </ContentSection>
      )}

      {tab === "tax" && (
        <ContentSection
          title="Sales tax"
          description="Tax collected and refunded vs Tax Payable (2100)"
        >
          <DateRangeFilters
            dateFrom={dateFrom}
            dateTo={dateTo}
            onFrom={setDateFrom}
            onTo={setDateTo}
            onRefresh={loadTaxReport}
            loading={reportLoading}
          />
          <div className="mb-3 flex flex-wrap gap-3 text-sm items-center">
            <Badge variant={taxReport?.reconciled ? "success" : "warning"}>
              {taxReport?.reconciled ? "Reconciled to tax control" : "Period view (lifetime control separate)"}
            </Badge>
            {taxReport?.tax_account ? (
              <span className="text-muted-foreground">
                {taxReport.tax_account.code} {taxReport.tax_account.name}
              </span>
            ) : null}
          </div>
          <KpiGrid className="mb-4">
            <KpiCard
              title="Collected"
              value={formatCurrency(taxReport?.collected ?? 0)}
              loading={reportLoading}
            />
            <KpiCard
              title="Refunded"
              value={formatCurrency(taxReport?.refunded ?? 0)}
              loading={reportLoading}
            />
            <KpiCard
              title="Net payable"
              value={formatCurrency(taxReport?.net_payable ?? 0)}
              loading={reportLoading}
            />
            <KpiCard
              title="Control balance"
              value={formatCurrency(taxReport?.control_balance ?? 0)}
              loading={reportLoading}
            />
          </KpiGrid>
          <DataTable
            embedded
            exportTitle="Tax Report"
            loading={reportLoading}
            emptyMessage="No tax postings in this range."
            columns={[
              {
                key: "date",
                header: "Date",
                cell: (r) => String(r.entry_date ?? ""),
                exportValue: (r) => String(r.entry_date ?? ""),
              },
              {
                key: "entry",
                header: "Journal",
                cell: (r) => String(r.entry_number ?? ""),
                exportValue: (r) => String(r.entry_number ?? ""),
              },
              {
                key: "ref",
                header: "Reference",
                cell: (r) => String(r.source_reference ?? ""),
                exportValue: (r) => String(r.source_reference ?? ""),
              },
              {
                key: "collected",
                header: "Collected",
                cell: (r) => formatCurrency(Number(r.collected ?? 0)),
                exportValue: (r) => formatCurrency(Number(r.collected ?? 0)),
              },
              {
                key: "refunded",
                header: "Refunded",
                cell: (r) => formatCurrency(Number(r.refunded ?? 0)),
                exportValue: (r) => formatCurrency(Number(r.refunded ?? 0)),
              },
            ]}
            data={(taxReport?.rows ?? []) as Record<string, unknown>[]}
            defaultPageSize={15}
          />
        </ContentSection>
      )}

      {tab === "periods" && (
        <ContentSection title="Financial Periods" description="Open, soft-close, close, reopen, or lock accounting periods">
          <div className="mb-3">
            <Button type="button" variant="secondary" size="sm" onClick={loadPeriods}>
              Refresh
            </Button>
          </div>
          {!periods.length ? (
            <EmptyState
              title="No periods yet"
              description="Periods are created automatically when journals are posted."
            />
          ) : (
            <div className="space-y-3">
              {periods.map((p) => (
                <div key={p.id} className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-border/60 p-4">
                  <div>
                    <p className="font-medium">{p.name}</p>
                    <p className="text-xs text-muted-foreground">
                      {p.start_date} → {p.end_date}
                      {p.fiscal_year_name ? ` · ${p.fiscal_year_name}` : ""}
                    </p>
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant={PERIOD_STATUS[p.status] ?? "secondary"} className="capitalize">
                      {p.status.replace("_", " ")}
                    </Badge>
                    {p.status === "open" && (
                      <>
                        <Button
                          size="sm"
                          variant="secondary"
                          disabled={periodBusy === `${p.id}:soft-close`}
                          onClick={() => runPeriodAction(p.id, "soft-close")}
                        >
                          Soft close
                        </Button>
                        <Button
                          size="sm"
                          variant="secondary"
                          disabled={periodBusy === `${p.id}:close`}
                          onClick={() => runPeriodAction(p.id, "close")}
                        >
                          Close
                        </Button>
                      </>
                    )}
                    {p.status === "soft_closed" && (
                      <>
                        <Button size="sm" variant="secondary" disabled={!!periodBusy} onClick={() => runPeriodAction(p.id, "close")}>
                          Close
                        </Button>
                        <Button size="sm" variant="secondary" disabled={!!periodBusy} onClick={() => runPeriodAction(p.id, "reopen")}>
                          Reopen
                        </Button>
                      </>
                    )}
                    {p.status === "closed" && (
                      <>
                        <Button size="sm" variant="secondary" disabled={!!periodBusy} onClick={() => runPeriodAction(p.id, "reopen")}>
                          Reopen
                        </Button>
                        <Button size="sm" variant="secondary" disabled={!!periodBusy} onClick={() => runPeriodAction(p.id, "lock")}>
                          Lock
                        </Button>
                      </>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </ContentSection>
      )}

      {tab === "health" && (
        <ContentSection title="Accounting Health" description="Integrity checks for the central ledger">
          <div className="mb-3 flex flex-wrap items-center gap-3">
            <Button type="button" variant="secondary" size="sm" onClick={loadHealth}>
              Refresh
            </Button>
            <Button type="button" variant="secondary" size="sm" onClick={runBackfillPreview} disabled={backfillBusy}>
              {backfillBusy ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
              Backfill dry-run
            </Button>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => runCutoverAction("prepare")}
              disabled={cutoverBusy}
            >
              Prepare cutover
            </Button>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => runCutoverAction("activate")}
              disabled={cutoverBusy}
            >
              Activate cutover
            </Button>
            {health && (
              <Badge
                variant={
                  health.status === "healthy" ? "success" : health.status === "degraded" ? "warning" : "destructive"
                }
                className="capitalize"
              >
                {health.status}
              </Badge>
            )}
          </div>
          {cutover ? (
            <p className="mb-2 text-xs text-muted-foreground font-mono">
              Cutover · phase {String(cutover.phase)} · posting{" "}
              {cutover.posting_enabled ? "on" : "off"} · date{" "}
              {cutover.cutover_date ? String(cutover.cutover_date) : "—"} · ready{" "}
              {cutover.ready ? "yes" : "no"}
            </p>
          ) : null}
          {cutoverMsg ? <p className="mb-2 text-sm text-muted-foreground">{cutoverMsg}</p> : null}
          {backfillMsg ? <p className="mb-3 text-sm text-muted-foreground">{backfillMsg}</p> : null}
          {backfillPreview?.counts ? (
            <p className="mb-4 text-xs text-muted-foreground font-mono">
              Missing — invoices {(backfillPreview.counts as Record<string, number>).invoices} · expenses{" "}
              {(backfillPreview.counts as Record<string, number>).expenses} · POs{" "}
              {(backfillPreview.counts as Record<string, number>).purchase_orders}
              {backfillPreview.before_date ? ` · before ${String(backfillPreview.before_date)}` : ""}
            </p>
          ) : null}
          {!health ? (
            <EmptyState title="Unable to load health" description="Check finance permissions and try again." />
          ) : (
            <div className="space-y-3">
              {health.checks.map((check) => (
                <div key={check.id} className="flex items-start gap-3 rounded-xl border border-border/60 p-4">
                  <Badge variant={check.ok ? "success" : check.severity ? "destructive" : "warning"}>
                    {check.ok ? "OK" : "Issue"}
                  </Badge>
                  <div>
                    <p className="text-sm font-medium font-mono">{check.id}</p>
                    <p className="text-sm text-muted-foreground">{check.message}</p>
                  </div>
                </div>
              ))}
              <p className="text-xs text-muted-foreground">
                Summary: {health.summary.ok} ok · {health.summary.warnings} warnings · {health.summary.errors} errors
              </p>
            </div>
          )}
        </ContentSection>
      )}
    </PageLayout>
  );
}
