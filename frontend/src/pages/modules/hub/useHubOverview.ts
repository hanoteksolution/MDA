import { useCallback, useEffect, useMemo, useState } from "react";
import { dashboardApi, type DashboardTransaction } from "@/services/api/dashboard";
import { salesApi } from "@/services/api/sales";
import { financeApi } from "@/services/api/finance";
import { customersApi, purchasesApi, suppliersApi } from "@/services/api/partners";
import { inventoryApi } from "@/services/api/catalog";
import { gymApi } from "@/services/api/gym";
import { pharmacyApi } from "@/services/api/pharmacy";
import { restaurantApi } from "@/services/api/restaurant";
import { hotelApi } from "@/services/api/hotel";
import { propertyApi } from "@/services/api/property";
import { housingApi } from "@/services/api/housing";
import { officeApi } from "@/services/api/office";
import { futsalApi } from "@/services/api/futsal";
import { notificationsApi, type NotificationItem } from "@/services/api/notifications";
import { platformApi, type TenantEntitlements } from "@/services/api/platform";
import type { ModuleWorkspace } from "@/navigation/moduleWorkspaces";
import { formatCurrency } from "@/utils/cn";
import { seededSeries, seriesDelta } from "./HubSparkline";

export interface HubKpi {
  id: string;
  label: string;
  value: number;
  money?: boolean;
  integer?: boolean;
  hint?: string;
  delta?: number;
  sparkline?: number[];
}

export interface WorkspaceMetric {
  label: string;
  value: string;
  alert?: boolean;
}

export type WorkspaceHealth = "live" | "healthy" | "attention" | "trial" | "setup";

export interface WorkspaceLiveState {
  metrics: WorkspaceMetric[];
  status: WorkspaceHealth;
  alertCount: number;
  alertLabel?: string;
  sparkline?: number[];
}

export interface HubActivityItem {
  id: string;
  title: string;
  detail?: string;
  at: string;
  tone?: "sale" | "alert" | "info";
}

interface HubOverviewState {
  loading: boolean;
  kpis: HubKpi[];
  live: Record<string, WorkspaceLiveState>;
  activity: HubActivityItem[];
  entitlements: TenantEntitlements | null;
  announcements: { title: string; body: string; tone: "info" | "warning" | "danger" }[];
  refresh: () => void;
}

function settled<T>(p: PromiseSettledResult<T>): T | null {
  return p.status === "fulfilled" ? p.value : null;
}

async function safe<T>(fn: () => Promise<T>): Promise<T | null> {
  try {
    return await fn();
  } catch {
    return null;
  }
}

function money(n: number | undefined | null): string {
  return formatCurrency(Number(n) || 0);
}

function num(n: number | undefined | null): string {
  return (Number(n) || 0).toLocaleString();
}

function pct(part: number, total: number): string {
  if (!total) return "0%";
  return `${Math.round((part / total) * 100)}%`;
}

function liveState(
  metrics: WorkspaceMetric[],
  alertCount = 0,
  alertLabel?: string,
  trial = false,
  sparkline?: number[]
): WorkspaceLiveState {
  let status: WorkspaceHealth = "live";
  if (trial) status = "trial";
  else if (alertCount > 0) status = "attention";
  else if (metrics.length) status = "healthy";
  return { metrics, status, alertCount, alertLabel, sparkline };
}

function metricBase(metrics: WorkspaceMetric[]): number {
  const raw = metrics[0]?.value?.replace(/[^\d.]/g, "") ?? "";
  const n = Number(raw);
  return Number.isFinite(n) && n > 0 ? n : 18;
}

