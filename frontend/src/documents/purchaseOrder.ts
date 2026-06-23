import { formatCurrency } from "@/utils/cn";
import type { PurchaseOrder } from "@/types/models/partners";
import { getDocumentBranding } from "./branding";
import type { DocumentBranding, EnterpriseDocument, PurchaseOrderPayload } from "./types";

function formatDocDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("en-GB", { day: "2-digit", month: "2-digit", year: "numeric" });
}

function paymentTermsLabel(days: number | undefined): string {
  const n = days ?? 30;
  return `Net ${n} Days`;
}

function lineTax(po: PurchaseOrder, lineTotal: number): number {
  if (po.subtotal <= 0 || po.tax_amount <= 0) return 0;
  return (lineTotal / po.subtotal) * po.tax_amount;
}

export function buildPurchaseOrderPayload(
  po: PurchaseOrder,
  branding: DocumentBranding
): PurchaseOrderPayload {
  const items = po.items ?? [];
  const rows = items.map((item, i) => {
    const lineTotal = item.line_total ?? item.quantity_ordered * item.unit_cost;
    const tax = lineTax(po, lineTotal);
    return {
      index: i + 1,
      name: item.product_name ?? "Item",
      quantity: item.quantity_ordered,
      unitCost: formatCurrency(item.unit_cost),
      tax: formatCurrency(tax),
      total: formatCurrency(lineTotal + tax),
    };
  });

  const supplierContact = [
    po.supplier_phone ? `Phone: ${po.supplier_phone}` : "",
    po.supplier_email ? `Email: ${po.supplier_email}` : "",
  ]
    .filter(Boolean)
    .join(" | ");

  const supplierLines = [
    po.supplier_address || "",
    supplierContact,
  ].filter(Boolean);

  const shippingName = branding.companyName || "MDA Retail Store";
  const shippingLines = [
    shippingName,
    po.branch_address || branding.address || "",
    branding.branchName ? `${po.branch_name}` : po.branch_name,
  ].filter(Boolean);

  const paymentTerms =
    po.supplier_payment_terms != null
      ? paymentTermsLabel(po.supplier_payment_terms)
      : paymentTermsLabel(30);

  const terms = po.notes
    ? po.notes.split(/[.\n]/).map((s) => s.trim()).filter(Boolean).slice(0, 4)
    : undefined;

  return {
    branding,
    orderNumber: po.order_number,
    supplier: {
      title: "Supplier",
      name: po.supplier_name,
      lines: supplierLines,
    },
    metaRows: [
      { label: "PO Date", value: formatDocDate(po.order_date) },
      { label: "Expected Date", value: po.expected_date ? formatDocDate(po.expected_date) : "—" },
      { label: "Payment Terms", value: paymentTerms },
      { label: "Created By", value: po.ordered_by ?? "MDA ERP" },
      { label: "Branch", value: po.branch_name },
    ],
    rows,
    shippingAddress: shippingLines,
    totals: [
      { label: "Subtotal", value: formatCurrency(po.subtotal) },
      { label: "Tax", value: formatCurrency(po.tax_amount) },
    ],
    grandTotal: formatCurrency(po.total_amount),
    terms,
  };
}

export function documentFromPurchaseOrder(
  po: PurchaseOrder,
  branding: DocumentBranding
): EnterpriseDocument {
  const payload = buildPurchaseOrderPayload(po, branding);
  return {
    type: "purchase_order",
    branding,
    meta: {
      documentNumber: po.order_number,
      documentTitle: "Purchase Order",
      issueDate: formatDocDate(po.order_date),
      generatedBy: po.ordered_by ?? "MDA ERP",
      branch: po.branch_name,
      status: "sent",
    },
    purchaseOrderPayload: payload,
    columns: [],
    rows: [],
    confidential: false,
  };
}

export async function buildPurchaseOrderDocument(po: PurchaseOrder): Promise<EnterpriseDocument> {
  const branding = await getDocumentBranding({
    name: po.branch_name,
    address: po.branch_address,
  });
  return documentFromPurchaseOrder(po, branding);
}
