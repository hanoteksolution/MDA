import { useCallback, useEffect, useMemo, useState } from "react";
import type { Product } from "@/types/models/catalog";

export interface CartLine {
  id: string;
  name: string;
  sku: string;
  price: number;
  qty: number;
  image?: string;
  maxStock?: number;
}

export interface RecentSale {
  id: string;
  name: string;
  total: number;
  at: string;
}

export interface HeldSale {
  id: string;
  label: string;
  cart: CartLine[];
  discountPct: number;
  discountAmount: number;
  notes: string;
  heldAt: string;
  itemCount: number;
  subtotal: number;
  customerId?: string;
  waiterId?: string;
  waiterName?: string;
  /** Server receipt number (e.g. INV-BR01-00055) — used on every reprint. */
  invoiceNumber?: string;
}

const FAVORITES_KEY = "mda_pos_favorites";
const RECENT_KEY = "mda_pos_recent";
const HELD_KEY = "mda_pos_held";
const ACTIVE_CART_KEY = "mda_pos_active_cart";
export const POS_TAX_RATE = 0.05;

/** Which discount field the cashier last edited — prevents % and $ from fighting. */
export type DiscountMode = "none" | "percent" | "amount";

type ActiveCartSession = {
  cart: CartLine[];
  discountPct: number;
  discountAmount: number;
  discountMode: DiscountMode;
  orderNotes: string;
  customerId?: string;
  waiterId?: string;
  /** Server invoice id of the resumed hold — keeps its receipt number on checkout/re-hold. */
  holdInvoiceId?: string;
};

function loadJson<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}

function loadActiveCart(): ActiveCartSession {
  const empty: ActiveCartSession = {
    cart: [],
    discountPct: 0,
    discountAmount: 0,
    discountMode: "none",
    orderNotes: "",
  };
  try {
    const raw = localStorage.getItem(ACTIVE_CART_KEY);
    if (!raw) return empty;
    const parsed = JSON.parse(raw) as Partial<ActiveCartSession>;
    const cart = Array.isArray(parsed.cart) ? parsed.cart.filter((l) => l?.id && l.qty > 0) : [];
    const mode =
      parsed.discountMode === "percent" || parsed.discountMode === "amount" || parsed.discountMode === "none"
        ? parsed.discountMode
        : "none";
    return {
      cart,
      discountPct: Number(parsed.discountPct) || 0,
      discountAmount: Number(parsed.discountAmount) || 0,
      discountMode: mode,
      orderNotes: typeof parsed.orderNotes === "string" ? parsed.orderNotes : "",
      customerId: typeof parsed.customerId === "string" ? parsed.customerId : undefined,
      waiterId: typeof parsed.waiterId === "string" ? parsed.waiterId : undefined,
      holdInvoiceId: typeof parsed.holdInvoiceId === "string" ? parsed.holdInvoiceId : undefined,
    };
  } catch {
    return empty;
  }
}

function saveActiveCart(session: ActiveCartSession) {
  localStorage.setItem(ACTIVE_CART_KEY, JSON.stringify(session));
}

function clearActiveCartStorage() {
  localStorage.removeItem(ACTIVE_CART_KEY);
}

function saveHeld(held: HeldSale[]) {
  localStorage.setItem(HELD_KEY, JSON.stringify(held));
}

function calcSubtotal(cart: CartLine[]) {
  return cart.reduce((s, i) => s + i.price * i.qty, 0);
}

export function roundMoney(n: number) {
  return Math.round((n + Number.EPSILON) * 100) / 100;
}

function calcDiscount(
  subtotal: number,
  mode: DiscountMode,
  discountPct: number,
  discountAmount: number
) {
  if (subtotal <= 0) return 0;
  if (mode === "percent" && discountPct > 0) {
    return roundMoney(Math.min(subtotal, (subtotal * discountPct) / 100));
  }
  if (mode === "amount" && discountAmount > 0) {
    return roundMoney(Math.min(subtotal, discountAmount));
  }
  // Legacy held sales / resume without an explicit mode
  if (discountAmount > 0) return roundMoney(Math.min(subtotal, discountAmount));
  if (discountPct > 0) return roundMoney(Math.min(subtotal, (subtotal * discountPct) / 100));
  return 0;
}

