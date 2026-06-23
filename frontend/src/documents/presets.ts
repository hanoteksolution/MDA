import { formatCurrency } from "@/utils/cn";
import type { PosReceipt } from "@/services/api/pos";
import type { Quotation } from "@/services/api/sales";
import type { DocumentBranding } from "./types";
import { brandingFromReceiptCompany } from "./branding";
import type { DocumentType, EnterpriseDocument, FinancialLine, LineItemRow, SalesDocumentPayload } from "./types";
import { getPaymentLabel, getTaxRateLabel, getVerificationUrl } from "@/modules/pos/receipt/receiptFormat";
import { amountInWords } from "./utils/amountInWords";

const SALES_COLUMNS = [
  { key: "item", label: "Item Description" },
  { key: "qty", label: "Qty", align: "center" as const },
  { key: "unit_price", label: "Unit Price", align: "right" as const },
  { key: "discount", label: "Discount", align: "right" as const },
  { key: "tax", label: "Tax", align: "right" as const },
  { key: "total", label: "Amount", align: "right" as const },
];

const INVENTORY_COLUMNS = [
  { key: "item", label: "Product" },
  { key: "qty", label: "Qty", align: "center" as const },
  { key: "col_2", label: "Cost", align: "right" as const },
  { key: "col_3", label: "Price", align: "right" as const },
  { key: "status", label: "Status", align: "center" as const },
  { key: "total", label: "Value", align: "right" as const },
];

export const DOCUMENT_TITLES: Record<DocumentType, string> = {
  tax_invoice: "Tax Invoice",
  sales_invoice: "Sales Invoice",
  proforma_invoice: "Proforma Invoice",
  credit_note: "Credit Note",
  debit_note: "Debit Note",
  sales_return: "Sales Return",
  purchase_order: "Purchase Order",
  goods_received_note: "Goods Received Note",
  supplier_invoice: "Supplier Invoice",
  purchase_return: "Purchase Return",
  product_list: "Product List",
  stock_report: "Stock Report",
  inventory_valuation: "Inventory Valuation",
  stock_movement: "Stock Movement",
  stock_adjustment: "Stock Adjustment",
  reorder_report: "Reorder Report",
  customer_statement: "Customer Statement",
  customer_ledger: "Customer Ledger",
  customer_balance: "Customer Balance Report",
  supplier_statement: "Supplier Statement",
  supplier_ledger: "Supplier Ledger",
  supplier_balance: "Supplier Balance Report",
  sales_report: "Sales Report",
  profit_loss: "Profit & Loss Statement",
  cash_flow: "Cash Flow Statement",
  expense_report: "Expense Report",
  tax_report: "Tax Report",
  vat_report: "VAT Report",
  delivery_note: "Delivery Note",
  quotation: "Quotation",
  barcode_labels: "Barcode Labels",
  product_catalog: "Product Catalog",
  receipt: "Receipt",
  thermal_receipt: "Thermal Receipt",
  table_report: "Report",
};

function formatDocDate(isoOrDisplay: string): string {
  const d = new Date(isoOrDisplay);
  if (!Number.isNaN(d.getTime())) {
    return d.toLocaleDateString("en-GB", { day: "2-digit", month: "2-digit", year: "numeric" });
  }
  return isoOrDisplay.split("·")[0]?.trim() ?? isoOrDisplay;
}

function addDays(isoDate: string, days: number): string {
  const d = new Date(isoDate);
  if (Number.isNaN(d.getTime())) return isoDate;
  d.setDate(d.getDate() + days);
  return d.toLocaleDateString("en-GB", { day: "2-digit", month: "2-digit", year: "numeric" });
}

function rowTaxLabel(receipt: PosReceipt): string {
  const rate = receipt.tax_rate ?? 0;
  if (rate <= 0) return "—";
  return `${Math.round(rate * 100)}%`;
}

function receiptRows(receipt: PosReceipt): LineItemRow[] {
  const taxCol = rowTaxLabel(receipt);
  return receipt.items.map((item) => ({
    name: item.name,
    sku: item.sku,
    imageUrl: item.image,
    quantity: item.quantity,
    unitPrice: formatCurrency(item.unit_price),
    discount: "$0.00",
    tax: taxCol,
    total: formatCurrency(item.line_total),
  }));
}

