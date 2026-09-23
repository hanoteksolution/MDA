import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Coffee,
  PackagePlus,
  Plus,
  Receipt,
  ShoppingCart,
  Store,
  Users,
  Warehouse,
} from "lucide-react";
import { PageLayout } from "@/components/layout/PageLayout";
import { KpiCard, KpiGrid } from "@/components/data/KpiCard";
import { ContentSection } from "@/components/layout/ContentSection";
import { Button } from "@/components/ui/button";
import { useAuthStore } from "@/store/authStore";
import { useScopedPath } from "@/hooks/useScopedPath";
import {
  restaurantApi,
  type CafeteriaProfile,
  type RestaurantOrder,
  type RestaurantSummary,
} from "@/services/api/restaurant";
import { formatCurrency } from "@/utils/cn";

const QUICK_ACTIONS = [
  { label: "New Sale", to: "/cafeteria/pos", icon: Store },
  { label: "New Order", to: "/cafeteria/orders", icon: ShoppingCart },
  { label: "Add Menu Item", to: "/cafeteria/menu/items/new", icon: PackagePlus },
  { label: "Add Ingredient", to: "/cafeteria/ingredients/new", icon: Coffee },
  { label: "Purchase Order", to: "/cafeteria/purchasing", icon: Receipt },
  { label: "Receive Stock", to: "/cafeteria/inventory", icon: Warehouse },
  { label: "Stock Adjustment", to: "/cafeteria/inventory", icon: Warehouse },
  { label: "Add Customer", to: "/cafeteria/customers", icon: Users },
  { label: "Add Expense", to: "/cafeteria/finance", icon: Receipt },
  { label: "Open Shift", to: "/cafeteria/pos", icon: Store },
  { label: "Barista Queue", to: "/cafeteria/barista", icon: Coffee },
  { label: "Settings", to: "/cafeteria/settings", icon: Plus },
] as const;

export function CafeteriaDashboardPage() {
  const { scoped } = useScopedPath();
  const branchId = useAuthStore((s) => s.user?.branch?.id);
  const [summary, setSummary] = useState<RestaurantSummary | null>(null);
  const [profile, setProfile] = useState<CafeteriaProfile | null>(null);
  const [orders, setOrders] = useState<RestaurantOrder[]>([]);
  const [loading, setLoading] = useState(true);

  const reload = useCallback(async () => {
    if (!branchId) return;
    setLoading(true);
    try {
      const [sumRes, orderRes, profileRes] = await Promise.all([
        restaurantApi.summary(branchId),
        restaurantApi.orders(1, branchId),
        restaurantApi.cafeteriaProfile(branchId).catch(() => ({ data: null })),
      ]);
      setSummary(sumRes.data);
      setOrders(orderRes.data.results.slice(0, 8));
      setProfile(profileRes.data);
    } finally {
      setLoading(false);
    }
  }, [branchId]);

  useEffect(() => {
    void reload();
  }, [reload]);

  const brand = profile?.business_name || profile?.trading_name || "Cafeteria";

  return (
    <PageLayout
      title={brand}
      description="Café & barista operations — sales, queue, menu, and inventory."
      actions={
        <div className="flex gap-2">
          <Button asChild variant="outline">
            <Link to={scoped("/cafeteria/barista")}>Barista Queue</Link>
          </Button>
          <Button asChild>
            <Link to={scoped("/cafeteria/pos")}>Open POS</Link>
          </Button>
        </div>
      }
    >
      <KpiGrid>
        <KpiCard title="Today's Sales" value={formatCurrency(summary?.todays_sales ?? 0)} loading={loading} accent="warning" />
        <KpiCard title="Today's Orders" value={String(summary?.orders_today ?? 0)} loading={loading} />
        <KpiCard
          title="Avg Order Value"
          value={formatCurrency(summary?.average_order_value ?? 0)}
          loading={loading}
        />
        <KpiCard title="Open Orders" value={String(summary?.orders_open ?? 0)} loading={loading} />
        <KpiCard title="Preparing" value={String(summary?.orders_preparing ?? 0)} loading={loading} accent="info" />
        <KpiCard title="Ready" value={String(summary?.orders_ready ?? 0)} loading={loading} accent="success" />
        <KpiCard title="Menu Items" value={String(summary?.menu_items ?? 0)} loading={loading} />
        <KpiCard
          title="Tables Occupied"
          value={`${summary?.tables_occupied ?? 0}/${summary?.tables ?? 0}`}
          loading={loading}
        />
      </KpiGrid>

      <ContentSection title="Quick actions" description="Operational shortcuts for the café floor.">
        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {QUICK_ACTIONS.map((action) => {
            const Icon = action.icon;
            return (
              <Button key={action.label} asChild variant="outline" className="justify-start h-11">
                <Link to={scoped(action.to)}>
                  <Icon className="mr-2 h-4 w-4 text-amber-700" />
                  {action.label}
                </Link>
              </Button>
            );
          })}
        </div>
      </ContentSection>

      <ContentSection title="Recent orders" description="Latest floor and counter tickets.">
        <div className="divide-y rounded-lg border border-border/60">
          {orders.length === 0 && !loading ? (
            <p className="p-4 text-sm text-muted-foreground">No orders yet. Open POS to start selling.</p>
          ) : (
            orders.map((o) => (
              <div key={o.id} className="flex items-center justify-between gap-3 px-4 py-3">
                <div>
                  <p className="font-medium">{o.order_number}</p>
                  <p className="text-xs text-muted-foreground">
                    {o.service_type} · {o.waiter_name || "—"} · {o.status}
                  </p>
                </div>
                <div className="text-right">
                  <p className="font-medium">{formatCurrency(o.subtotal)}</p>
                  <Link className="text-xs text-amber-800 hover:underline" to={scoped(`/cafeteria/barista`)}>
                    Queue
                  </Link>
                </div>
              </div>
            ))
          )}
        </div>
      </ContentSection>
    </PageLayout>
  );
}
