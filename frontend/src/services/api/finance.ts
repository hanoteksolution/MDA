import type { ApiResponse } from "@/types/models";
import type { ApiListResponse } from "@/types/models/catalog";
import { apiRequest, qs } from "./http";

export interface FinanceKPIs {
  revenue: number;
  expenses: number;
  operating_expenses?: number;
  purchase_expenses?: number;
  net_profit: number;
  cash_collected: number;
  cash_balance: number;
}

export interface FinanceAccount {
  id: string;
  code?: string;
  name: string;
  type: string;
  balance: number;
  is_system?: boolean;
  is_active?: boolean;
  parent_id?: string | null;
  description?: string;
}

export interface FinanceActivity {
  id: string;
  label: string;
  amount: number;
  type: "in" | "out";
  date: string;
}

export interface FinanceExpense {
  id: string;
  description: string;
  category: string;
  date: string;
  amount: number;
  status: string;
  source?: string;
}

export interface FinanceJournalLine {
  id: string;
  account_id: string;
  account_code: string;
  account_name: string;
  debit: number;
  credit: number;
  memo: string;
}

export interface FinanceJournalEntry {
  id: string;
  entry_number: string;
  entry_date: string | null;
  description: string;
  status: string;
  source_type: string;
  lines: FinanceJournalLine[];
  total_debit: number;
  total_credit: number;
  is_balanced: boolean;
  created_by_id?: string | null;
  approved_by_id?: string | null;
  approved_at?: string | null;
  reverses_entry_id?: string | null;
}

export interface FinanceSummary {
  kpis: FinanceKPIs;
  activity: FinanceActivity[];
  accounts: FinanceAccount[];
  expenses: FinanceExpense[];
  journal?: FinanceJournalEntry[];
  chart: { month: string; profit: number; expenses: number }[];
  has_ledger?: boolean;
}

export interface TrialBalanceRow {
  account_id: string;
  code: string;
  name: string;
  type: string;
  debit: number;
  credit: number;
  balance: number;
}

export interface TrialBalanceReport {
  date_from: string | null;
  date_to: string | null;
  rows: TrialBalanceRow[];
  totals: { debit: number; credit: number };
  is_balanced: boolean;
}

export interface ProfitLossLine {
  account_id: string;
  code: string;
  name: string;
  amount: number;
}

export interface ProfitLossReport {
  date_from?: string | null;
  date_to?: string | null;
  business_unit_id?: string | null;
  cost_center_id?: string | null;
  revenue: ProfitLossLine[];
  expenses: ProfitLossLine[];
  totals: { revenue: number; expenses: number; net_profit: number };
}

export interface BalanceSheetLine {
  account_id: string | null;
  code: string;
  name: string;
  balance: number;
}

export interface BalanceSheetReport {
  as_of: string | null;
  assets: BalanceSheetLine[];
  liabilities: BalanceSheetLine[];
  equity: BalanceSheetLine[];
  totals: {
    assets: number;
    liabilities: number;
    equity: number;
    liabilities_plus_equity: number;
    is_balanced: boolean;
  };
}

export interface AccountingHealthCheck {
  id: string;
  ok: boolean;
  severity?: boolean;
  message: string;
}

export interface AccountingHealthReport {
  status: "healthy" | "degraded" | "unhealthy" | "unknown";
  checks: AccountingHealthCheck[];
  summary: { ok: number; warnings: number; errors: number };
}

export interface AccountingEquationReport {
  as_of: string;
  assets: number;
  liabilities: number;
  equity: number;
  revenue: number;
  expenses: number;
  retained_earnings: number;
  equity_with_earnings: number;
  liabilities_plus_equity: number;
  balance_sheet_ok: boolean;
  expanded_ok: boolean;
  ok: boolean;
  difference_balance_sheet: number;
  difference_expanded: number;
  message: string;
}

export interface GeneralLedgerLine {
  id: string;
  entry_id: string;
  entry_number: string;
  entry_date: string | null;
  description: string;
  source_type: string;
  memo: string;
  debit: number;
  credit: number;
  running_balance: number;
}

export interface GeneralLedgerReport {
  account: { id: string; code: string; name: string; type: string } | null;
  cost_center_id?: string | null;
  business_unit_id?: string | null;
  date_from: string | null;
  date_to: string | null;
  opening_balance: number;
  period_debit: number;
  period_credit: number;
  closing_balance: number;
  lines: GeneralLedgerLine[];
  error?: string;
}

export interface CashFlowSection {
  inflows: { label: string; amount: number }[];
  outflows: { label: string; amount: number }[];
  net: number;
}

export interface CashFlowReport {
  date_from: string | null;
  date_to: string | null;
  operating: CashFlowSection;
  investing: CashFlowSection;
  financing: CashFlowSection;
  net_change: number;
  opening_cash: number;
  closing_cash: number;
}

export interface FinancialPeriod {
  id: string;
  name: string;
  start_date: string;
  end_date: string;
  status: "open" | "soft_closed" | "closed" | "locked";
  fiscal_year_id: string;
  fiscal_year_name: string;
  closed_at: string | null;
}

