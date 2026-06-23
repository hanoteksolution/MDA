import { formatCurrency } from "@/utils/cn";
import type { CustomerReportPrintData } from "@/types/models/partners";
import { getDocumentBranding } from "./branding";
import type { CustomerReportPayload, DocumentBranding, EnterpriseDocument } from "./types";
import { nowStamp } from "./utils";

const KPI_CONFIG: {
  key: keyof CustomerReportPrintData["kpis"];
  label: string;
  sub: string;
  color: string;
  icon: string;
  format?: "currency";
}[] = [
  { key: "total", label: "Total Customers", sub: "All Customers", color: "#2563EB", icon: "👥" },
  { key: "active", label: "Active Customers", sub: "Currently Active", color: "#16A34A", icon: "✓" },
  { key: "corporate", label: "Corporate", sub: "Business Accounts", color: "#2563EB", icon: "🏢" },
  { key: "retail", label: "Retail", sub: "Individual Buyers", color: "#8B5CF6", icon: "🛒" },
  { key: "wholesale", label: "Wholesale", sub: "Bulk Buyers", color: "#F59E0B", icon: "📦" },
  { key: "with_credit", label: "With Credit", sub: "Credit Accounts", color: "#EAB308", icon: "💳" },
  { key: "outstanding", label: "Outstanding", sub: "Total Receivables", color: "#DC2626", icon: "⚠", format: "currency" },
  { key: "new_customers", label: "New Customers", sub: "This Month", color: "#16A34A", icon: "✨" },
];

function formatTopRows(
  rows: { rank: number; name: string; amount: number; pct: number }[]
): CustomerReportPayload["topBySales"] {
  return rows.map((r) => ({
    rank: r.rank,
    name: r.name,
    amount: formatCurrency(r.amount),
    pct: `${r.pct}%`,
  }));
}

export function buildCustomerReportPayload(
  data: CustomerReportPrintData,
  branding: DocumentBranding,
  qrDataUrl?: string
): CustomerReportPayload {
  const total = data.kpis.total || 1;
  const pct = (n: number) => `${Math.round((n / total) * 100)}%`;

  return {
    branding,
    reportId: data.report_id,
    reportDate: data.report_date,
    generatedBy: data.generated_by,
    generatedAt: nowStamp(),
    branch: data.branch ?? undefined,
    printDate: new Date().toISOString().slice(0, 10),
    kpis: KPI_CONFIG.map((k) => ({
      key: k.key,
      label: k.label,
      sub: k.sub,
      color: k.color,
      icon: k.icon,
      value:
        k.format === "currency"
          ? formatCurrency(data.kpis[k.key] as number)
          : String(data.kpis[k.key]),
    })),
    distribution: data.distribution,
    monthlyGrowth: data.monthly_growth,
    growthYear: data.growth_year,
    directory: data.directory.map((row) => ({
      index: row.index,
      name: row.name,
      code: row.code,
      phone: row.phone,
      email: row.email,
      type: row.type,
      creditLimit: formatCurrency(row.credit_limit),
      balance: formatCurrency(row.balance),
      lastTransaction: row.last_transaction,
      status: row.status,
      isActive: row.is_active,
    })),
    financialSummary: [
      { label: "Total Credit Limit", value: formatCurrency(data.financial_summary.total_credit_limit) },
      { label: "Total Outstanding", value: formatCurrency(data.financial_summary.total_outstanding) },
      { label: "Average Customer Value", value: formatCurrency(data.financial_summary.avg_customer_value) },
      { label: "Highest Customer Balance", value: formatCurrency(data.financial_summary.highest_balance) },
    ],
    contactSummary: [
      { label: "With Email", value: `${data.contact_summary.with_email} (${pct(data.contact_summary.with_email)})` },
      { label: "With Phone", value: `${data.contact_summary.with_phone} (${pct(data.contact_summary.with_phone)})` },
      { label: "With Both", value: `${data.contact_summary.with_both} (${pct(data.contact_summary.with_both)})` },
      {
        label: "Missing Info",
        value: `${data.contact_summary.missing_info} (${pct(data.contact_summary.missing_info)})`,
        warning: data.contact_summary.missing_info > 0,
      },
    ],
    topBySales: formatTopRows(data.top_by_sales),
    topByProfit: formatTopRows(data.top_by_profit),
    topByOutstanding: formatTopRows(data.top_by_outstanding),
    qrDataUrl,
    pageNumber: 1,
    pageCount: 1,
  };
}

export function documentFromCustomerReport(
  data: CustomerReportPrintData,
  branding: DocumentBranding,
  qrDataUrl?: string
): EnterpriseDocument {
  const payload = buildCustomerReportPayload(data, branding, qrDataUrl);
  return {
    type: "customer_statement",
    branding,
    meta: {
      documentNumber: data.report_id,
      documentTitle: "Customers Report",
      issueDate: data.report_date,
      generatedBy: data.generated_by,
      branch: data.branch ?? undefined,
      status: "completed",
    },
    customerReportPayload: payload,
    columns: [],
    rows: [],
    confidential: true,
    qrDataUrl,
  };
}

export async function buildCustomerReportDocument(
  data: CustomerReportPrintData,
  qrDataUrl?: string
): Promise<EnterpriseDocument> {
  const branding = await getDocumentBranding();
  return documentFromCustomerReport(data, branding, qrDataUrl);
}
