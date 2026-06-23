/** All supported enterprise print document types. */
export type DocumentType =
  | "tax_invoice"
  | "sales_invoice"
  | "proforma_invoice"
  | "credit_note"
  | "debit_note"
  | "sales_return"
  | "purchase_order"
  | "goods_received_note"
  | "supplier_invoice"
  | "purchase_return"
  | "product_list"
  | "stock_report"
  | "inventory_valuation"
  | "stock_movement"
  | "stock_adjustment"
  | "reorder_report"
  | "customer_statement"
  | "customer_ledger"
  | "customer_balance"
  | "supplier_statement"
  | "supplier_ledger"
  | "supplier_balance"
  | "sales_report"
  | "profit_loss"
  | "cash_flow"
  | "expense_report"
  | "tax_report"
  | "vat_report"
  | "delivery_note"
  | "quotation"
  | "barcode_labels"
  | "product_catalog"
  | "receipt"
  | "thermal_receipt"
  | "table_report";

export type DocumentStatus =
  | "paid"
  | "unpaid"
  | "pending"
  | "draft"
  | "completed"
  | "cancelled"
  | "out_of_stock"
  | "low_stock"
  | "active"
  | "sent"
  | "accepted"
  | "overdue";

export interface DocumentBranding {
  companyName: string;
  legalName?: string;
  tagline?: string;
  branchName?: string;
  branchCode?: string;
  address: string;
  phone: string;
  email?: string;
  website?: string;
  taxId?: string;
  logoUrl?: string;
}

export interface DocumentMeta {
  documentNumber: string;
  documentTitle: string;
  issueDate: string;
  dueDate?: string;
  generatedBy?: string;
  branch?: string;
  status?: DocumentStatus;
  reference?: string;
  verificationUrl?: string;
}

export interface KpiCardData {
  label: string;
  value: string;
  accent?: "primary" | "success" | "warning" | "danger" | "neutral";
}

export interface PartyInfo {
  title: string;
  name: string;
  lines?: string[];
}

export interface LineItemRow {
  name: string;
  sku?: string;
  description?: string;
  category?: string;
  imageUrl?: string;
  barcodeDataUrl?: string;
  quantity?: string | number;
  unitPrice?: string;
  discount?: string;
  tax?: string;
  total: string;
  status?: DocumentStatus;
  extra?: Record<string, string>;
}

export interface TableColumn {
  key: string;
  label: string;
  align?: "left" | "center" | "right";
}

export interface FinancialLine {
  label: string;
  value: string;
  emphasis?: boolean;
  highlight?: boolean;
}

export interface SignatureBlock {
  label: string;
  name?: string;
  title?: string;
}

export interface AnalyticsBlock {
  title: string;
  items: { label: string; value: string; pct?: string }[];
}

export type ProductListStatus = "active" | "out_of_stock" | "inactive" | "low_stock";

export interface ProductListRow {
  index: number;
  sku: string;
  name: string;
  imageUrl?: string;
  category: string;
  cost: string;
  price: string;
  stock: number;
  status: ProductListStatus;
}

export interface CategorySummaryRow {
  category: string;
  items: number;
  stock: number;
  stockValue: string;
}

export interface CategoryChartSlice {
  label: string;
  value: number;
  pct: number;
  color: string;
}

export interface ProductListPayload {
  branding: DocumentBranding;
  generatedAt: string;
  kpis: { label: string; value: string; icon: "products" | "categories" | "stock" | "value" }[];
  rows: ProductListRow[];
  categorySummary: CategorySummaryRow[];
  categoryChart: CategoryChartSlice[];
  totals: { items: number; stock: number; stockValue: string };
  pageNumber?: number;
  pageCount?: number;
}

export interface SalesReportKpi {
  label: string;
  value: string;
  icon: "sales" | "orders" | "customers" | "profit";
}

export interface SalesReportProductRow {
  index: number;
  name: string;
  sold: number;
  revenueFormatted: string;
  profitFormatted: string;
}

export interface SalesReportCategorySlice {
  label: string;
  revenue: number;
  revenueFormatted: string;
  pct: number;
  color?: string;
}

export interface SalesReportSummaryLine {
  label: string;
  value: string;
  highlight?: boolean;
}

export interface PurchaseOrderRow {
  index: number;
  name: string;
  quantity: number;
  unitCost: string;
  tax: string;
  total: string;
}

export interface DeliveryNoteRow {
  index: number;
  name: string;
  quantityOrdered: number;
  quantityDelivered: number;
  unit: string;
}