export interface AgingReport {
  as_of: string;
  rows: Record<string, unknown>[];
  buckets: Record<string, number>;
  bucket_labels?: Record<string, string>;
  totals: {
    outstanding: number;
    control_balance: number;
    difference: number;
  };
  reconciled: boolean;
  note?: string;
}

export interface BankReconciliationSummary {
  unmatched_book_deposits: number;
  unmatched_book_withdrawals: number;
  unmatched_book_count: number;
  matched_statement_count: number;
  unmatched_statement_count: number;
  adjusted_book_balance: number;
  difference: number;
  is_balanced: boolean;
}

export interface BankReconciliation {
  id: string;
  account_id: string;
  account_code: string;
  account_name: string;
  statement_date: string;
  statement_balance: number;
  book_balance: number;
  status: string;
  notes: string;
  completed_at: string | null;
  summary: BankReconciliationSummary;
  statement_lines?: Record<string, unknown>[];
}

export interface TaxReport {
  date_from: string | null;
  date_to: string | null;
  as_of?: string;
  tax_account: { id: string; code: string; name: string } | null;
  collected: number;
  refunded: number;
  net_payable: number;
  control_balance: number;
  difference: number;
  reconciled: boolean;
  rows: Record<string, unknown>[];
}

export const financeApi = {
  summary: (period = "month") =>
    apiRequest<ApiResponse<FinanceSummary>>(`/finance/summary/?period=${period}`),

  accounts: (params: Record<string, string | undefined> = {}) =>
    apiRequest<ApiListResponse<FinanceAccount>>(`/finance/accounts/${qs(params)}`),

  createAccount: (data: {
    code: string;
    name: string;
    type: string;
    parent_id?: string;
    description?: string;
  }) =>
    apiRequest<ApiResponse<FinanceAccount>>("/finance/accounts/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  updateAccount: (id: string, data: Record<string, unknown>) =>
    apiRequest<ApiResponse<FinanceAccount>>(`/finance/accounts/${id}/`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  deactivateAccount: (id: string) =>
    apiRequest<ApiResponse<Record<string, unknown>>>(`/finance/accounts/${id}/`, {
      method: "DELETE",
    }),

  costCenters: (params: { is_active?: string } = {}) =>
    apiRequest<ApiListResponse<{ id: string; code: string; name: string; is_active: boolean }>>(
      `/finance/cost-centers/${qs(params)}`
    ),

  createCostCenter: (data: { code: string; name: string; description?: string; parent_id?: string }) =>
    apiRequest<ApiResponse<{ id: string; code: string; name: string }>>("/finance/cost-centers/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  businessUnits: (params: { is_active?: string } = {}) =>
    apiRequest<
      ApiListResponse<{
        id: string;
        code: string;
        name: string;
        module_code: string;
        is_active: boolean;
      }>
    >(`/finance/business-units/${qs(params)}`),

  createBusinessUnit: (data: {
    code: string;
    name: string;
    module_code?: string;
    description?: string;
  }) =>
    apiRequest<ApiResponse<{ id: string; code: string; name: string }>>("/finance/business-units/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  journal: (params: Record<string, string | undefined> = {}) =>
    apiRequest<ApiListResponse<FinanceJournalEntry>>(`/finance/journal/${qs(params)}`),

  createJournalEntry: (data: {
    description: string;
    entry_date?: string;
    status?: string;
    allow_self_approve?: boolean;
    lines: {
      account_code?: string;
      account_id?: string;
      debit?: number;
      credit?: number;
      memo?: string;
    }[];
  }) =>
    apiRequest<ApiResponse<FinanceJournalEntry>>("/finance/journal/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  postJournal: (entryId: string, data: { allow_self_approve?: boolean } = {}) =>
    apiRequest<ApiResponse<FinanceJournalEntry>>(`/finance/journal/${entryId}/post/`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  discardJournal: (entryId: string) =>
    apiRequest<ApiResponse<Record<string, unknown>>>(`/finance/journal/${entryId}/discard/`, {
      method: "POST",
      body: JSON.stringify({}),
    }),

  reverseJournal: (entryId: string, reason = "") =>
    apiRequest<ApiResponse<FinanceJournalEntry>>(`/finance/journal/${entryId}/reverse/`, {
      method: "POST",
      body: JSON.stringify({ reason }),
    }),

  trialBalance: (params: { date_from?: string; date_to?: string } = {}) =>
    apiRequest<ApiResponse<TrialBalanceReport>>(`/finance/reports/trial-balance/${qs(params)}`),

  profitLoss: (params: {
    date_from?: string;
    date_to?: string;
    business_unit_id?: string;
    cost_center_id?: string;
  } = {}) =>
    apiRequest<ApiResponse<ProfitLossReport>>(`/finance/reports/profit-loss/${qs(params)}`),

  balanceSheet: (params: { as_of?: string } = {}) =>
    apiRequest<ApiResponse<BalanceSheetReport>>(`/finance/reports/balance-sheet/${qs(params)}`),

  health: () => apiRequest<ApiResponse<AccountingHealthReport>>("/finance/health/"),

  equation: (params: { as_of?: string } = {}) =>
    apiRequest<ApiResponse<AccountingEquationReport>>(`/finance/equation/${qs(params)}`),

  generalLedger: (params: {
    account_id?: string;
    account_code?: string;
    cost_center_id?: string;
    business_unit_id?: string;
    date_from?: string;
    date_to?: string;
    limit?: number | string;
  }) =>
    apiRequest<ApiResponse<GeneralLedgerReport>>(`/finance/reports/general-ledger/${qs(params)}`),

  cashFlow: (params: { date_from?: string; date_to?: string } = {}) =>
    apiRequest<ApiResponse<CashFlowReport>>(`/finance/reports/cash-flow/${qs(params)}`),

  periods: (params: { status?: string } = {}) =>
    apiRequest<ApiResponse<FinancialPeriod[]>>(`/finance/periods/${qs(params)}`),

  periodAction: (
    periodId: string,
    action: "soft-close" | "close" | "reopen" | "lock"
  ) =>
    apiRequest<ApiResponse<FinancialPeriod>>(`/finance/periods/${periodId}/${action}/`, {
      method: "POST",
      body: JSON.stringify({}),
    }),

  arAging: (params: { as_of?: string } = {}) =>
    apiRequest<ApiResponse<AgingReport>>(`/finance/reports/ar-aging/${qs(params)}`),

  apAging: (params: { as_of?: string } = {}) =>
    apiRequest<ApiResponse<AgingReport>>(`/finance/reports/ap-aging/${qs(params)}`),

  createReceipt: (data: {
    invoice_id: string;
    amount: number | string;
    method?: string;
    reference?: string;
    paid_at?: string;
  }) =>
    apiRequest<ApiResponse<Record<string, unknown>>>("/finance/vouchers/receipts/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  createSupplierPayment: (data: {
    purchase_order_id: string;
    amount: number | string;
    method?: string;
    reference?: string;
    notes?: string;
    paid_at?: string;
    branch_id?: string;
  }) =>
    apiRequest<ApiResponse<Record<string, unknown>>>("/finance/vouchers/supplier-payments/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  bankBook: (params: { account_id?: string; as_of?: string; unmatched_only?: string } = {}) =>
    apiRequest<ApiResponse<{
      cash_accounts: { id: string; code: string; name: string; balance: number }[];
      account?: { id: string; code: string; name: string; balance: number } | null;
      lines: Record<string, unknown>[];
    }>>(`/finance/bank-book/${qs(params)}`),

  reconciliations: (params: { account_id?: string; status?: string } = {}) =>
    apiRequest<ApiResponse<BankReconciliation[]>>(`/finance/reconciliations/${qs(params)}`),

  createReconciliation: (data: {
    account_id: string;
    statement_date: string;
    statement_balance: number | string;
    notes?: string;
  }) =>
    apiRequest<ApiResponse<BankReconciliation>>("/finance/reconciliations/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  getReconciliation: (id: string) =>
    apiRequest<ApiResponse<BankReconciliation>>(`/finance/reconciliations/${id}/`),

  addStatementLine: (
    id: string,
    data: { line_date: string; amount: number | string; description?: string; reference?: string }
  ) =>
    apiRequest<ApiResponse<Record<string, unknown>>>(`/finance/reconciliations/${id}/lines/`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  matchReconciliationLine: (
    id: string,
    data: { statement_line_id: string; journal_line_id: string }
  ) =>
    apiRequest<ApiResponse<Record<string, unknown>>>(`/finance/reconciliations/${id}/match/`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  autoMatchReconciliation: (id: string) =>
    apiRequest<ApiResponse<{ result: { matched: number }; reconciliation: BankReconciliation }>>(
      `/finance/reconciliations/${id}/auto-match/`,
      { method: "POST", body: JSON.stringify({}) }
    ),

  completeReconciliation: (id: string) =>
    apiRequest<ApiResponse<BankReconciliation>>(`/finance/reconciliations/${id}/complete/`, {
      method: "POST",
      body: JSON.stringify({}),
    }),

  taxReport: (params: { date_from?: string; date_to?: string } = {}) =>
    apiRequest<ApiResponse<TaxReport>>(`/finance/reports/tax/${qs(params)}`),

  backfillPreview: (params: { before?: string; limit?: string } = {}) =>
    apiRequest<ApiResponse<Record<string, unknown>>>(`/finance/backfill/${qs(params)}`),

  backfillRun: (data: {
    dry_run?: boolean;
    before?: string;
    limit?: number;
    include_invoices?: boolean;
    include_expenses?: boolean;
    include_purchases?: boolean;
  } = {}) =>
    apiRequest<ApiResponse<Record<string, unknown>>>("/finance/backfill/", {
      method: "POST",
      body: JSON.stringify({ dry_run: true, ...data }),
    }),

  cutoverStatus: () =>
    apiRequest<ApiResponse<Record<string, unknown>>>("/finance/cutover/"),

  cutoverAction: (data: { action: "prepare" | "activate" | "disable_posting"; date?: string }) =>
    apiRequest<ApiResponse<Record<string, unknown>>>("/finance/cutover/", {
      method: "POST",
      body: JSON.stringify(data),
    }),
};
