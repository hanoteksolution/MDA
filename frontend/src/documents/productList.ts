import { resolveMediaUrl } from "@/config/api";
import { formatCurrency } from "@/utils/cn";
import type { Product } from "@/types/models/catalog";
import { getDocumentBranding } from "./branding";
import type {
  CategoryChartSlice,
  CategorySummaryRow,
  DocumentBranding,
  EnterpriseDocument,
  ProductListPayload,
  ProductListRow,
  ProductListStatus,
} from "./types";

const CHART_COLORS = ["#2563EB", "#60A5FA", "#F59E0B", "#001B3D", "#10B981", "#8B5CF6"];

function productStatus(p: Product): ProductListStatus {
  const stock = p.total_stock ?? 0;
  if (!p.is_active) return "inactive";
  if (stock <= 0) return "out_of_stock";
  if (stock <= p.minimum_stock) return "low_stock";
  return "active";
}

function formatGeneratedAt(): string {
  const d = new Date();
  const date = d.toLocaleDateString("en-GB", { day: "2-digit", month: "2-digit", year: "numeric" });
  const time = d.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", hour12: true });
  return `${date} · ${time}`;
}

function buildCategorySummary(products: Product[]): CategorySummaryRow[] {
  const map = new Map<string, { items: number; stock: number; value: number }>();
  for (const p of products) {
    const cat = p.category_name || "Uncategorized";
    const entry = map.get(cat) ?? { items: 0, stock: 0, value: 0 };
    const stock = p.total_stock ?? 0;
    entry.items += 1;
    entry.stock += stock;
    entry.value += stock * p.cost_price;
    map.set(cat, entry);
  }
  return Array.from(map.entries())
    .map(([category, d]) => ({
      category,
      items: d.items,
      stock: d.stock,
      stockValue: formatCurrency(d.value),
    }))
    .sort((a, b) => b.stock - a.stock);
}

function buildCategoryChart(summary: CategorySummaryRow[]): CategoryChartSlice[] {
  const totalStock = summary.reduce((s, c) => s + c.stock, 0);
  if (totalStock <= 0) {
    return summary.slice(0, 4).map((c, i) => ({
      label: c.category,
      value: c.stock,
      pct: summary.length ? Math.round(100 / summary.length) : 0,
      color: CHART_COLORS[i % CHART_COLORS.length],
    }));
  }
  return summary.slice(0, 6).map((c, i) => ({
    label: c.category,
    value: c.stock,
    pct: Math.round((c.stock / totalStock) * 100),
    color: CHART_COLORS[i % CHART_COLORS.length],
  }));
}

export function buildProductListPayload(
  products: Product[],
  branding: DocumentBranding
): ProductListPayload {
  const categories = new Set(products.map((p) => p.category_name || "Uncategorized"));
  const totalStock = products.reduce((s, p) => s + (p.total_stock ?? 0), 0);
  const stockValue = products.reduce((s, p) => s + (p.total_stock ?? 0) * p.cost_price, 0);

  const rows: ProductListRow[] = products.map((p, i) => ({
    index: i + 1,
    sku: p.sku,
    name: p.name,
    imageUrl: resolveMediaUrl(p.image) ?? (p.sku ? `https://picsum.photos/seed/${encodeURIComponent(p.sku)}/64/64` : undefined),
    category: p.category_name || "—",
    cost: formatCurrency(p.cost_price),
    price: formatCurrency(p.selling_price),
    stock: p.total_stock ?? 0,
    status: productStatus(p),
  }));

  const categorySummary = buildCategorySummary(products);
  const categoryChart = buildCategoryChart(categorySummary);

  return {
    branding,
    generatedAt: formatGeneratedAt(),
    kpis: [
      { label: "Total Products", value: String(products.length), icon: "products" },
      { label: "Total Categories", value: String(categories.size), icon: "categories" },
      { label: "Total Stock", value: totalStock.toLocaleString(), icon: "stock" },
      { label: "Stock Value", value: formatCurrency(stockValue), icon: "value" },
    ],
    rows,
    categorySummary,
    categoryChart,
    totals: {
      items: products.length,
      stock: totalStock,
      stockValue: formatCurrency(stockValue),
    },
    pageNumber: 1,
    pageCount: 1,
  };
}

export function documentFromProducts(products: Product[], branding: DocumentBranding): EnterpriseDocument {
  const payload = buildProductListPayload(products, branding);
  return {
    type: "product_list",
    branding,
    meta: {
      documentNumber: `PL-${Date.now().toString().slice(-6)}`,
      documentTitle: "Product List",
      issueDate: payload.generatedAt,
      generatedBy: "MDA ERP",
      status: "completed",
    },
    productListPayload: payload,
    columns: [],
    rows: [],
    footerMessage: "Thank you for using MDA Retail ERP & POS",
    confidential: false,
  };
}

export async function fetchAllProductsForReport(
  fetchPage: (params: Record<string, string | number | undefined>) => Promise<{ data: { results: Product[]; count: number } }>,
  filters: Record<string, string | number | undefined> = {}
): Promise<Product[]> {
  const pageSize = 500;
  const first = await fetchPage({ ...filters, page: 1, page_size: pageSize });
  const all = [...first.data.results];
  const totalPages = Math.ceil(first.data.count / pageSize);
  for (let page = 2; page <= totalPages; page++) {
    const res = await fetchPage({ ...filters, page, page_size: pageSize });
    all.push(...res.data.results);
  }
  return all;
}

export async function buildProductListDocument(
  products: Product[],
  branding?: DocumentBranding
): Promise<EnterpriseDocument> {
  const brand = branding ?? (await getDocumentBranding());
  return documentFromProducts(products, brand);
}