export function useHubOverview(workspaces: ModuleWorkspace[], isTrial = false): HubOverviewState {
  const codes = useMemo(() => new Set(workspaces.map((w) => w.code)), [workspaces]);
  const [loading, setLoading] = useState(true);
  const [kpis, setKpis] = useState<HubKpi[]>([]);
  const [live, setLive] = useState<Record<string, WorkspaceLiveState>>({});
  const [activity, setActivity] = useState<HubActivityItem[]>([]);
  const [entitlements, setEntitlements] = useState<TenantEntitlements | null>(null);
  const [announcements, setAnnouncements] = useState<HubOverviewState["announcements"]>([]);
  const [tick, setTick] = useState(0);

  const refresh = useCallback(() => setTick((n) => n + 1), []);

  useEffect(() => {
    let active = true;
    setLoading(true);

    const run = async () => {
      const has = (code: string) => codes.has(code);
      const [
        kpisToday,
        kpisMonth,
        sales,
        finance,
        customers,
        suppliers,
        inventory,
        warehouses,
        gym,
        pharmacy,
        restaurant,
        hotel,
        property,
        housing,
        office,
        futsal,
        purchases,
        recentSales,
        notes,
        entitlementsRes,
        charts,
      ] = await Promise.allSettled([
        safe(() => dashboardApi.kpis("today")),
        safe(() => dashboardApi.kpis("month")),
        has("sales") || has("pos") ? safe(() => salesApi.summary()) : Promise.resolve(null),
        has("finance") ? safe(() => financeApi.summary("month")) : Promise.resolve(null),
        has("sales") || has("pos") ? safe(() => customersApi.summary()) : Promise.resolve(null),
        has("purchases") ? safe(() => suppliersApi.summary()) : Promise.resolve(null),
        has("inventory") ? safe(() => inventoryApi.summary()) : Promise.resolve(null),
        has("inventory") ? safe(() => inventoryApi.warehouses()) : Promise.resolve(null),
        has("gym") ? safe(() => gymApi.summary()) : Promise.resolve(null),
        has("pharmacy") ? safe(() => pharmacyApi.summary()) : Promise.resolve(null),
        has("restaurant") ? safe(() => restaurantApi.summary()) : Promise.resolve(null),
        has("hotel") ? safe(() => hotelApi.summary()) : Promise.resolve(null),
        has("property") ? safe(() => propertyApi.summary()) : Promise.resolve(null),
        has("housing") ? safe(() => housingApi.summary()) : Promise.resolve(null),
        has("office") ? safe(() => officeApi.summary()) : Promise.resolve(null),
        has("futsal") ? safe(() => futsalApi.summary()) : Promise.resolve(null),
        has("purchases") ? safe(() => purchasesApi.summary()) : Promise.resolve(null),
        safe(() => dashboardApi.recentSales()),
        safe(() => notificationsApi.list({ page_size: 12 })),
        safe(() => platformApi.entitlements()),
        safe(() => dashboardApi.charts()),
      ]);

      if (!active) return;

      const today = settled(kpisToday)?.data;
      const month = settled(kpisMonth)?.data;
      const salesData = settled(sales)?.data;
      const financeData = settled(finance)?.data;
      const customerData = settled(customers)?.data;
      const supplierData = settled(suppliers)?.data;
      const invData = settled(inventory)?.data;
      const warehousePage = settled(warehouses)?.data;
      const warehouseCount = warehousePage?.count ?? warehousePage?.results?.length ?? 0;
      const gymData = settled(gym)?.data;
      const pharmacyData = settled(pharmacy)?.data;
      const restaurantData = settled(restaurant)?.data;
      const hotelData = settled(hotel)?.data;
      const propertyData = settled(property)?.data;
      const housingData = settled(housing)?.data;
      const officeData = settled(office)?.data;
      const futsalData = settled(futsal)?.data;
      const purchaseData = settled(purchases)?.data;
      const recent = settled(recentSales)?.data?.results ?? [];
      const notifications = settled(notes)?.data?.results ?? [];
      const ents = settled(entitlementsRes)?.data ?? null;
      const chartData = settled(charts)?.data;
      const revenueSeries = (chartData?.revenue?.length ? chartData.revenue : chartData?.sales_trend ?? []).map((p) =>
        Number(p.revenue || 0)
      );
      const profitSeries = (chartData?.profit ?? []).map((p) => Number(p.profit || 0));
      const salesSeries = (chartData?.sales_trend ?? []).map((p) => Number(p.sales || p.revenue || 0));
      const hasTrend = (s?: number[]) => Boolean(s && s.length > 1 && s.some((v) => v > 0));

      const cash = financeData?.kpis?.cash_balance ?? today?.cash_collected ?? 0;
      const receivables = customerData?.credit_outstanding ?? 0;
      const payables = supplierData?.payables ?? 0;
      const pendingJournals = (financeData?.journal ?? []).filter(
        (j) => j.status && !["posted", "approved"].includes(String(j.status).toLowerCase())
      ).length;

      const revSpark = hasTrend(revenueSeries) ? revenueSeries : seededSeries("revenue", today?.revenue ?? salesData?.today_sales ?? 20);
      const profitSpark = hasTrend(profitSeries) ? profitSeries : seededSeries("profit", today?.profit ?? 16);
      const orderSpark = hasTrend(salesSeries) ? salesSeries : seededSeries("orders", salesData?.invoice_count ?? 14);
      const nextKpis: HubKpi[] = [
        {
          id: "revenue",
          label: "Revenue Today",
          value: today?.revenue ?? salesData?.today_sales ?? 0,
          money: true,
          hint: month?.revenue ? `Month ${money(month.revenue)}` : undefined,
          sparkline: revSpark,
          delta: seriesDelta(revSpark),
        },
        {
          id: "profit",
          label: "Profit",
          value: today?.profit ?? financeData?.kpis?.net_profit ?? 0,
          money: true,
          sparkline: profitSpark,
          delta: seriesDelta(profitSpark),
        },
        {
          id: "orders",
          label: "Orders",
          value: salesData?.invoice_count ?? restaurantData?.orders_today ?? 0,
          integer: true,
          sparkline: orderSpark,
          delta: seriesDelta(orderSpark),
        },
        {
          id: "customers",
          label: "Customers",
          value: customerData?.active ?? customerData?.total ?? 0,
          integer: true,
          hint: customerData?.total ? `${num(customerData.total)} total` : undefined,
          sparkline: seededSeries("customers", customerData?.total ?? 8),
        },
        {
          id: "cash",
          label: "Cash Balance",
          value: cash,
          money: true,
          sparkline: seededSeries("cash", cash || 22),
        },
        {
          id: "receivables",
          label: "Receivables",
          value: receivables,
          money: true,
          sparkline: seededSeries("ar", receivables || 18),
        },
        {
          id: "payables",
          label: "Payables",
          value: payables,
          money: true,
          sparkline: seededSeries("ap", payables || 14),
        },
      ];

      const trial = Boolean(isTrial || ents?.trial_or_demo);
      const nextLive: Record<string, WorkspaceLiveState> = {};

      if (has("pos") || has("sales")) {
        const posMetrics: WorkspaceMetric[] = [
          { label: "Today's Sales", value: money(salesData?.today_sales ?? today?.revenue) },
          { label: "Orders", value: num(salesData?.invoice_count) },
          { label: "Open invoices", value: num(salesData?.open_invoices), alert: (salesData?.open_invoices ?? 0) > 0 },
        ];
        nextLive.pos = liveState(posMetrics, salesData?.open_invoices ?? 0, salesData?.open_invoices ? `${salesData.open_invoices} open invoices` : undefined, trial);
        nextLive.sales = liveState(
          [
            { label: "Today", value: money(salesData?.today_sales) },
            { label: "All time", value: money(salesData?.all_time_sales ?? salesData?.month_sales) },
            { label: "Open", value: num(salesData?.open_invoices), alert: (salesData?.open_invoices ?? 0) > 0 },
            { label: "Quotes", value: num(salesData?.quotations_count) },
          ],
          salesData?.open_invoices ?? 0,
          salesData?.open_invoices ? `${salesData.open_invoices} unpaid` : undefined,
          trial
        );
      }

      if (has("finance")) {
        nextLive.finance = liveState(
          [
            { label: "Cash", value: money(financeData?.kpis?.cash_balance) },
            { label: "Receivables", value: money(receivables) },
            { label: "Payables", value: money(payables) },
            { label: "Pending journals", value: num(pendingJournals), alert: pendingJournals > 0 },
          ],
          pendingJournals,
          pendingJournals ? `${pendingJournals} journals awaiting approval` : undefined,
          trial
        );
      }

      if (has("inventory")) {
        const low = invData?.low_stock_count ?? 0;
        nextLive.inventory = liveState(
          [
            { label: "Products", value: num(invData?.total_items) },
            { label: "Low stock", value: num(low), alert: low > 0 },
            { label: "Warehouses", value: num(warehouseCount) },
            { label: "Value", value: money(invData?.inventory_value) },
          ],
          low,
          low ? `${low} low stock items` : undefined,
          trial
        );
      }

      if (has("purchases")) {
        const pending = purchaseData?.pending_receipt ?? 0;
        nextLive.purchases = liveState(
          [
            { label: "Open POs", value: num(purchaseData?.open_orders) },
            { label: "To receive", value: num(pending), alert: pending > 0 },
            { label: "Month total", value: money(purchaseData?.month_total) },
          ],
          pending,
          pending ? `${pending} awaiting receipt` : undefined,
          trial
        );
      }

      if (has("gym")) {
        const expiring = gymData?.subscriptions?.expired ?? 0;
        const pendingSubs = gymData?.subscriptions?.pending ?? 0;
        const alerts = expiring + pendingSubs;
        nextLive.gym = liveState(
          [
            { label: "Active members", value: num(gymData?.members?.active ?? gymData?.members?.total) },
            { label: "Today's attendance", value: num(gymData?.attendance?.today_checkins) },
            { label: "Expiring", value: num(expiring), alert: expiring > 0 },
            { label: "Active plans", value: num(gymData?.subscriptions?.active) },
          ],
          alerts,
          expiring ? `${expiring} memberships expiring` : pendingSubs ? `${pendingSubs} pending` : undefined,
          trial
        );
      }

      if (has("restaurant")) {
        const queue = restaurantData?.orders_open ?? 0;
        nextLive.restaurant = liveState(
          [
            { label: "Orders today", value: num(restaurantData?.orders_today) },
            { label: "Kitchen queue", value: num(queue), alert: queue > 0 },
            {
              label: "Tables",
              value: `${num(restaurantData?.tables_occupied)} / ${num(restaurantData?.tables)}`,
            },
          ],
          queue,
          queue ? `${queue} kitchen orders` : undefined,
          trial
        );
      }

      if (has("hotel")) {
        const arrivals = hotelData?.arrivals_today ?? 0;
        nextLive.hotel = liveState(
          [
            { label: "Occupancy", value: pct(hotelData?.rooms_occupied ?? 0, hotelData?.rooms ?? 0) },
            { label: "Arrivals", value: num(arrivals), alert: arrivals > 0 },
            { label: "Departures", value: num(hotelData?.departures_today) },
            { label: "Reservations", value: num(hotelData?.reservations_booked) },
          ],
          arrivals,
          arrivals ? `${arrivals} guests arriving` : undefined,
          trial
        );
      }

      if (has("property")) {
        const maint = propertyData?.maintenance_open ?? 0;
        nextLive.property = liveState(
          [
            { label: "Properties", value: num(propertyData?.properties) },
            { label: "Units", value: num(propertyData?.units) },
            { label: "Occupied", value: num(propertyData?.units_occupied) },
            { label: "Maintenance", value: num(maint), alert: maint > 0 },
          ],
          maint,
          maint ? `${maint} open tickets` : undefined,
          trial
        );
      }

      if (has("housing")) {
        const due = housingData?.charges_overdue ?? 0;
        nextLive.housing = liveState(
          [
            { label: "Active leases", value: num(housingData?.leases_active) },
            { label: "Occupied", value: num(housingData?.units_occupied) },
            { label: "Rent due", value: num((housingData?.charges_pending ?? 0) + due), alert: due > 0 },
            { label: "Outstanding", value: money(housingData?.rent_pending_amount) },
          ],
          due,
          due ? `${due} rent payments due` : undefined,
          trial
        );
      }

      if (has("office")) {
        const due = officeData?.charges_overdue ?? 0;
        nextLive.office = liveState(
          [
            { label: "Active leases", value: num(officeData?.leases_active) },
            { label: "Occupied", value: num(officeData?.units_occupied) },
            { label: "Rent due", value: num((officeData?.charges_pending ?? 0) + due), alert: due > 0 },
            { label: "Outstanding", value: money(officeData?.rent_pending_amount) },
          ],
          due,
          due ? `${due} rent payments due` : undefined,
          trial
        );
      }

      if (has("pharmacy")) {
        const exp = (pharmacyData?.expired_count ?? 0) + (pharmacyData?.expiring_count ?? 0);
        nextLive.pharmacy = liveState(
          [
            { label: "Batches", value: num(pharmacyData?.batch_count) },
            { label: "Expiring", value: num(pharmacyData?.expiring_count), alert: (pharmacyData?.expiring_count ?? 0) > 0 },
            { label: "Expired", value: num(pharmacyData?.expired_count), alert: (pharmacyData?.expired_count ?? 0) > 0 },
            { label: "Prescriptions", value: num(pharmacyData?.prescriptions_active) },
          ],
          exp,
          exp ? `${exp} batch alerts` : undefined,
          trial
        );
      }

      if (has("futsal")) {
        nextLive.futsal = liveState(
          [
            { label: "Bookings today", value: num(futsalData?.bookings_today) },
            { label: "Courts", value: num(futsalData?.courts) },
            { label: "Teams", value: num(futsalData?.teams) },
            { label: "Month income", value: money(futsalData?.income_month) },
          ],
          0,
          undefined,
          trial
        );
      }

      if (has("overview")) {
        nextLive.overview = liveState(
          [
            { label: "Revenue", value: money(today?.revenue) },
            { label: "Profit", value: money(today?.profit) },
            { label: "Inventory", value: money(today?.inventory_value ?? invData?.inventory_value) },
            { label: "Expenses", value: money(today?.expenses) },
          ],
          invData?.low_stock_count ?? 0,
          invData?.low_stock_count ? `${invData.low_stock_count} low stock` : undefined,
          trial
        );
      }

      if (has("reports")) {
        nextLive.reports = liveState(
          [
            { label: "Month revenue", value: money(month?.revenue) },
            { label: "Month profit", value: money(month?.profit) },
            { label: "Expenses", value: money(month?.expenses) },
          ],
          0,
          undefined,
          trial
        );
      }

      if (has("admin")) {
        nextLive.admin = liveState(
          [
            { label: "Users", value: num(ents?.users_used) },
            { label: "Branches", value: num(ents?.branches_used) },
            { label: "Plan", value: ents?.plan_name || "Active" },
          ],
          0,
          undefined,
          trial
        );
      }

      if (has("platform")) {
        nextLive.platform = liveState(
          [
            { label: "Plan", value: ents?.plan_name || "—" },
            { label: "Status", value: ents?.status || ents?.phase || "—" },
            { label: "Days left", value: ents?.days_until_expiry != null ? String(ents.days_until_expiry) : "—" },
          ],
          ents?.phase === "warning" || ents?.phase === "grace" || ents?.phase === "expired" ? 1 : 0,
          ents?.phase === "expired" ? "Subscription expired" : undefined,
          trial
        );
      }

      if (has("settings")) {
        nextLive.settings = liveState(
          [{ label: "Company", value: "Ready" }, { label: "Branches", value: num(ents?.branches_used) }],
          0,
          undefined,
          trial
        );
      }

      const saleItems: HubActivityItem[] = (recent as DashboardTransaction[]).slice(0, 6).map((s) => ({
        id: `sale-${s.id}`,
        title: `New sale completed (${money(s.amount)})`,
        detail: s.customer,
        at: s.date,
        tone: "sale",
      }));
      const noteItems: HubActivityItem[] = (notifications as NotificationItem[]).slice(0, 8).map((n) => ({
        id: n.id,
        title: n.title,
        detail: n.message,
        at: n.created_at,
        tone: n.type?.includes("low") || n.type?.includes("expir") ? "alert" : "info",
      }));
      const merged = [...noteItems, ...saleItems].sort((a, b) => {
        const da = new Date(a.at).getTime() || 0;
        const db = new Date(b.at).getTime() || 0;
        return db - da;
      });

      const nextAnnouncements: HubOverviewState["announcements"] = [];
      if (ents?.phase === "expired" || ents?.phase === "suspended") {
        nextAnnouncements.push({
          title: "Subscription attention",
          body: `${ents.plan_name || "Your plan"} is ${ents.phase}. Renew to keep all workspaces live.`,
          tone: "danger",
        });
      } else if (ents?.phase === "warning" || ents?.phase === "grace") {
        nextAnnouncements.push({
          title: "Renewal reminder",
          body: `${ents.plan_name || "Your plan"} ${ents.days_until_expiry != null ? `has ${ents.days_until_expiry} days left` : "needs attention"}.`,
          tone: "warning",
        });
      } else if (ents?.trial_or_demo) {
        nextAnnouncements.push({
          title: "Trial workspace",
          body: "You are on a trial or demo plan. Upgrade to unlock the full enterprise suite.",
          tone: "info",
        });
      } else {
        nextAnnouncements.push({
          title: "System status",
          body: "All core services are running. No scheduled downtime.",
          tone: "info",
        });
      }

      const sparkMap: Record<string, number[] | undefined> = {
        pos: hasTrend(salesSeries) ? salesSeries : undefined,
        sales: hasTrend(salesSeries) ? salesSeries : undefined,
        finance: hasTrend(profitSeries) ? profitSeries : undefined,
        overview: hasTrend(revenueSeries) ? revenueSeries : undefined,
        reports: hasTrend(revenueSeries) ? revenueSeries : undefined,
      };
      Object.keys(nextLive).forEach((code) => {
        const current = nextLive[code];
        nextLive[code] = {
          ...current,
          sparkline: sparkMap[code] ?? seededSeries(code, metricBase(current.metrics)),
        };
      });

      setKpis(nextKpis);
      setLive(nextLive);
      setActivity(merged.slice(0, 10));
      setEntitlements(ents);
      setAnnouncements(nextAnnouncements);
      setLoading(false);
    };

    void run();
    return () => {
      active = false;
    };
  }, [codes, isTrial, tick]);

  return { loading, kpis, live, activity, entitlements, announcements, refresh };
}
