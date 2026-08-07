import type { Invoice } from "@/services/api/sales";
import type { HeldSale, CartLine } from "@/modules/pos/hooks/usePosCart";
import { roundMoney } from "@/modules/pos/hooks/usePosCart";

export function parseHoldLabel(notes?: string | null): string {
  if (!notes) return "";
  const match = notes.match(/HoldLabel:\s*([^|\n]+)/i);
  return match?.[1]?.trim() || "";
}

export function invoiceToHeldSale(inv: Invoice): HeldSale {
  const cart: CartLine[] = (inv.items || []).map((item) => ({
    id: item.product_id,
    name: item.product_name || "Item",
    sku: item.product_sku || "",
    price: item.unit_price,
    qty: item.quantity,
  }));
  const itemCount = cart.reduce((s, i) => s + i.qty, 0) || inv.item_count || 0;
  const discount = inv.discount_amount || 0;
  const subtotal = inv.subtotal || cart.reduce((s, i) => s + i.price * i.qty, 0);
  return {
    id: inv.id,
    invoiceNumber: inv.number,
    label: parseHoldLabel(inv.notes) || (cart.length === 1 ? cart[0].name : inv.number),
    cart,
    discountPct: subtotal > 0 ? roundMoney((discount / subtotal) * 100) : 0,
    discountAmount: discount,
    notes: (inv.notes || "")
      .split("\n")
      .filter((line) => !/^\s*Payment:/i.test(line) && !/HoldLabel:/i.test(line))
      .join("\n")
      .trim(),
    heldAt: inv.created_at || inv.issue_date,
    itemCount,
    subtotal,
    customerId: inv.customer_id,
    waiterId: inv.served_by_user_id || undefined,
    waiterName: inv.waiter_name || undefined,
  };
}
