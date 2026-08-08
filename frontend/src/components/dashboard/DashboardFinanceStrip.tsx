import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, Scale, TrendingDown, TrendingUp, Wallet } from "lucide-react";
import { ContentSection } from "@/components/layout/ContentSection";
import { KpiCard, KpiGrid } from "@/components/data/KpiCard";
import { Badge } from "@/components/ui/badge";
import { usePermissions } from "@/hooks/usePermissions";
import { financeApi, type FinanceSummary } from "@/services/api/finance";
import { formatCurrency } from "@/utils/cn";

/**
 * Cross-module finance KPIs on the main dashboard (PHASE 08 follow-on).
 * Gated by finance.view — not BusinessType. Prefers ledger cash when has_ledger.
 */
export function DashboardFinanceStrip({ period = "month" }: { period?: string }) {
  const { hasPermission, isSuperAdmin } = usePermissions();
  const canView = isSuperAdmin || hasPermission("finance.view");
  const [summary, setSummary] = useState<FinanceSummary | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!canView) return;
    let alive = true;
    setLoading(true);
    financeApi
      .summary(period)
      .then((res) => {
        if (alive) setSummary(res.data);
      })
      .catch(() => {
        if (alive) setSummary(null);
      })
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [canView, period]);

  if (!canView) return null;

  const kpis = summary?.kpis;
  const fromLedger = Boolean(summary?.has_ledger);

  return (
    <ContentSection
      index={0}
      title="Finance overview"
      description={
        fromLedger
          ? "Ledger-backed KPIs for the selected period"
          : "Operational finance KPIs for the selected period"
      }
      action={
        <Link
          to="/finance"
          className="inline-flex items-center gap-1 text-sm font-medium text-primary hover:underline"
        >
          Open finance
          <ArrowRight className="h-4 w-4" />
        </Link>
      }
    >
      <div className="mb-3 flex flex-wrap items-center gap-2">
        {fromLedger ? (
          <Badge variant="success">Ledger</Badge>
        ) : (
          <Badge variant="secondary">Operational</Badge>
        )}
        <span className="text-xs text-muted-foreground">
          Period follows the dashboard filter above
        </span>
      </div>
      <KpiGrid columns={4}>
        <KpiCard
          title="Revenue"
          value={formatCurrency(kpis?.revenue ?? 0)}
          icon={<TrendingUp className="h-5 w-5" />}
          accent="success"
          loading={loading}
        />
        <KpiCard
          title="Expenses"
          value={formatCurrency(kpis?.expenses ?? 0)}
          icon={<TrendingDown className="h-5 w-5" />}
          accent="warning"
          trendUp={false}
          loading={loading}
        />
        <KpiCard
          title="Net profit"
          value={formatCurrency(kpis?.net_profit ?? 0)}
          icon={<Scale className="h-5 w-5" />}
          accent="primary"
          loading={loading}
        />
        <KpiCard
          title={fromLedger ? "Cash (ledger)" : "Cash balance"}
          value={formatCurrency(kpis?.cash_balance ?? kpis?.cash_collected ?? 0)}
          icon={<Wallet className="h-5 w-5" />}
          accent="info"
          loading={loading}
        />
      </KpiGrid>
    </ContentSection>
  );
}