function receiptFinancials(receipt: PosReceipt): FinancialLine[] {
  const taxLabel = getTaxRateLabel(receipt);
  return [
    { label: "Subtotal", value: formatCurrency(receipt.subtotal) },
    {
      label: "Discount",
      value: receipt.discount_amount > 0 ? `−${formatCurrency(receipt.discount_amount)}` : formatCurrency(0),
    },
    { label: taxLabel, value: formatCurrency(receipt.tax_amount) },
    { label: "Grand Total", value: formatCurrency(receipt.total_amount), highlight: true },
  ];
}

function customerLines(receipt: PosReceipt): string[] {
  const lines: string[] = [];
  if (receipt.customer_address) lines.push(receipt.customer_address);
  if (receipt.customer_phone) lines.push(receipt.customer_phone);
  if (receipt.customer_email) lines.push(receipt.customer_email);
  if (lines.length === 0 && receipt.customer_name && receipt.customer_name !== "Walk-in Customer") {
    lines.push("—");
  }
  return lines;
}

function paymentMethodsForReceipt(receipt: PosReceipt): { title: string; lines: string[] }[] {
  return [
    {
      title: "Bank Transfer",
      lines: [
        `Bank: ${receipt.company.name} Bank`,
        receipt.payment_method === "bank" && receipt.payment_reference
          ? `Account: ${receipt.payment_reference}`
          : "Account: Contact accounts department",
      ],
    },
    {
      title: "Mobile Money",
      lines: [
        receipt.merchant?.label ? `Service: ${receipt.merchant.label}` : "Service: Mobile Money",
        receipt.merchant_reference
          ? `Number: ${receipt.merchant_reference}`
          : receipt.merchant?.merchant_number
            ? `Number: ${receipt.merchant.merchant_number}`
            : "Number: —",
      ],
    },
  ];
}

function buildSalesPayload(
  receipt: PosReceipt,
  type: DocumentType,
  branding: EnterpriseDocument["branding"],
  meta: EnterpriseDocument["meta"],
  rows: LineItemRow[],
  financials: FinancialLine[],
  assets?: { qr?: string }
): SalesDocumentPayload {
  const isQuote = type === "quotation";
  const issueDate = formatDocDate(receipt.date);
  const branchLabel = receipt.branch.name;

  const metaRows = isQuote
    ? [
        { label: "Quote Date", value: issueDate },
        { label: "Valid Until", value: addDays(receipt.date, 14) },
        { label: "Sales Person", value: receipt.cashier },
        { label: "Branch", value: branchLabel },
      ]
    : [
        { label: "Invoice Date", value: issueDate },
        { label: "Due Date", value: addDays(receipt.date, 30) },
        { label: "Payment Terms", value: "Net 7 Days" },
        { label: "Sales Person", value: receipt.cashier },
        { label: "Branch", value: branchLabel },
      ];

  const terms = receipt.return_policy
    ? receipt.return_policy.split(/[.\n]/).map((s) => s.trim()).filter(Boolean).slice(0, 4)
    : undefined;

  return {
    variant: isQuote ? "quotation" : "invoice",
    branding,
    meta,
    party: {
      title: isQuote ? "Quote To" : "Bill To",
      name: receipt.customer_name,
      lines: customerLines(receipt),
    },
    metaRows,
    rows,
    financials,
    amountInWords: isQuote ? undefined : amountInWords(receipt.total_amount),
    paymentMethods: isQuote ? undefined : paymentMethodsForReceipt(receipt),
    terms,
    qrDataUrl: assets?.qr,
    salesPerson: receipt.cashier,
    shipping: isQuote ? undefined : formatCurrency(0),
  };
}

const SALES_LAYOUT_TYPES = new Set<DocumentType>(["tax_invoice", "sales_invoice", "proforma_invoice", "quotation"]);

