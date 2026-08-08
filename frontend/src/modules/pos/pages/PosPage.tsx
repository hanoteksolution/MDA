import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import {
  Search, ScanBarcode, Wifi, WifiOff,
  SlidersHorizontal, ArrowUpDown, MapPin, CheckCircle2,
  ShoppingCart, LayoutGrid, Armchair, BedDouble,
} from "lucide-react";
import { useSetPageMeta } from "@/contexts/PageMetaContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { EmptyState } from "@/components/layout/EmptyState";
import { cn, formatCurrency } from "@/utils/cn";
import { productsApi } from "@/services/api/catalog";
import { customersApi } from "@/services/api/partners";
import { useAuthStore } from "@/store/authStore";
import type { Product } from "@/types/models/catalog";
import type { Category } from "@/types/models/catalog";
import { usePosCart, roundMoney } from "../hooks/usePosCart";
import { usePosProfile } from "../hooks/usePosProfile";
import { PosProductCard } from "../components/PosProductCard";
import { PosCartPanel } from "../components/PosCartPanel";
import { PosCheckoutPanel } from "../components/PosCheckoutPanel";
import { PosHeldSalesPanel } from "../components/PosHeldSalesPanel";
import { PosWaiterSalesPanel } from "../components/PosWaiterSalesPanel";
import { posApi, type PosProfile, type PosWaiter } from "@/services/api/pos";
import { restaurantApi, type RestaurantOrder } from "@/services/api/restaurant";
import { hotelApi, type HotelOpenFolio } from "@/services/api/hotel";
import { salesApi } from "@/services/api/sales";
import { printHeldSaleSlip } from "../receipt/printCartSlip";
import { invoiceToHeldSale } from "../utils/heldSales";
import type { PosReceipt } from "@/services/api/pos";
import { useAutoRefresh, requestDataRefresh } from "@/hooks/useAutoRefresh";

