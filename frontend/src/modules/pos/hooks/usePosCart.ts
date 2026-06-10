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
}

const FAVORITES_KEY = "mda_pos_favorites";
const RECENT_KEY = "mda_pos_recent";
const HELD_KEY = "mda_pos_held";
export const POS_TAX_RATE = 0.05;

function loadJson<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}

function saveHeld(held: HeldSale[]) {
  localStorage.setItem(HELD_KEY, JSON.stringify(held));
}

function calcSubtotal(cart: CartLine[]) {
  return cart.reduce((s, i) => s + i.price * i.qty, 0);
}

function calcDiscount(subtotal: number, discountPct: number, discountAmount: number) {
  if (discountAmount > 0) return Math.min(subtotal, discountAmount);
  if (discountPct > 0) return subtotal * (discountPct / 100);
  return 0;
}

export function usePosCart() {
  const [cart, setCart] = useState<CartLine[]>([]);
  const [favorites, setFavorites] = useState<string[]>(() => loadJson(FAVORITES_KEY, []));
  const [recentSales, setRecentSales] = useState<RecentSale[]>(() => loadJson(RECENT_KEY, []));
  const [heldSales, setHeldSales] = useState<HeldSale[]>(() => loadJson<HeldSale[]>(HELD_KEY, []));
  const [discountPct, setDiscountPctState] = useState(0);
  const [discountAmount, setDiscountAmountState] = useState(0);
  const [taxRate] = useState(POS_TAX_RATE);
  const [orderNotes, setOrderNotes] = useState("");

  const subtotal = useMemo(() => calcSubtotal(cart), [cart]);

  useEffect(() => {
    localStorage.setItem(FAVORITES_KEY, JSON.stringify(favorites));
  }, [favorites]);

  useEffect(() => {
    saveHeld(heldSales);
  }, [heldSales]);

  // Keep amount in sync when cart subtotal changes but % discount is set
  useEffect(() => {
    if (discountPct > 0) {
      setDiscountAmountState(subtotal * (discountPct / 100));
    } else if (discountAmount > subtotal) {
      setDiscountAmountState(subtotal);
    }
  }, [subtotal, discountPct]);

  const setDiscountPct = useCallback(
    (pct: number) => {
      const safe = Math.min(100, Math.max(0, pct));
      setDiscountPctState(safe);
      setDiscountAmountState(subtotal * (safe / 100));
    },
    [subtotal]
  );

  const setDiscountAmount = useCallback(
    (amount: number) => {
      const safe = Math.min(subtotal, Math.max(0, amount));
      setDiscountAmountState(safe);
      setDiscountPctState(subtotal > 0 ? (safe / subtotal) * 100 : 0);
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
    setOrderNotes("");
  }, []);

  const toggleFavorite = useCallback((productId: string) => {
    setFavorites((prev) =>
      prev.includes(productId) ? prev.filter((id) => id !== productId) : [...prev, productId]
    );
  }, []);

  const holdSale = useCallback(() => {
    if (!cart.length) return null;
    const itemCount = cart.reduce((s, i) => s + i.qty, 0);
    const discount = calcDiscount(subtotal, discountPct, discountAmount);
    const held: HeldSale = {
      id: crypto.randomUUID(),
      label: cart.length === 1 ? cart[0].name : `${itemCount} items`,
      cart: [...cart],
      discountPct,
      discountAmount: discount,
      notes: orderNotes,
      heldAt: new Date().toISOString(),
      itemCount,
      subtotal,
    };
    setHeldSales((prev) => [held, ...prev]);
    clearCart();
    return held;
  }, [cart, discountPct, discountAmount, orderNotes, subtotal, clearCart]);

  const resumeHeldSale = useCallback(
    (id: string) => {
      const sale = heldSales.find((h) => h.id === id);
      if (!sale) return false;

      let nextHeld = heldSales.filter((h) => h.id !== id);

      if (cart.length) {
        const itemCount = cart.reduce((s, i) => s + i.qty, 0);
        const disc = calcDiscount(subtotal, discountPct, discountAmount);
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
      setDiscountPctState(sale.discountPct);
      setDiscountAmountState(sale.discountAmount ?? subtotal * (sale.discountPct / 100));
      setOrderNotes(sale.notes);
      return true;
    },
    [heldSales, cart, discountPct, discountAmount, orderNotes, subtotal]
  );

  const deleteHeldSale = useCallback((id: string) => {
    setHeldSales((prev) => prev.filter((h) => h.id !== id));
  }, []);

  const completeSale = useCallback(
    (method: string, total?: number, invoiceNumber?: string) => {
      if (!cart.length) return;
      const discount = calcDiscount(subtotal, discountPct, discountAmount);
      const grandTotal =
        total ?? subtotal - discount + (subtotal - discount) * taxRate;

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
    [cart, discountPct, discountAmount, subtotal, taxRate, clearCart]
  );

  const totals = useMemo(() => {
    const discount = calcDiscount(subtotal, discountPct, discountAmount);
    const afterDiscount = subtotal - discount;
    const tax = afterDiscount * taxRate;
    const grandTotal = afterDiscount + tax;
    const itemCount = cart.reduce((s, i) => s + i.qty, 0);
    return { subtotal, discount, tax, grandTotal, itemCount };
  }, [cart, discountPct, discountAmount, subtotal, taxRate]);

  return {
    cart,
    favorites,
    recentSales,
    heldSales,
    discountPct,
    setDiscountPct,
    discountAmount,
    setDiscountAmount,
    taxRate,
    orderNotes,
    setOrderNotes,
    totals,
    addToCart,
    updateQty,
    removeLine,
    clearCart,
    toggleFavorite,
    holdSale,
    resumeHeldSale,
    deleteHeldSale,
    completeSale,
  };
}