/** Build sales layout payload from a generic enterprise doc when salesPayload is missing. */
export function enterpriseToSalesPayload(doc: EnterpriseDocument): SalesDocumentPayload | null {
  if (!SALES_LAYOUT_TYPES.has(doc.type)) return null;
  const isQuote = doc.type === "quotation";
  const issueDate = doc.meta.issueDate;
  return {
    variant: isQuote ? "quotation" : "invoice",
    branding: doc.branding,
    meta: doc.meta,
    party: doc.billTo ?? { title: isQuote ? "Quote To" : "Bill To", name: "—" },
    metaRows: isQuote
      ? [
          { label: "Quote Date", value: issueDate },
          { label: "Valid Until", value: doc.meta.dueDate ?? issueDate },
          { label: "Sales Person", value: doc.meta.generatedBy ?? "—" },
          { label: "Branch", value: doc.meta.branch ?? doc.branding.branchName ?? "—" },
        ]
      : [
          { label: "Invoice Date", value: issueDate },
          { label: "Due Date", value: doc.meta.dueDate ?? issueDate },
          { label: "Payment Terms", value: "Net 7 Days" },
          { label: "Sales Person", value: doc.meta.generatedBy ?? "—" },
          { label: "Branch", value: doc.meta.branch ?? doc.branding.branchName ?? "—" },
        ],
    rows: doc.rows,
    financials: doc.financials ?? [],
    amountInWords: isQuote ? undefined : amountInWords(parseFloat(doc.financials?.find((f) => f.highlight)?.value?.replace(/[^0-9.-]/g, "") ?? "0") || 0),
    paymentMethods: isQuote ? undefined : [{ title: "Bank Transfer", lines: ["See accounts department."] }],
    terms: doc.terms?.split(/[.\n]/).map((s) => s.trim()).filter(Boolean).slice(0, 4),
    qrDataUrl: doc.qrDataUrl,
    shipping: isQuote ? undefined : formatCurrency(0),
  };
}

export function documentFromQuotation(
  q: Quotation,
  branding: DocumentBranding,
  assets?: { qr?: string },
  generatedBy = "MDA ERP"
): EnterpriseDocument {
  const afterDiscount = q.subtotal - q.discount_amount;
  const taxRate = afterDiscount > 0 && q.tax_amount > 0 ? q.tax_amount / afterDiscount : 0;
  const taxLabel = taxRate > 0 ? `Tax (${Math.round(taxRate * 100)}%)` : "Tax (0%)";
  const taxCol = taxRate > 0 ? `${Math.round(taxRate * 100)}%` : "—";

  const rows: LineItemRow[] = (q.items ?? []).map((item) => ({
    name: item.product_name ?? "Item",
    sku: item.product_sku,
    quantity: item.quantity,
    unitPrice: formatCurrency(item.unit_price),
    discount: "$0.00",
    tax: taxCol,
    total: formatCurrency(item.line_total ?? item.quantity * item.unit_price),
  }));

  const financials: FinancialLine[] = [
    { label: "Subtotal", value: formatCurrency(q.subtotal) },
    {
      label: "Discount",
      value: q.discount_amount > 0 ? `−${formatCurrency(q.discount_amount)}` : formatCurrency(0),
    },
    { label: taxLabel, value: formatCurrency(q.tax_amount) },
    { label: "Grand Total", value: formatCurrency(q.total_amount), highlight: true },
  ];

  const issueDate = formatDocDate(q.date);
  const validUntil = q.valid_until ? formatDocDate(q.valid_until) : addDays(q.date, 14);

  const meta = {
    documentNumber: q.number,
    documentTitle: "Quotation",
    issueDate,
    dueDate: validUntil,
    generatedBy,
    branch: q.branch_name,
    status: "sent" as const,
  };

  const salesPayload: SalesDocumentPayload = {
    variant: "quotation",
    branding,
    meta,
    party: { title: "Quote To", name: q.customer_name, lines: [] },
    metaRows: [
      { label: "Quote Date", value: issueDate },
      { label: "Valid Until", value: validUntil },
      { label: "Sales Person", value: generatedBy },
      { label: "Branch", value: q.branch_name },
    ],
    rows,
    financials,
    terms: q.notes
      ? q.notes.split(/[.\n]/).map((s) => s.trim()).filter(Boolean).slice(0, 4)
      : undefined,
    qrDataUrl: assets?.qr,
  };

  return {
    type: "quotation",
    branding,
    meta,
    salesPayload,
    columns: SALES_COLUMNS,
    rows,
    financials,
    billTo: { title: "Quote To", name: q.customer_name },
    signatures: [{ label: "Customer Signature" }, { label: "Authorized Signature" }],
    qrDataUrl: assets?.qr,
    confidential: false,
  };
}