export function usePosCart() {
  const restored = useMemo(() => loadActiveCart(), []);
  const [cart, setCart] = useState<CartLine[]>(() => restored.cart);
  const [favorites, setFavorites] = useState<string[]>(() => loadJson(FAVORITES_KEY, []));
  const [recentSales, setRecentSales] = useState<RecentSale[]>(() => loadJson(RECENT_KEY, []));
  const [heldSales, setHeldSales] = useState<HeldSale[]>(() => loadJson<HeldSale[]>(HELD_KEY, []));
  const [discountPct, setDiscountPctState] = useState(() => restored.discountPct);
  const [discountAmount, setDiscountAmountState] = useState(() => restored.discountAmount);
  const [discountMode, setDiscountMode] = useState<DiscountMode>(() => restored.discountMode);
  const [taxRate] = useState(POS_TAX_RATE);
  const [orderNotes, setOrderNotes] = useState(() => restored.orderNotes);
  const [sessionCustomerId, setSessionCustomerId] = useState(() => restored.customerId || "walkin");
  const [sessionWaiterId, setSessionWaiterId] = useState(() => restored.waiterId || "");
  const [activeHoldId, setActiveHoldId] = useState<string | null>(() => restored.holdInvoiceId || null);

  const subtotal = useMemo(() => calcSubtotal(cart), [cart]);

  useEffect(() => {
    localStorage.setItem(FAVORITES_KEY, JSON.stringify(favorites));
  }, [favorites]);

  useEffect(() => {
    saveHeld(heldSales);
  }, [heldSales]);

  // Persist active cart so refresh does not wipe in-progress sales
  useEffect(() => {
    if (!cart.length && discountMode === "none" && !orderNotes.trim() && sessionCustomerId === "walkin" && !sessionWaiterId) {
      clearActiveCartStorage();
      return;
    }
    saveActiveCart({
      cart,
      discountPct,
      discountAmount,
      discountMode,
      orderNotes,
      customerId: sessionCustomerId,
      waiterId: sessionWaiterId || undefined,
      holdInvoiceId: activeHoldId || undefined,
    });
  }, [cart, discountPct, discountAmount, discountMode, orderNotes, sessionCustomerId, sessionWaiterId, activeHoldId]);

  // When the cart total changes, keep the active discount source and refresh the other field.
  useEffect(() => {
    if (discountMode === "percent" && discountPct > 0) {
      setDiscountAmountState(roundMoney((subtotal * discountPct) / 100));
    } else if (discountMode === "amount" && discountAmount > 0) {
      const capped = Math.min(subtotal, discountAmount);
      setDiscountAmountState(capped);
      setDiscountPctState(subtotal > 0 ? roundMoney((capped / subtotal) * 100) : 0);
    } else if (discountAmount > subtotal) {
      setDiscountAmountState(subtotal);
    }
  }, [subtotal]); // intentionally only when subtotal changes

  const setDiscountPct = useCallback(
    (pct: number) => {
      const safe = Math.min(100, Math.max(0, pct));
      if (safe <= 0) {
        setDiscountMode("none");
        setDiscountPctState(0);
        setDiscountAmountState(0);
        return;
      }
      setDiscountMode("percent");
      setDiscountPctState(safe);
      setDiscountAmountState(roundMoney((subtotal * safe) / 100));
    },
    [subtotal]
  );

  const setDiscountAmount = useCallback(
    (amount: number) => {
      const safe = roundMoney(Math.min(subtotal, Math.max(0, amount)));
      if (safe <= 0) {
        setDiscountMode("none");
        setDiscountPctState(0);
        setDiscountAmountState(0);
        return;
      }
      setDiscountMode("amount");
      setDiscountAmountState(safe);
      setDiscountPctState(subtotal > 0 ? roundMoney((safe / subtotal) * 100) : 0);
    },
    [subtotal]
  );

  const addToCart = useCallback((product: Product) => {
    const stock = product.total_stock ?? 0;
    if (stock <= 0) return false;
    setCart((prev) => {
      const existing = prev.find((i) => i.id === product.id);
      if (existing) {
        return prev.map((i) =>
          i.id === product.id ? { ...i, qty: Math.min(i.qty + 1, stock) } : i
        );
      }
      return [
        ...prev,
        {
          id: product.id,
          name: product.name,
          sku: product.sku,
          price: product.selling_price,
          qty: 1,
          image: product.image,
          maxStock: stock,
        },
      ];
    });
    return true;
  }, []);

  const updateQty = useCallback((id: string, delta: number) => {
    setCart((prev) =>
      prev
        .map((i) => {
          if (i.id !== id) return i;
          const max = i.maxStock ?? Infinity;
          return { ...i, qty: Math.min(Math.max(0, i.qty + delta), max) };
        })
        .filter((i) => i.qty > 0)
    );
  }, []);

  const removeLine = useCallback((id: string) => {
    setCart((prev) => prev.filter((i) => i.id !== id));
  }, []);

  const clearCart = useCallback(() => {
    setCart([]);
    setDiscountPctState(0);
    setDiscountAmountState(0);
    setDiscountMode("none");
    setOrderNotes("");
    setActiveHoldId(null);
    clearActiveCartStorage();
  }, []);

  const toggleFavorite = useCallback((productId: string) => {
    setFavorites((prev) =>
      prev.includes(productId) ? prev.filter((id) => id !== productId) : [...prev, productId]
    );
  }, []);

  const holdSale = useCallback(
    (extras?: { customerId?: string; waiterId?: string; waiterName?: string }) => {
      if (!cart.length) return null;
      const itemCount = cart.reduce((s, i) => s + i.qty, 0);
      const discount = calcDiscount(subtotal, discountMode, discountPct, discountAmount);
      const held: HeldSale = {
        id: crypto.randomUUID(),
        label: cart.length === 1 ? cart[0].name : `${itemCount} items`,
        cart: [...cart],
        discountPct: discountMode === "percent" ? discountPct : subtotal > 0 ? roundMoney((discount / subtotal) * 100) : 0,
        discountAmount: discount,
        notes: orderNotes,
        heldAt: new Date().toISOString(),
        itemCount,
        subtotal,
        customerId: extras?.customerId,
        waiterId: extras?.waiterId,
        waiterName: extras?.waiterName,
      };
      setHeldSales((prev) => [held, ...prev]);
      clearCart();
      return held;
    },
    [cart, discountMode, discountPct, discountAmount, orderNotes, subtotal, clearCart]
  );

  const resumeHeldSale = useCallback(
    (id: string) => {
      const sale = heldSales.find((h) => h.id === id);
      if (!sale) return null;

      let nextHeld = heldSales.filter((h) => h.id !== id);

      if (cart.length) {
        const itemCount = cart.reduce((s, i) => s + i.qty, 0);
        const disc = calcDiscount(subtotal, discountMode, discountPct, discountAmount);
        nextHeld = [
          {
            id: crypto.randomUUID(),
            label: cart.length === 1 ? cart[0].name : `${itemCount} items`,
            cart: [...cart],
            discountPct,
            discountAmount: disc,
            notes: orderNotes,
            heldAt: new Date().toISOString(),
            itemCount,
            subtotal,
          },
          ...nextHeld,
        ];
      }

      setHeldSales(nextHeld);
      setCart(sale.cart);
      const saleSub = calcSubtotal(sale.cart);
      const restoredAmount = roundMoney(sale.discountAmount ?? 0);
      const restoredPct = sale.discountPct ?? 0;
      // Prefer fixed amount when resume data stores the applied $ discount.
      if (restoredAmount > 0 && (restoredPct <= 0 || Math.abs(saleSub * (restoredPct / 100) - restoredAmount) > 0.02)) {
        setDiscountMode("amount");
        setDiscountAmountState(restoredAmount);
        setDiscountPctState(saleSub > 0 ? roundMoney((restoredAmount / saleSub) * 100) : 0);
      } else if (restoredPct > 0) {
        setDiscountMode("percent");
        setDiscountPctState(restoredPct);
        setDiscountAmountState(roundMoney((saleSub * restoredPct) / 100));
      } else {
        setDiscountMode("none");
        setDiscountPctState(0);
        setDiscountAmountState(0);
      }
      setOrderNotes(sale.notes);
      return { sale, restored: true };
    },
    [heldSales, cart, discountMode, discountPct, discountAmount, orderNotes, subtotal]
  );

  const deleteHeldSale = useCallback((id: string) => {
    setHeldSales((prev) => prev.filter((h) => h.id !== id));
  }, []);

  const replaceHeldSales = useCallback(
    (next: HeldSale[] | ((prev: HeldSale[]) => HeldSale[])) => {
      setHeldSales(next);
    },
    []
  );

  const completeSale = useCallback(
    (method: string, total?: number, invoiceNumber?: string) => {
      if (!cart.length) return;
      const discount = calcDiscount(subtotal, discountMode, discountPct, discountAmount);
      const tax = roundMoney(subtotal * taxRate);
      const grandTotal =
        total ?? roundMoney(Math.max(0, subtotal - discount) + tax);

      const sale: RecentSale = {
        id: invoiceNumber ?? crypto.randomUUID(),
        name: invoiceNumber
          ? `${invoiceNumber} · ${method}`
          : cart.length === 1
            ? cart[0].name
            : `${cart.length} items · ${method}`,
        total: grandTotal,
        at: new Date().toISOString(),
      };
      setRecentSales((prev) => {
        const next = [sale, ...prev].slice(0, 8);
        localStorage.setItem(RECENT_KEY, JSON.stringify(next));
        return next;
      });
      clearCart();
    },
    [cart, discountMode, discountPct, discountAmount, subtotal, taxRate, clearCart]
  );

  const totals = useMemo(() => {
    const discount = calcDiscount(subtotal, discountMode, discountPct, discountAmount);
    // VAT is charged on the full item subtotal (before discount), so offline
    // cashiers can waive tax by entering that VAT amount as a $ discount and get
    // a clean total equal to the pre-tax subtotal.
    const tax = roundMoney(subtotal * taxRate);
    const afterDiscount = Math.max(0, roundMoney(subtotal - discount));
    const grandTotal = roundMoney(afterDiscount + tax);
    const itemCount = cart.reduce((s, i) => s + i.qty, 0);
    return { subtotal, discount, tax, grandTotal, itemCount };
  }, [cart, discountMode, discountPct, discountAmount, subtotal, taxRate]);

  return {
    cart,
    favorites,
    recentSales,
    heldSales,
    discountPct,
    setDiscountPct,
    discountAmount,
    setDiscountAmount,
    discountMode,
    taxRate,
    orderNotes,
    setOrderNotes,
    sessionCustomerId,
    setSessionCustomerId,
    sessionWaiterId,
    setSessionWaiterId,
    activeHoldId,
    setActiveHoldId,
    totals,
    addToCart,
    updateQty,
    removeLine,
    clearCart,
    toggleFavorite,
    holdSale,
    resumeHeldSale,
    deleteHeldSale,
    replaceHeldSales,
    completeSale,
  };
}
