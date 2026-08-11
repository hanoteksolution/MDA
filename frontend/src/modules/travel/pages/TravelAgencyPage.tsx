import { Link } from "react-router-dom";
import { useEffect, useState } from "react";
import { Globe2, Plane, Receipt, Users } from "lucide-react";
import { PageLayout } from "@/components/layout/PageLayout";
import { KpiCard, KpiGrid } from "@/components/data/KpiCard";
import { ContentSection } from "@/components/layout/ContentSection";
import { Button } from "@/components/ui/button";
import { useAuthStore } from "@/store/authStore";
import { travelApi, type TravelSummary } from "@/services/api/travel";
import { formatCurrency } from "@/utils/cn";

export function TravelAgencyPage() {
  const branchId = useAuthStore((s) => s.user?.branch?.id);
  const [summary, setSummary] = useState<TravelSummary | null>(null);

  useEffect(() => {
    travelApi.summary(branchId).then((response) => setSummary(response.data)).catch(() => setSummary(null));
  }, [branchId]);

  return (
    <PageLayout
      title="Travel Agency"
      description="Manage bookings, customers, services, payments, and travel operations."
      breadcrumbs={["Home", "Travel Agency"]}
      actions={
        <div className="flex gap-2">
          <Button asChild variant="outline" size="sm">
            <Link to="/travel/packages">Packages</Link>
          </Button>
          <Button asChild variant="outline" size="sm">
            <Link to="/travel/reports">Reports</Link>
          </Button>
        </div>
      }
    >
      <KpiGrid columns={4}>
        <KpiCard index={0} accent="primary" title="Total bookings" value={String(summary?.total_bookings ?? "—")} icon={<Plane className="h-5 w-5" />} />
        <KpiCard index={1} accent="warning" title="Awaiting confirmation" value={String(summary?.draft_bookings ?? "—")} icon={<Globe2 className="h-5 w-5" />} />
        <KpiCard index={2} accent="info" title="Travelers" value={String(summary?.travelers ?? "—")} icon={<Users className="h-5 w-5" />} />
        <KpiCard index={3} accent="success" title="Booking revenue" value={formatCurrency(summary?.total_revenue ?? 0)} icon={<Receipt className="h-5 w-5" />} />
      </KpiGrid>
      <ContentSection title="Travel operations" description="This workspace reuses shared ERP engines (Sales, Purchasing, Suppliers, Finance).">
        <p className="text-sm text-muted-foreground">
          Manage bookings, packages, travelers, flights, hotel stays, visas, and commissions. Outstanding balance: {formatCurrency(summary?.outstanding_amount ?? 0)}.
        </p>
      </ContentSection>
    </PageLayout>
  );
}