export function documentFromReceipt(
  receipt: PosReceipt,
  type: DocumentType = "tax_invoice",
  assets?: { qr?: string; barcode?: string }
): EnterpriseDocument {
  const paymentLabel = getPaymentLabel(receipt);
  const status = receipt.payment_method === "cash" || receipt.total_amount > 0 ? "paid" : "pending";
  const isQuote = type === "quotation";
  const branding = brandingFromReceiptCompany(receipt.company, receipt.branch);
  const rows = receiptRows(receipt);
  const financials = receiptFinancials(receipt);

  const meta = {
    documentNumber: receipt.invoice_number,
    documentTitle: DOCUMENT_TITLES[type] ?? "Invoice",
    issueDate: receipt.datetime_display ?? `${receipt.date} ${receipt.time}`,
    dueDate: addDays(receipt.date, 30),
    generatedBy: receipt.cashier,
    branch: receipt.branch.name,
    status: isQuote ? ("sent" as const) : (status as "paid"),
    reference: receipt.payment_reference || receipt.merchant_reference,
    verificationUrl: getVerificationUrl(receipt),
  };

  const salesPayload = SALES_LAYOUT_TYPES.has(type)
    ? buildSalesPayload(receipt, type, branding, meta, rows, financials, assets)
    : undefined;

  return {
    type,
    branding,
    meta,
    salesPayload,
    kpis: [
      { label: "Total Amount", value: formatCurrency(receipt.total_amount), accent: "primary" },
      { label: "Tax", value: formatCurrency(receipt.tax_amount), accent: "warning" },
      { label: "Discount", value: formatCurrency(receipt.discount_amount), accent: "success" },
      { label: "Items", value: String(receipt.items.length), accent: "neutral" },
    ],
    billTo: {
      title: isQuote ? "Quote To" : "Bill To",
      name: receipt.customer_name,
      lines: customerLines(receipt),
    },
    columns: SALES_COLUMNS,
    rows,
    financials,
    analytics: [
      {
        title: "Payment Verification",
        items: [
          { label: "Method", value: paymentLabel },
          { label: "Reference", value: receipt.payment_reference || receipt.merchant_reference || "—" },
          { label: "Status", value: "Verified", pct: "✓" },
        ],
      },
    ],
    notes: receipt.footer,
    terms: receipt.return_policy,
    signatures: [
      { label: "Prepared By", name: receipt.cashier },
      { label: "Authorized Signature" },
      { label: "Received By" },
    ],
    qrDataUrl: assets?.qr,
    barcodeDataUrl: assets?.barcode,
    footerMessage: receipt.footer,
    confidential: false,
  };
}

export function defaultInventoryDoc(
  branding: EnterpriseDocument["branding"],
  title: DocumentType,
  rows: LineItemRow[],
  kpis: EnterpriseDocument["kpis"]
): EnterpriseDocument {
  return {
    type: title,
    branding,
    meta: {
      documentNumber: `${title.toUpperCase().slice(0, 3)}-${Date.now().toString().slice(-6)}`,
      documentTitle: DOCUMENT_TITLES[title],
      issueDate: new Date().toLocaleDateString(),
      generatedBy: "MDA ERP",
      status: "completed",
    },
    kpis,
    columns: INVENTORY_COLUMNS,
    rows,
    signatures: [
      { label: "Prepared By" },
      { label: "Approved By" },
      { label: "Received By" },
    ],
    footerMessage: "MDA Retail — Inventory Management",
    confidential: true,
  };
}