export interface DeliveryNotePayload {
  branding: DocumentBranding;
  deliveryNumber: string;
  deliverTo: PartyInfo;
  metaRows: { label: string; value: string }[];
  rows: DeliveryNoteRow[];
  companyPhone?: string;
  companyEmail?: string;
  companyWebsite?: string;
}

export interface PurchaseOrderPayload {
  branding: DocumentBranding;
  orderNumber: string;
  supplier: PartyInfo;
  metaRows: { label: string; value: string }[];
  rows: PurchaseOrderRow[];
  shippingAddress: string[];
  totals: FinancialLine[];
  grandTotal: string;
  terms?: string[];
}

export interface CustomerReportKpi {
  key: string;
  label: string;
  value: string;
  sub?: string;
  color: string;
  icon?: string;
}

export interface CustomerReportRow {
  index: number;
  name: string;
  code: string;
  phone: string;
  email: string;
  type: string;
  creditLimit: string;
  balance: string;
  lastTransaction: string;
  status: string;
  isActive: boolean;
}

export interface CustomerReportSlice {
  label: string;
  count: number;
  pct: number;
}

export interface CustomerReportTopRow {
  rank: number;
  name: string;
  amount: string;
  pct: string;
}

export interface CustomerReportPayload {
  branding: DocumentBranding;
  reportId: string;
  reportDate: string;
  generatedBy: string;
  generatedAt: string;
  branch?: string;
  printDate: string;
  kpis: CustomerReportKpi[];
  distribution: CustomerReportSlice[];
  monthlyGrowth: { month: string; value: number }[];
  growthYear: number;
  directory: CustomerReportRow[];
  financialSummary: { label: string; value: string }[];
  contactSummary: { label: string; value: string; warning?: boolean }[];
  topBySales: CustomerReportTopRow[];
  topByProfit: CustomerReportTopRow[];
  topByOutstanding: CustomerReportTopRow[];
  qrDataUrl?: string;
  pageNumber?: number;
  pageCount?: number;
}

export interface SalesReportPayload {
  branding: DocumentBranding;
  dateRange: string;
  kpis: SalesReportKpi[];
  hourlySales: { hour: string; value: number }[];
  salesByCategory: SalesReportCategorySlice[];
  topProducts: SalesReportProductRow[];
  summary: SalesReportSummaryLine[];
  pageNumber?: number;
  pageCount?: number;
}

export interface SalesDocumentPayload {
  variant: "invoice" | "quotation";
  branding: DocumentBranding;
  meta: DocumentMeta;
  party: PartyInfo;
  metaRows: { label: string; value: string }[];
  rows: LineItemRow[];
  financials: FinancialLine[];
  amountInWords?: string;
  paymentMethods?: { title: string; lines: string[] }[];
  terms?: string[];
  qrDataUrl?: string;
  salesPerson?: string;
  shipping?: string;
}

export interface EnterpriseDocument {
  type: DocumentType;
  branding: DocumentBranding;
  meta: DocumentMeta;
  /** When set, uses the premium invoice/quotation layout matching brand designs. */
  salesPayload?: SalesDocumentPayload;
  /** When set, uses the premium product list report layout. */
  productListPayload?: ProductListPayload;
  /** When set, uses the premium sales report layout. */
  salesReportPayload?: SalesReportPayload;
  /** When set, uses the premium purchase order layout. */
  purchaseOrderPayload?: PurchaseOrderPayload;
  /** When set, uses the premium delivery note layout. */
  deliveryNotePayload?: DeliveryNotePayload;
  /** When set, uses the premium customers report layout. */
  customerReportPayload?: CustomerReportPayload;
  kpis?: KpiCardData[];
  billTo?: PartyInfo;
  shipTo?: PartyInfo;
  columns: TableColumn[];
  rows: LineItemRow[];
  financials?: FinancialLine[];
  analytics?: AnalyticsBlock[];
  notes?: string;
  terms?: string;
  signatures?: SignatureBlock[];
  qrDataUrl?: string;
  barcodeDataUrl?: string;
  watermark?: string;
  footerMessage?: string;
  confidential?: boolean;
}

export interface TableReportDocument {
  title: string;
  subtitle?: string;
  branding: DocumentBranding;
  columns: { header: string; align?: "left" | "center" | "right" }[];
  rows: string[][];
  kpis?: KpiCardData[];
  reference?: string;
  generatedAt?: string;
  generatedBy?: string;
}

export type PageSize = "a4-portrait" | "a4-landscape" | "letter" | "thermal-80" | "thermal-58";

export interface PrintOptions {
  pageSize?: PageSize;
  filename?: string;
}