export function PosPage() {
  useSetPageMeta({ title: "Point of Sale", breadcrumbs: ["Home", "POS"] });

  const user = useAuthStore((s) => s.user);
  const searchRef = useRef<HTMLInputElement>(null);

  const [search, setSearch] = useState("");
  const [searchResults, setSearchResults] = useState<Product[] | null>(null);
  const [searchLoading, setSearchLoading] = useState(false);
  const [categoryId, setCategoryId] = useState<string>("all");
  const [products, setProducts] = useState<Product[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [customers, setCustomers] = useState<{ id: string; name: string }[]>([]);
  const [loading, setLoading] = useState(true);
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [checkoutOpen, setCheckoutOpen] = useState(false);
  const [checkoutMsg, setCheckoutMsg] = useState<string | null>(null);
  const [draftsOpen, setDraftsOpen] = useState(false);
  const [waiterSalesOpen, setWaiterSalesOpen] = useState(false);
  const [waiters, setWaiters] = useState<PosWaiter[]>([]);
  const [posProfile, setPosProfile] = useState<PosProfile | null>(null);
  const [restaurantOrderId, setRestaurantOrderId] = useState<string | null>(null);
  const [restaurantLabel, setRestaurantLabel] = useState<string | null>(null);
  const [hotelFolioId, setHotelFolioId] = useState<string | null>(null);
  const [hotelLabel, setHotelLabel] = useState<string | null>(null);
  const [floorOpen, setFloorOpen] = useState(false);
  const [floorOrders, setFloorOrders] = useState<RestaurantOrder[]>([]);
  const [floorLoading, setFloorLoading] = useState(false);
  const [roomsOpen, setRoomsOpen] = useState(false);
  const [openFolios, setOpenFolios] = useState<HotelOpenFolio[]>([]);
  const [roomsLoading, setRoomsLoading] = useState(false);
  const { showTables, showChargeToRoom } = usePosProfile(posProfile);

  const {
    cart, favorites, heldSales, discountPct, setDiscountPct, discountAmount, setDiscountAmount, discountMode, taxRate,
    orderNotes, setOrderNotes, totals, addToCart, updateQty, removeLine, replaceCart,
    clearCart, toggleFavorite, holdSale, resumeHeldSale, deleteHeldSale, replaceHeldSales, completeSale,
    sessionCustomerId: customerId,
    setSessionCustomerId: setCustomerId,
    sessionWaiterId: waiterId,
    setSessionWaiterId: setWaiterId,
    activeHoldId,
    setActiveHoldId,
  } = usePosCart();

  // A resumed hold stays on the server until checkout — hide it from the held list.
  const visibleHeldSales = useMemo(
    () => heldSales.filter((h) => h.id !== activeHoldId),
    [heldSales, activeHoldId]
  );

  const syncHoldsFromServer = useCallback(async () => {
    try {
      const res = await posApi.listHolds({ branch_id: user?.branch?.id });
      const server = (res.data || []).map(invoiceToHeldSale);
      // Keep offline holds (no server number yet) until they reach the server
      replaceHeldSales((prev) => [
        ...prev.filter((h) => !h.invoiceNumber && !server.some((s) => s.id === h.id)),
        ...server,
      ]);
    } catch {
      /* keep local cache if offline */
    }
  }, [user?.branch?.id, replaceHeldSales]);

  useEffect(() => {
    void syncHoldsFromServer();
  }, [syncHoldsFromServer]);

  useEffect(() => {
    const load = async () => {
      try {
        const [prodRes, catRes, custRes] = await Promise.all([
          productsApi.list({ page_size: 60, is_active: "true" }),
          productsApi.categories(),
          customersApi.list({ page_size: 50, is_active: "true" }),
        ]);
        setProducts(prodRes.data.results);
        setCategories(catRes.data.results.filter((c) => c.is_active));
        setCustomers(custRes.data.results.map((c) => ({ id: c.id, name: c.full_name })));
      } finally {
        setLoading(false);
      }
    };
    load();
    posApi.profile().then((res) => {
      setWaiters(res.data.waiters ?? []);
      setPosProfile(res.data);
    }).catch(() => {});
  }, []);

  const refreshCatalog = useCallback(async () => {
    try {
      const [prodRes, catRes, custRes] = await Promise.all([
        productsApi.list({ page_size: 60, is_active: "true" }),
        productsApi.categories(),
        customersApi.list({ page_size: 50, is_active: "true" }),
      ]);
      setProducts(prodRes.data.results);
      setCategories(catRes.data.results.filter((c) => c.is_active));
      setCustomers(custRes.data.results.map((c) => ({ id: c.id, name: c.full_name })));
    } catch {
      /* keep current catalog on background refresh failure */
    }
  }, []);

  useAutoRefresh(refreshCatalog, { intervalMs: 45_000 });

  useEffect(() => {
    const q = search.trim();
    if (q.length < 2) {
      setSearchResults(null);
      setSearchLoading(false);
      return;
    }
    setSearchLoading(true);
    const handle = window.setTimeout(() => {
      void productsApi
        .search(q, {
          limit: 50,
          category: categoryId === "all" ? undefined : categoryId,
        })
        .then((res) => setSearchResults(res.data ?? []))
        .catch(() => setSearchResults([]))
        .finally(() => setSearchLoading(false));
    }, 300);
    return () => window.clearTimeout(handle);
  }, [search, categoryId]);

  useEffect(() => {
    const onOnline = () => setIsOnline(true);
    const onOffline = () => setIsOnline(false);
    window.addEventListener("online", onOnline);
    window.addEventListener("offline", onOffline);
    return () => {
      window.removeEventListener("online", onOnline);
      window.removeEventListener("offline", onOffline);
    };
  }, []);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    const source = searchResults ?? products;
    if (searchResults !== null) {
      return source;
    }
    return source.filter((p) => {
      const matchSearch =
        !q ||
        p.name.toLowerCase().includes(q) ||
        p.sku.toLowerCase().includes(q) ||
        p.barcode?.toLowerCase().includes(q);
      const matchCat = categoryId === "all" || p.category_id === categoryId;
      return matchSearch && matchCat;
    });
  }, [products, search, categoryId, searchResults]);

  const handleAdd = useCallback(
    (product: Product) => {
      if (!addToCart(product)) return;
    },
    [addToCart]
  );

  const customerName = useMemo(() => {
    if (customerId === "walkin") return "Walk-in Customer";
    return customers.find((c) => c.id === customerId)?.name ?? "Customer";
  }, [customerId, customers]);

  const handleCheckoutComplete = useCallback(
    (receipt: PosReceipt) => {
      completeSale(receipt.payment_method, receipt.total_amount, receipt.invoice_number);
      setRestaurantOrderId(null);
      setRestaurantLabel(null);
      setHotelFolioId(null);
      setHotelLabel(null);
      setCheckoutMsg(`Sale ${receipt.invoice_number} completed`);
      setTimeout(() => setCheckoutMsg(null), 3000);
      requestDataRefresh();
      void refreshCatalog();
      void syncHoldsFromServer();
    },
    [completeSale, refreshCatalog, syncHoldsFromServer]
  );

  const openFloorPicker = useCallback(async () => {
    if (!user?.branch?.id) return;
    setFloorOpen(true);
    setFloorLoading(true);
    try {
      const res = await restaurantApi.orders(1, user.branch.id);
      const open = (res.data.results || []).filter((o) =>
        ["open", "sent", "ready", "served"].includes(o.status)
      );
      setFloorOrders(open);
    } catch {
      setFloorOrders([]);
    } finally {
      setFloorLoading(false);
    }
  }, [user?.branch?.id]);

  const openRoomPicker = useCallback(async () => {
    if (!user?.branch?.id) return;
    setRoomsOpen(true);
    setRoomsLoading(true);
    try {
      const res = await hotelApi.openFolios(user.branch.id);
      setOpenFolios(res.data.results || []);
    } catch {
      setOpenFolios([]);
    } finally {
      setRoomsLoading(false);
    }
  }, [user?.branch?.id]);

  const selectHotelFolio = useCallback((folio: HotelOpenFolio) => {
    setHotelFolioId(folio.folio_id);
    setHotelLabel(
      folio.room_code
        ? `Room ${folio.room_code} · ${folio.guest_name || folio.reservation_number}`
        : folio.guest_name || folio.reservation_number
    );
    setRoomsOpen(false);
    setCheckoutMsg(`Charging to ${folio.room_code || "room"}`);
    setTimeout(() => setCheckoutMsg(null), 2500);
  }, []);

  const loadRestaurantOrder = useCallback(
    async (orderId: string) => {
      try {
        const res = await restaurantApi.orderForPos(orderId);
        const payload = res.data;
        replaceCart(
          (payload.items || []).map((i) => ({
            id: i.product_id,
            name: i.name,
            sku: i.sku || "",
            price: i.unit_price,
            qty: i.quantity,
          }))
        );
        setOrderNotes(payload.notes || "");
        setRestaurantOrderId(payload.order.id);
        setRestaurantLabel(
          payload.order.table_code
            ? `Table ${payload.order.table_code} · ${payload.order.order_number}`
            : payload.order.order_number
        );
        setFloorOpen(false);
        setCheckoutMsg(`Loaded ${payload.order.order_number}`);
        setTimeout(() => setCheckoutMsg(null), 2500);
      } catch (err) {
        setCheckoutMsg(err instanceof Error ? err.message : "Could not load table order");
        setTimeout(() => setCheckoutMsg(null), 3000);
      }
    },
    [replaceCart, setOrderNotes]
  );

  const clearPosCart = useCallback(() => {
    clearCart();
    setRestaurantOrderId(null);
    setRestaurantLabel(null);
    setHotelFolioId(null);
    setHotelLabel(null);
  }, [clearCart]);

  const handleCreateCustomer = useCallback(
    async (data: { full_name: string; phone?: string }) => {
      const res = await customersApi.create({
        full_name: data.full_name,
        phone: data.phone || "",
        email: "",
        customer_type: "retail",
        credit_limit: 0,
        branch_id: user?.branch?.id,
        is_active: true,
      });
      const entry = { id: res.data.id, name: res.data.full_name };
      setCustomers((prev) => [entry, ...prev]);
      setCustomerId(entry.id);
      setCheckoutMsg(`Customer ${entry.name} added`);
      setTimeout(() => setCheckoutMsg(null), 2500);
    },
    [user?.branch?.id]
  );

  const handleCreateWaiter = useCallback(async (name: string) => {
    const profileRes = await posApi.profile();
    const profile = profileRes.data;
    const newWaiter: PosWaiter = {
      id: crypto.randomUUID(),
      name,
      is_active: true,
    };
    const waitersList = [...(profile.waiters ?? []), newWaiter];
    await posApi.saveProfile({ ...profile, waiters: waitersList });
    setWaiters(waitersList);
    setWaiterId(newWaiter.id);
    setCheckoutMsg(`Waiter ${name} added`);
    setTimeout(() => setCheckoutMsg(null), 2500);
  }, []);

  const waiterName = useMemo(
    () => waiters.find((w) => w.id === waiterId)?.name ?? "",
    [waiters, waiterId]
  );

  const handleHold = useCallback(async () => {
    if (!waiterId) {
      setCheckoutMsg("Select a waiter first");
      setTimeout(() => setCheckoutMsg(null), 2500);
      return;
    }
    if (!cart.length) return;

    const label = cart.length === 1 ? cart[0].name : `${totals.itemCount} items`;
    const snapshot = {
      label,
      cart: cart.map((l) => ({ ...l })),
      subtotal: totals.subtotal,
      discountAmount: totals.discount,
      notes: orderNotes,
      customerId,
      waiterId,
      waiterName: waiterName || undefined,
      heldAt: new Date().toISOString(),
    };

    let receiptNumber: string | undefined;
    try {
      const res = await posApi.createHold({
        customer_id: customerId !== "walkin" ? customerId : undefined,
        branch_id: user?.branch?.id,
        items: cart.map((line) => ({
          product_id: line.id,
          quantity: line.qty,
          unit_price: line.price,
        })),
        discount_pct: discountMode === "percent" ? discountPct : 0,
        discount_amount: totals.discount,
        tax_rate: taxRate,
        payment_method: "cash",
        waiter_id: waiterId,
        waiter_name: waiterName || undefined,
        notes: orderNotes,
        label,
        // Re-holding a resumed hold keeps the same receipt number
        hold_invoice_id: activeHoldId ?? undefined,
      });
      receiptNumber = res.data.number;
      clearPosCart();
      await syncHoldsFromServer();
    } catch (err) {
      // Offline / API failure — keep browser hold so the sale is not lost
      holdSale({
        customerId,
        waiterId,
        waiterName: waiterName || undefined,
      });
      setCheckoutMsg(err instanceof Error ? err.message : "Held locally (offline)");
      setTimeout(() => setCheckoutMsg(null), 3000);
    }

    const disc = snapshot.discountAmount;
    const taxAmt = roundMoney(snapshot.subtotal * taxRate);
    const total = roundMoney(Math.max(0, snapshot.subtotal - disc) + taxAmt);
    const cust =
      snapshot.customerId && snapshot.customerId !== "walkin"
        ? customers.find((c) => c.id === snapshot.customerId)?.name ?? "Customer"
        : "Walk-in Customer";
    try {
      await printHeldSaleSlip({
        label: snapshot.label,
        customerName: cust,
        waiterName: snapshot.waiterName,
        branchName: user?.branch?.name,
        branchCode: user?.branch?.code,
        branchId: user?.branch?.id,
        cart: snapshot.cart,
        subtotal: snapshot.subtotal,
        discount: disc,
        tax: taxAmt,
        taxRate,
        grandTotal: total,
        notes: snapshot.notes,
        heldAt: new Date(snapshot.heldAt).toLocaleString(),
        // Slip carries the real receipt number so reprints always match
        refNumber: receiptNumber,
      });
    } catch {
      /* print optional */
    }
    setCheckoutMsg(`On hold · ${receiptNumber || snapshot.label}`);
    setTimeout(() => setCheckoutMsg(null), 2500);
  }, [
    cart,
    totals,
    orderNotes,
    customerId,
    waiterId,
    waiterName,
    discountMode,
    discountPct,
    taxRate,
    customers,
    user?.branch,
    clearPosCart,
    holdSale,
    syncHoldsFromServer,
    activeHoldId,
  ]);

  const handleResumeHeld = useCallback(
    (id: string) => {
      if (cart.length) {
        setCheckoutMsg("Hold or clear the current cart before resuming");
        setTimeout(() => setCheckoutMsg(null), 3000);
        return;
      }
      const result = resumeHeldSale(id);
      if (result?.restored) {
        const sale = result.sale;
        if (sale.customerId) setCustomerId(sale.customerId);
        if (sale.waiterId) setWaiterId(sale.waiterId);
        // Keep the server hold linked — checkout or re-hold reuses its receipt number.
        setActiveHoldId(id);
        setDraftsOpen(false);
        setCheckoutMsg(`Resumed ${sale.label} — receipt number kept`);
        setTimeout(() => setCheckoutMsg(null), 2500);
      }
    },
    [cart.length, resumeHeldSale, setActiveHoldId, setCustomerId, setWaiterId]
  );

  const handleDeleteHeld = useCallback(
    async (id: string) => {
      try {
        await salesApi.deleteInvoice(id);
      } catch {
        /* local-only */
      }
      deleteHeldSale(id);
      await syncHoldsFromServer();
    },
    [deleteHeldSale, syncHoldsFromServer]
  );

  // /pos?resume=<invoiceId> (from the Receipts page) auto-resumes that hold.
  const [searchParams, setSearchParams] = useSearchParams();
  const resumeHandledRef = useRef<string | null>(null);
  useEffect(() => {
    const resumeId = searchParams.get("resume");
    if (!resumeId || resumeHandledRef.current === resumeId) return;

    const clearParam = () => {
      const next = new URLSearchParams(searchParams);
      next.delete("resume");
      setSearchParams(next, { replace: true });
    };

    if (resumeId === activeHoldId) {
      resumeHandledRef.current = resumeId;
      setCheckoutMsg("That held sale is already in the cart");
      setTimeout(() => setCheckoutMsg(null), 2500);
      clearParam();
      return;
    }
    const sale = heldSales.find((h) => h.id === resumeId);
    if (!sale) return; // holds still syncing from server
    resumeHandledRef.current = resumeId;
    handleResumeHeld(resumeId);
    clearParam();
  }, [searchParams, setSearchParams, heldSales, activeHoldId, handleResumeHeld]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
        if (e.key === "Escape") (e.target as HTMLElement).blur();
        return;
      }
      switch (e.key) {
        case "F2":
          e.preventDefault();
          searchRef.current?.focus();
          break;
        case "F3":
          e.preventDefault();
          handleHold();
          break;
        case "F4":
          e.preventDefault();
          clearPosCart();
          break;
        case "F5":
          e.preventDefault();
          if (cart.length) setCheckoutOpen(true);
          break;
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [cart.length, clearPosCart, handleHold]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        searchRef.current?.focus();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const hasCart = cart.length > 0;

  return (
    <div className="pos-shell flex h-full min-h-0 overflow-hidden rounded-xl border border-border/30 shadow-[0_16px_48px_hsl(var(--foreground)/0.05)] xl:rounded-2xl xl:shadow-[0_24px_80px_hsl(var(--foreground)/0.06)]">
      {/* Left — product area */}
      <div className="relative z-[1] flex min-w-0 flex-1 flex-col">
        {/* Top bar */}
        <div className="pos-glass relative flex shrink-0 flex-nowrap items-center gap-2 px-3 py-2.5 xl:gap-3 xl:px-5 xl:py-3">
          <div className="flex shrink-0 items-center gap-2.5 pr-1">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-primary via-primary to-emerald-600 text-primary-foreground shadow-[0_8px_24px_hsl(var(--primary)/0.35)] xl:h-11 xl:w-11 xl:rounded-2xl">
              <ShoppingCart className="h-4 w-4 xl:h-5 xl:w-5" strokeWidth={2.25} />
            </div>
            <div className="hidden lg:block">
              <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-primary/90 xl:text-[11px]">
                Point of Sale
              </p>
              <p className="text-xs font-medium tracking-tight text-foreground xl:text-sm">
                {searchLoading ? "Searching…" : `${filtered.length} products ready`}
              </p>
            </div>
          </div>
          <div className="relative min-w-0 flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground xl:left-4" />
            <Input
              ref={searchRef}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search name, SKU, or barcode…"
              className="h-10 rounded-xl border-border/50 bg-background/70 pl-10 pr-12 text-sm shadow-[inset_0_1px_2px_hsl(var(--foreground)/0.04)] focus-visible:ring-primary/25 xl:h-11 xl:rounded-2xl xl:pl-11 xl:pr-14"
            />
            <kbd className="absolute right-2.5 top-1/2 hidden h-6 -translate-y-1/2 items-center rounded-lg border border-border/60 bg-card/90 px-2 text-[10px] font-medium text-muted-foreground xl:inline-flex">
              F2
            </kbd>
          </div>
          {showTables ? (
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="shrink-0 gap-1.5 rounded-xl"
              onClick={() => void openFloorPicker()}
            >
              <Armchair className="h-4 w-4" />
              Pay table
            </Button>
          ) : null}
          {showChargeToRoom ? (
            <Button
              type="button"
              variant={hotelFolioId ? "default" : "outline"}
              size="sm"
              className="shrink-0 gap-1.5 rounded-xl"
              onClick={() => void openRoomPicker()}
            >
              <BedDouble className="h-4 w-4" />
              {hotelFolioId ? "Room" : "Charge room"}
            </Button>
          ) : null}

          <Button
            variant="secondary"
            size="sm"
            className="h-10 shrink-0 gap-2 rounded-xl border-border/60 bg-card/80 px-3 text-sm font-medium shadow-sm xl:h-11 xl:rounded-2xl xl:px-4"
          >
            <ScanBarcode className="h-4 w-4 text-primary" />
            <span className="hidden 2xl:inline">Scan</span>
          </Button>
          {!hasCart && (
            <>
              <Button
                variant="secondary"
                size="sm"
                className="hidden h-10 shrink-0 gap-2 rounded-xl border-border/60 bg-card/80 px-3 text-sm font-medium shadow-sm sm:inline-flex xl:h-11 xl:rounded-2xl xl:px-4"
                onClick={handleHold}
                disabled
              >
                Hold
              </Button>
              <Button
                variant="ghost"
                size="sm"
                className="h-10 shrink-0 gap-2 rounded-xl px-3 text-sm font-medium text-muted-foreground hover:text-foreground xl:h-11 xl:rounded-2xl xl:px-4"
                onClick={() => setDraftsOpen(true)}
              >
                Drafts
                {visibleHeldSales.length > 0 && (
                  <span className="rounded-full bg-primary/10 px-2 py-0.5 text-[11px] font-semibold text-primary">
                    {visibleHeldSales.length}
                  </span>
                )}
              </Button>
            </>
          )}
          {hasCart && (
            <Button
              variant="ghost"
              size="sm"
              className="h-10 shrink-0 gap-1.5 rounded-xl px-2.5 text-sm font-medium text-muted-foreground hover:text-foreground xl:h-11"
              onClick={() => setDraftsOpen(true)}
            >
              Drafts
              {visibleHeldSales.length > 0 && (
                <span className="rounded-full bg-primary/10 px-1.5 py-0.5 text-[10px] font-semibold text-primary">
                  {visibleHeldSales.length}
                </span>
              )}
            </Button>
          )}

          <div className="ml-auto hidden items-center gap-1.5 xl:flex">
            <span
              className={cn(
                "flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-medium",
                isOnline
                  ? "bg-emerald-500/10 text-emerald-700 ring-1 ring-emerald-500/15 dark:text-emerald-400"
                  : "bg-destructive/10 text-destructive ring-1 ring-destructive/15"
              )}
            >
              {isOnline ? <Wifi className="h-3.5 w-3.5" /> : <WifiOff className="h-3.5 w-3.5" />}
              {isOnline ? "Online" : "Offline"}
            </span>
            {user?.branch && (
              <span className="flex items-center gap-1.5 rounded-full bg-background/80 px-2.5 py-1 text-[11px] font-medium text-foreground ring-1 ring-border/60">
                <MapPin className="h-3.5 w-3.5 text-primary" />
                {user.branch.name}
              </span>
            )}
          </div>
        </div>

        {/* Category navigation */}
        <div className="flex shrink-0 items-center gap-1.5 overflow-x-auto border-b border-border/40 bg-background/40 px-3 py-2 scrollbar-thin backdrop-blur-md xl:gap-2 xl:px-5 xl:py-2.5">
          <button
            type="button"
            onClick={() => setCategoryId("all")}
            className={cn(
              "shrink-0 rounded-full px-3.5 py-2 text-xs font-medium transition-all duration-200 min-h-10 xl:min-h-0 xl:px-4 xl:py-2 xl:text-[13px]",
              categoryId === "all"
                ? "pos-category-active"
                : "bg-card/70 text-muted-foreground ring-1 ring-border/50 hover:bg-card hover:text-foreground"
            )}
          >
            All
          </button>
          {categories.map((cat) => (
            <button
              key={cat.id}
              type="button"
              onClick={() => setCategoryId(cat.id)}
              className={cn(
                "shrink-0 rounded-full px-3.5 py-2 text-xs font-medium transition-all duration-200 min-h-10 xl:min-h-0 xl:px-4 xl:py-2 xl:text-[13px]",
                categoryId === cat.id
                  ? "pos-category-active"
                  : "bg-card/70 text-muted-foreground ring-1 ring-border/50 hover:bg-card hover:text-foreground"
              )}
            >
              {cat.name}
            </button>
          ))}
          <div className="ml-auto hidden shrink-0 gap-1 lg:flex">
            <Button variant="ghost" size="sm" className="h-8 gap-1.5 rounded-xl px-2.5 text-[11px] text-muted-foreground">
              <SlidersHorizontal className="h-3.5 w-3.5" />
              Filters
            </Button>
            <Button variant="ghost" size="sm" className="h-8 gap-1.5 rounded-xl px-2.5 text-[11px] text-muted-foreground">
              <ArrowUpDown className="h-3.5 w-3.5" />
              Sort
            </Button>
          </div>
        </div>

        {/* Product grid */}
        <div className="min-h-0 flex-1 overflow-y-auto px-3 pb-4 pt-3 scrollbar-thin xl:px-5 xl:pb-5 xl:pt-4">
          <div className="mb-3 flex items-end justify-between xl:mb-4">
            <div>
              <div className="flex items-center gap-2">
                <LayoutGrid className="h-4 w-4 text-primary/80" />
                <span className="text-sm font-semibold tracking-tight text-foreground xl:text-base">Catalog</span>
              </div>
              <p className="mt-0.5 hidden text-xs text-muted-foreground sm:block">
                Tap a product to add it to the sale
              </p>
            </div>
            {totals.itemCount > 0 && (
              <span className="rounded-full bg-primary/10 px-3 py-1 text-xs font-semibold tabular-nums text-primary ring-1 ring-primary/15 xl:px-3.5 xl:py-1.5">
                {formatCurrency(totals.grandTotal)}
              </span>
            )}
          </div>
          {loading ? (
            <div className="pos-product-grid">
              {[...Array(12)].map((_, i) => (
                <div
                  key={i}
                  className="aspect-[4/5] animate-pulse rounded-xl bg-gradient-to-b from-muted/70 to-muted/20 ring-1 ring-border/40 xl:rounded-[1.15rem]"
                />
              ))}
            </div>
          ) : filtered.length === 0 ? (
            <EmptyState
              icon={<Search className="h-7 w-7" />}
              title="No products found"
              description="Try another search term or category"
              className="xl:py-28"
            />
          ) : (
            <motion.div layout className="pos-product-grid">
              <AnimatePresence mode="popLayout">
                {filtered.map((p, i) => (
                  <PosProductCard
                    key={p.id}
                    index={i}
                    product={p}
                    isFavorite={favorites.includes(p.id)}
                    onAdd={() => handleAdd(p)}
                    onToggleFavorite={() => toggleFavorite(p.id)}
                  />
                ))}
              </AnimatePresence>
            </motion.div>
          )}
        </div>

        <PosHeldSalesPanel
          open={draftsOpen}
          heldSales={visibleHeldSales}
          customers={customers}
          taxRate={taxRate}
          branchName={user?.branch?.name}
          branchId={user?.branch?.id}
          onClose={() => setDraftsOpen(false)}
          onResume={handleResumeHeld}
          onDelete={handleDeleteHeld}
        />

        <PosWaiterSalesPanel
          open={waiterSalesOpen}
          waiterId={waiterId}
          waiterName={waiterName}
          branchId={user?.branch?.id}
          onClose={() => setWaiterSalesOpen(false)}
        />

        {/* Checkout toast */}
        <AnimatePresence>
          {checkoutMsg && (
            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 16 }}
              className="absolute bottom-8 left-1/2 z-50 flex -translate-x-1/2 items-center gap-2 rounded-2xl border border-emerald-500/20 bg-emerald-500/10 px-5 py-3 text-sm font-medium text-emerald-700 shadow-[0_12px_40px_hsl(var(--foreground)/0.12)] backdrop-blur-xl dark:text-emerald-400"
            >
              <CheckCircle2 className="h-4 w-4" />
              {checkoutMsg}
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Right — cart panel (opens once an item is selected) */}
      <AnimatePresence initial={false}>
        {hasCart && (
          <motion.div
            key="pos-cart"
            initial={{ opacity: 0, x: 28 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 28 }}
            transition={{ duration: 0.28, ease: [0.22, 1, 0.36, 1] }}
            className="relative flex h-full min-h-0 w-[min(100%,280px)] shrink-0 flex-col overflow-hidden xl:w-[min(100%,320px)] 2xl:w-[min(100%,380px)]"
          >
          <PosCartPanel
            cart={cart}
            itemCount={totals.itemCount}
            subtotal={totals.subtotal}
            discount={totals.discount}
            discountPct={discountPct}
            discountAmount={discountAmount}
            discountMode={discountMode}
            onDiscountPctChange={setDiscountPct}
            onDiscountAmountChange={setDiscountAmount}
            tax={totals.tax}
            taxRate={taxRate}
            grandTotal={totals.grandTotal}
            orderNotes={orderNotes}
            onNotesChange={setOrderNotes}
            customerId={customerId}
            customerName={customerName}
            onCustomerChange={setCustomerId}
            customers={customers}
            waiters={waiters}
            waiterId={waiterId}
            onWaiterChange={setWaiterId}
            branchName={user?.branch?.name}
            branchCode={user?.branch?.code}
            branchId={user?.branch?.id}
            onCreateCustomer={handleCreateCustomer}
            onCreateWaiter={handleCreateWaiter}
            onUpdateQty={updateQty}
            onRemove={removeLine}
            onOpenCheckout={() => setCheckoutOpen(true)}
            onHold={handleHold}
            onViewWaiterSales={() => setWaiterSalesOpen(true)}
            restaurantLabel={restaurantLabel}
            hotelLabel={hotelLabel}
          />
          </motion.div>
        )}
      </AnimatePresence>

      <PosCheckoutPanel
        open={checkoutOpen}
        cart={cart}
        itemCount={totals.itemCount}
        customerId={customerId}
        customerName={customerName}
        subtotal={totals.subtotal}
        discount={totals.discount}
        discountPct={discountPct}
        tax={totals.tax}
        taxRate={taxRate}
        grandTotal={totals.grandTotal}
        orderNotes={orderNotes}
        branchId={user?.branch?.id}
        branchName={user?.branch?.name ?? "Main Branch"}
        branchCode={user?.branch?.code}
        waiterId={waiterId}
        waiterName={waiterName}
        waiters={waiters}
        holdInvoiceId={activeHoldId ?? undefined}
        restaurantOrderId={restaurantOrderId ?? undefined}
        restaurantLabel={restaurantLabel ?? undefined}
        hotelFolioId={hotelFolioId ?? undefined}
        hotelLabel={hotelLabel ?? undefined}
        onClose={() => setCheckoutOpen(false)}
        onSaveDraft={handleHold}
        onComplete={handleCheckoutComplete}
      />

      {floorOpen ? (
        <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 p-4 sm:items-center">
          <div className="w-full max-w-md rounded-2xl border border-border bg-card p-4 shadow-xl">
            <div className="mb-3 flex items-center justify-between">
              <h3 className="text-sm font-semibold">Open table orders</h3>
              <Button size="sm" variant="ghost" onClick={() => setFloorOpen(false)}>
                Close
              </Button>
            </div>
            {floorLoading ? (
              <p className="py-6 text-center text-sm text-muted-foreground">Loading…</p>
            ) : floorOrders.length === 0 ? (
              <p className="py-6 text-center text-sm text-muted-foreground">No open floor tickets.</p>
            ) : (
              <ul className="max-h-72 space-y-2 overflow-y-auto">
                {floorOrders.map((o) => (
                  <li key={o.id}>
                    <button
                      type="button"
                      className="flex w-full items-center justify-between rounded-xl border border-border px-3 py-2.5 text-left text-sm hover:bg-muted/50"
                      onClick={() => void loadRestaurantOrder(o.id)}
                    >
                      <span>
                        <span className="font-medium">{o.order_number}</span>
                        <span className="ml-2 text-muted-foreground">
                          {o.table_code || "Takeaway"} · {o.status}
                        </span>
                      </span>
                      <span className="tabular-nums">{formatCurrency(o.subtotal)}</span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      ) : null}

      {roomsOpen ? (
        <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 p-4 sm:items-center">
          <div className="w-full max-w-md rounded-2xl border border-border bg-card p-4 shadow-xl">
            <div className="mb-3 flex items-center justify-between">
              <h3 className="text-sm font-semibold">Charge to room</h3>
              <Button size="sm" variant="ghost" onClick={() => setRoomsOpen(false)}>
                Close
              </Button>
            </div>
            {hotelFolioId ? (
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="mb-3 w-full"
                onClick={() => {
                  setHotelFolioId(null);
                  setHotelLabel(null);
                }}
              >
                Clear room charge
              </Button>
            ) : null}
            {roomsLoading ? (
              <p className="py-6 text-center text-sm text-muted-foreground">Loading…</p>
            ) : openFolios.length === 0 ? (
              <p className="py-6 text-center text-sm text-muted-foreground">
                No in-house guests with open folios.
              </p>
            ) : (
              <ul className="max-h-72 space-y-2 overflow-y-auto">
                {openFolios.map((f) => (
                  <li key={f.folio_id}>
                    <button
                      type="button"
                      className={cn(
                        "flex w-full items-center justify-between rounded-xl border px-3 py-2.5 text-left text-sm hover:bg-muted/50",
                        hotelFolioId === f.folio_id
                          ? "border-primary bg-primary/5"
                          : "border-border"
                      )}
                      onClick={() => selectHotelFolio(f)}
                    >
                      <span>
                        <span className="font-medium">Room {f.room_code || "—"}</span>
                        <span className="ml-2 text-muted-foreground">
                          {f.guest_name || f.reservation_number}
                        </span>
                      </span>
                      <span className="tabular-nums text-muted-foreground">
                        {formatCurrency(f.balance)}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}
