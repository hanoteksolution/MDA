import { formatCurrency } from "@/utils/cn";
import { getDocumentBranding } from "./branding";
import type { DocumentBranding, EnterpriseDocument, SalesReportPayload } from "./types";

const CHART_COLORS = ["#2563EB", "#60A5FA", "#10B981", "#F59E0B", "#001B3D", "#8B5CF6"];

export interface SalesReportApiData {
  date_from: string;
  date_to: string;
  kpis: {
    total_sales: number;
    total_orders: number;
    total_customers: number;
    total_profit: number;
  };
  hourly_sales: { hour: string; value: number }[];
  sales_by_category: { label: string; revenue: number; pct: number }[];
  top_products: {
    index: number;
    name: string;
    sku: string;
    sold: number;
    revenue: number;
    profit: number;
  }[];
  summary: {
    total_sales: number;
    total_cost: number;
    total_profit: number;
    profit_margin: number;
    discounts: number;
    returns: number;
    tax_collected: number;
  };
}

function formatReportDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("en-GB", { day: "2-digit", month: "2-digit", year: "numeric" });
}

export function buildSalesReportPayload(
  data: SalesReportApiData,
  branding: DocumentBranding
): SalesReportPayload {
  const dateRange = `${formatReportDate(data.date_from)} - ${formatReportDate(data.date_to)}`;

  return {
    branding,
    dateRange,
    kpis: [
      { label: "Total Sales", value: formatCurrency(data.kpis.total_sales), icon: "sales" },
      { label: "Total Orders", value: String(data.kpis.total_orders), icon: "orders" },
      { label: "Total Customers", value: String(data.kpis.total_customers), icon: "customers" },
      { label: "Total Profit", value: formatCurrency(data.kpis.total_profit), icon: "profit" },
    ],
    hourlySales: data.hourly_sales,
    salesByCategory: data.sales_by_category.map((c, i) => ({
      label: c.label,
      revenue: c.revenue,
      revenueFormatted: formatCurrency(c.revenue),
      pct: c.pct,
      color: CHART_COLORS[i % CHART_COLORS.length],
    })),
    topProducts: data.top_products.map((p) => ({
      index: p.index,
      name: p.name,
      sold: p.sold,
      revenueFormatted: formatCurrency(p.revenue),
      profitFormatted: formatCurrency(p.profit),
    })),
    summary: [
      { label: "Total Sales", value: formatCurrency(data.summary.total_sales) },
      { label: "Total Cost", value: formatCurrency(data.summary.total_cost) },
      { label: "Total Profit", value: formatCurrency(data.summary.total_profit), highlight: true },
      { label: "Profit Margin", value: `${data.summary.profit_margin}%`, highlight: true },
      { label: "Discounts", value: formatCurrency(data.summary.discounts) },
      { label: "Returns", value: formatCurrency(data.summary.returns) },
      { label: "Tax Collected", value: formatCurrency(data.summary.tax_collected) },
    ],
    pageNumber: 1,
    pageCount: 1,
  };
}

export function documentFromSalesReport(
  data: SalesReportApiData,
  branding: DocumentBranding
): EnterpriseDocument {
  const payload = buildSalesReportPayload(data, branding);
  return {
    type: "sales_report",
    branding,
    meta: {
      documentNumber: `SR-${Date.now().toString().slice(-6)}`,
      documentTitle: "Sales Report",
      issueDate: payload.dateRange,
      generatedBy: "MDA ERP",
      status: "completed",
    },
    salesReportPayload: payload,
    columns: [],
    rows: [],
    footerMessage: "Thank you for your business!",
    confidential: false,
  };
}

export async function buildSalesReportDocument(data: SalesReportApiData): Promise<EnterpriseDocument> {
  const branding = await getDocumentBranding();
  return documentFromSalesReport(data, branding);
}
