import { THERMAL_RECEIPT_PRINT_CSS } from "@/documents/styles/thermalReceipt";
import { getDocumentBranding } from "@/documents/branding";
import { renderPremiumThermalSlip, type ThermalSlipItem } from "@/documents/renderers/thermal";
import { printThermalDocument } from "@/utils/printThermal";
import { posApi } from "@/services/api/pos";
import type { CartLine } from "../hooks/usePosCart";

export interface CartSlipData {
  title: string;
  customerName: string;
  waiterName?: string;
  branchName?: string;
  branchCode?: string;
  branchId?: string;
  cart: CartLine[];
  subtotal: number;
  discount: number;
  tax: number;
  taxRate: number;
  grandTotal: number;
  notes?: string;
  heldAt?: string;
  isHold?: boolean;
}

async function allocateSlipNumber(kind: "order" | "hold", branchId?: string): Promise<string> {
  const res = await posApi.allocateReceiptNumber({
    kind,
    branch_id: branchId,
  });
  return res.data.number;
}

function cartToItems(cart: CartLine[]): ThermalSlipItem[] {
  return cart.map((item) => ({
    name: item.name,
    quantity: item.qty,
    unit_price: item.price,
    line_total: item.price * item.qty,
  }));
}

export async function printCartSlip(data: CartSlipData): Promise<void> {
  const branding = await getDocumentBranding(
    data.branchName ? { name: data.branchName, code: data.branchCode } : undefined
  );

  const ref = await allocateSlipNumber(data.isHold ? "hold" : "order", data.branchId);

  const body = renderPremiumThermalSlip(
    {
      title: data.title,
      slipNumber: ref,
      customerName: data.customerName,
      waiterName: data.waiterName,
      heldAt: data.heldAt,
      notes: data.notes,
      items: cartToItems(data.cart),
      subtotal: data.subtotal,
      discount: data.discount,
      tax: data.tax,
      taxRate: data.taxRate,
      grandTotal: data.grandTotal,
      branding,
      isHold: data.isHold,
    },
    { qrDataUrl: "", barcodeDataUrl: "" },
    "80mm"
  );

  await printThermalDocument(body, {
    width: "80mm",
    css: THERMAL_RECEIPT_PRINT_CSS,
  });
}

export function printHeldSaleSlip(
  data: Omit<CartSlipData, "title" | "isHold"> & { label: string }
): Promise<void> {
  return printCartSlip({
    ...data,
    title: "On Hold",
    heldAt: data.heldAt ?? new Date().toLocaleString(),
    isHold: true,
  });
}

export function printOrderSlip(data: Omit<CartSlipData, "title">): Promise<void> {
  return printCartSlip({
    ...data,
    title: "Order",
  });
}
