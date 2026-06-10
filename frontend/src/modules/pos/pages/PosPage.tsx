import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Search, ScanBarcode, QrCode, Wifi, WifiOff, RefreshCw,
  SlidersHorizontal, ArrowUpDown, MapPin, CheckCircle2,
  ShoppingCart, ChevronDown, ChevronUp, LayoutGrid,
} from "lucide-react";
import { useSetPageMeta } from "@/contexts/PageMetaContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn, formatCurrency } from "@/utils/cn";
import { productsApi } from "@/services/api/catalog";
import { customersApi } from "@/services/api/partners";
import { useAuthStore } from "@/store/authStore";
import type { Product } from "@/types/models/catalog";
import type { Category } from "@/types/models/catalog";
import { usePosCart } from "../hooks/usePosCart";
import { PosProductCard } from "../components/PosProductCard";
import { PosCartPanel } from "../components/PosCartPanel";
import { PosBottomWidgets } from "../components/PosBottomWidgets";
import { PosCheckoutPanel } from "../components/PosCheckoutPanel";
import { PosHeldSalesPanel } from "../components/PosHeldSalesPanel";
import type { PosReceipt } from "@/services/api/pos";

export function PosPage() {
  useSetPageMeta({ title: "Point of Sale", breadcrumbs: ["Home", "POS"] });

  const user = useAuthStore((s) => s.user);
  const searchRef = useRef<HTMLInputElement>(null);

  const [search, setSearch] = useState("");
  const [categoryId, setCategoryId] = useState<string>("all");
  const [products, setProducts] = useState<Product[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [customers, setCustomers] = useState<{ id: string; name: string }[]>([]);
  const [customerId, setCustomerId] = useState("walkin");
  const [loading, setLoading] = useState(true);
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [lastSync, setLastSync] = useState(new Date());
  const [checkoutOpen, setCheckoutOpen] = useState(false);
  const [checkoutMsg, setCheckoutMsg] = useState<string | null>(null);
  const [draftsOpen, setDraftsOpen] = useState(false);
  const [widgetsCollapsed, setWidgetsCollapsed] = useState(false);

  const {
    cart, favorites, recentSales, heldSales, discountPct, setDiscountPct, discountAmount, setDiscountAmount, taxRate,
    orderNotes, setOrderNotes, totals, addToCart, updateQty, removeLine,
    clearCart, toggleFavorite, holdSale, resumeHeldSale, deleteHeldSale, completeSale,
  } = usePosCart();

  useEffect(() => {
    const load = async () => {
      try {
        const [prodRes, catRes, custRes] = await Promise.all([
          productsApi.list({ page_size: 200, is_active: "true" }),
          productsApi.categories(),
          customersApi.list({ page_size: 50, is_active: "true" }),
        ]);
        setProducts(prodRes.data.results);
        setCategories(catRes.data.results.filter((c) => c.is_active));
        setCustomers(custRes.data.results.map((c) => ({ id: c.id, name: c.full_name })));
        setLastSync(new Date());
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

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
    return products.filter((p) => {
      const matchSearch =
        !q ||
        p.name.toLowerCase().includes(q) ||
        p.sku.toLowerCase().includes(q) ||
        p.barcode?.toLowerCase().includes(q);
      const matchCat = categoryId === "all" || p.category_id === categoryId;
      return matchSearch && matchCat;
    });
  }, [products, search, categoryId]);

  const favoriteProducts = useMemo(
    () => products.filter((p) => favorites.includes(p.id)),
    [products, favorites]
  );

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
      setCheckoutMsg(`Sale ${receipt.invoice_number} completed`);
      setTimeout(() => setCheckoutMsg(null), 3000);
    },
    [completeSale]
  );

  const handleHold = useCallback(() => {
    const held = holdSale();
    if (held) {
      setCheckoutMsg(`Sale held · ${held.label}`);
      setTimeout(() => setCheckoutMsg(null), 2500);
    }
  }, [holdSale]);

  const handleResumeHeld = useCallback(
    (id: string) => {
      if (resumeHeldSale(id)) {
        setCheckoutMsg("Held sale restored to cart");
        setTimeout(() => setCheckoutMsg(null), 2500);
      }
    },
    [resumeHeldSale]
  );

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
          clearCart();
          break;
        case "F5":
          e.preventDefault();
          if (cart.length) setCheckoutOpen(true);
          break;
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [cart.length, clearCart, handleHold]);

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

  const syncLabel = useMemo(() => {
    const diff = Math.floor((Date.now() - lastSync.getTime()) / 60000);
    if (diff < 1) return "Synced just now";
    return `Synced ${diff}m ago`;
  }, [lastSync]);

  return (
    <div className="pos-shell -m-6 flex h-[calc(100vh-104px)] overflow-hidden rounded-xl border border-border/40 shadow-sm">
      {/* Left — product area (70%) */}
      <div className="relative z-[1] flex min-w-0 flex-[7] flex-col">
        {/* Top bar */}
        <div className="pos-glass relative flex shrink-0 flex-wrap items-center gap-3 border-b border-border/50 px-5 py-3">
          <div className="flex shrink-0 items-center gap-2.5 pr-2">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-primary to-emerald-600 text-primary-foreground shadow-lg shadow-primary/30">
              <ShoppingCart className="h-5 w-5" />
            </div>
            <div className="hidden sm:block">
              <p className="text-xs font-bold uppercase tracking-widest text-primary">POS Terminal</p>
              <p className="text-[11px] text-muted-foreground">{filtered.length} products</p>
            </div>
          </div>
          <div className="relative min-w-[220px] flex-1">
            <Search className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-primary/70" />
            <Input
              ref={searchRef}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search products by name, SKU or barcode..."
              className="h-11 rounded-xl border-border/60 bg-muted/30 pl-10 pr-14 shadow-inner focus-visible:ring-primary/30"
            />
            <kbd className="absolute right-3 top-1/2 hidden h-6 -translate-y-1/2 items-center rounded-md border border-border/70 bg-card px-2 text-[10px] font-medium text-muted-foreground sm:inline-flex">
              F2
            </kbd>
          </div>

          <Button variant="secondary" size="sm" className="h-11 shrink-0 gap-2 rounded-xl px-4 font-semibold shadow-sm">
            <ScanBarcode className="h-4 w-4 text-primary" />
            <span className="hidden sm:inline">Scan Barcode</span>
          </Button>
          <Button variant="secondary" size="sm" className="h-11 shrink-0 gap-2 rounded-xl px-4 font-semibold shadow-sm">
            <QrCode className="h-4 w-4 text-primary" />
            <span className="hidden sm:inline">Scan QR</span>
          </Button>

          <div className="ml-auto hidden items-center gap-2 md:flex">
            <span
              className={cn(
                "flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-semibold shadow-sm",
                isOnline
                  ? "bg-success/10 text-success ring-1 ring-success/20"
                  : "bg-destructive/10 text-destructive ring-1 ring-destructive/20"
              )}
            >
              {isOnline ? <Wifi className="h-3.5 w-3.5" /> : <WifiOff className="h-3.5 w-3.5" />}
              {isOnline ? "Online" : "Offline"}
            </span>
            <span className="flex items-center gap-1.5 rounded-full bg-muted/50 px-3 py-1.5 text-xs text-muted-foreground">
              <RefreshCw className="h-3.5 w-3.5" />
              {syncLabel}
            </span>
            {user?.branch && (
              <span className="flex items-center gap-1.5 rounded-full bg-primary/5 px-3 py-1.5 text-xs font-medium text-foreground">
                <MapPin className="h-3.5 w-3.5 text-primary" />
                {user.branch.name}
              </span>
            )}
          </div>
        </div>

        {/* Category navigation */}
        <div className="flex shrink-0 items-center gap-2 overflow-x-auto border-b border-border/50 bg-card/30 px-5 py-2.5 scrollbar-thin backdrop-blur-md">
          <button
            type="button"
            onClick={() => setCategoryId("all")}
            className={cn(
              "shrink-0 rounded-full px-4 py-2 text-sm font-semibold transition-all duration-200",
              categoryId === "all" ? "pos-category-active" : "bg-muted/40 text-muted-foreground hover:bg-muted/70 hover:text-foreground"
            )}
          >
            All Products
          </button>
          {categories.map((cat) => (
            <button
              key={cat.id}
              type="button"
              onClick={() => setCategoryId(cat.id)}
              className={cn(
                "shrink-0 rounded-full px-4 py-2 text-sm font-semibold transition-all duration-200",
                categoryId === cat.id ? "pos-category-active" : "bg-muted/40 text-muted-foreground hover:bg-muted/70 hover:text-foreground"
              )}
            >
              {cat.name}
            </button>
          ))}
          <div className="ml-auto flex shrink-0 gap-2">
            <Button variant="ghost" size="sm" className="h-9 gap-1.5 rounded-xl text-xs text-muted-foreground">
              <SlidersHorizontal className="h-3.5 w-3.5" />
              Filters
            </Button>
            <Button variant="ghost" size="sm" className="h-9 gap-1.5 rounded-xl text-xs text-muted-foreground">
              <ArrowUpDown className="h-3.5 w-3.5" />
              Sort
            </Button>
          </div>
        </div>

        {/* Product grid */}
        <div className="min-h-0 flex-1 overflow-y-auto px-5 pb-4 pt-3 scrollbar-thin">
          <div className="mb-3 flex items-center justify-between">
            <div className="flex items-center gap-2 text-sm">
              <LayoutGrid className="h-4 w-4 text-primary" />
              <span className="font-semibold text-foreground">Product Catalog</span>
              <span className="rounded-full bg-muted px-2 py-0.5 text-xs font-medium text-muted-foreground">
                {filtered.length}
              </span>
            </div>
            {totals.itemCount > 0 && (
              <span className="rounded-full bg-primary/10 px-3 py-1 text-xs font-bold text-primary">
                Cart {formatCurrency(totals.grandTotal)}
              </span>
            )}
          </div>
          {loading ? (
            <div className="grid grid-cols-3 gap-4 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6">
              {[...Array(12)].map((_, i) => (
                <div
                  key={i}
                  className="aspect-[3/4] animate-pulse rounded-2xl bg-gradient-to-b from-muted/80 to-muted/30"
                />
              ))}
            </div>
          ) : filtered.length === 0 ? (
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex flex-col items-center justify-center py-24 text-center"
            >
              <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-muted/50">
                <Search className="h-8 w-8 text-muted-foreground/50" />
              </div>
              <p className="text-base font-semibold">No products found</p>
              <p className="mt-1 text-sm text-muted-foreground">Try a different search or category</p>
            </motion.div>
          ) : (
            <motion.div
              layout
              className="grid grid-cols-3 gap-4 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6"
            >
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

        {/* Bottom widgets toggle + panel */}
        <div className="pos-glass flex shrink-0 items-center justify-between border-t border-border/50 px-5 py-1.5">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
            Quick panels
          </span>
          <Button
            variant="ghost"
            size="sm"
            className="h-7 gap-1 text-xs text-muted-foreground"
            onClick={() => setWidgetsCollapsed((v) => !v)}
          >
            {widgetsCollapsed ? (
              <>
                <ChevronUp className="h-3.5 w-3.5" /> Show
              </>
            ) : (
              <>
                <ChevronDown className="h-3.5 w-3.5" /> Hide
              </>
            )}
          </Button>
        </div>
        <AnimatePresence initial={false}>
          {!widgetsCollapsed && (
            <PosBottomWidgets
              key="pos-widgets"
              recentSales={recentSales}
              favoriteProducts={favoriteProducts}
              heldSales={heldSales}
              onAddProduct={handleAdd}
              onHoldSale={handleHold}
              onClearCart={clearCart}
              onOpenDrafts={() => setDraftsOpen(true)}
            />
          )}
        </AnimatePresence>

        <PosHeldSalesPanel
          open={draftsOpen}
          heldSales={heldSales}
          onClose={() => setDraftsOpen(false)}
          onResume={handleResumeHeld}
          onDelete={deleteHeldSale}
        />

        {/* Keyboard shortcuts bar */}
        <div className="flex shrink-0 items-center justify-between border-t border-border/70 bg-card/60 px-5 py-2 text-[10px] text-muted-foreground backdrop-blur-sm">
          <div className="flex flex-wrap gap-x-3 gap-y-0.5">
            {[
              ["F2", "Search"],
              ["F3", "Hold"],
              ["F4", "New Sale"],
              ["F5", "Checkout"],
              ["⌘K", "Quick Search"],
            ].map(([key, label]) => (
              <span key={key} className="flex items-center gap-1">
                <kbd className="rounded-md border border-border/70 bg-muted/50 px-1.5 py-0.5 font-mono text-[9px]">{key}</kbd>
                {label}
              </span>
            ))}
          </div>
          <span className="hidden sm:inline">
            {user?.username ?? "Cashier"} · POS-001
          </span>
        </div>

        {/* Checkout toast */}
        <AnimatePresence>
          {checkoutMsg && (
            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 16 }}
              className="absolute bottom-24 left-1/2 z-50 flex -translate-x-1/2 items-center gap-2 rounded-2xl border border-success/30 bg-success/15 px-5 py-3 text-sm font-semibold text-success shadow-xl backdrop-blur-md"
            >
              <CheckCircle2 className="h-4 w-4" />
              {checkoutMsg}
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Right — cart panel (30%) */}
      <div className="relative flex-[3] min-w-[300px] max-w-[420px] shrink-0">
        <PosCartPanel
          cart={cart}
          itemCount={totals.itemCount}
          subtotal={totals.subtotal}
          discount={totals.discount}
          discountPct={discountPct}
          discountAmount={discountAmount}
          onDiscountPctChange={setDiscountPct}
          onDiscountAmountChange={setDiscountAmount}
          tax={totals.tax}
          taxRate={taxRate}
          grandTotal={totals.grandTotal}
          orderNotes={orderNotes}
          onNotesChange={setOrderNotes}
          customerId={customerId}
          onCustomerChange={setCustomerId}
          customers={customers}
          onUpdateQty={updateQty}
          onRemove={removeLine}
          onOpenCheckout={() => setCheckoutOpen(true)}
        />
      </div>

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
        branchCode={user?.branch?.code ?? "BR01"}
        cashierName={user?.first_name || user?.username || "Cashier"}
        cashierRole={user?.role?.name ?? "Staff"}
        onClose={() => setCheckoutOpen(false)}
        onSaveDraft={handleHold}
        onComplete={handleCheckoutComplete}
      />
    </div>
  );
}
