import { Link } from "react-router-dom";
import { useEffect, useState } from "react";
import { ContentSection } from "@/components/layout/ContentSection";
import { KpiCard, KpiGrid } from "@/components/data/KpiCard";
import { PageLayout } from "@/components/layout/PageLayout";
import { Button } from "@/components/ui/button";
import { travelApi, type TravelBooking, type TravelMobileSummary, type TravelSummary } from "@/services/api/travel";

export function TravelFieldPage() {
  const [summary, setSummary] = useState<TravelMobileSummary | null>(null);
  const [bookings, setBookings] = useState<TravelBooking[]>([]);
  useEffect(() => {
    travelApi.mobileSummary().then((r) => setSummary(r.data)).catch(() => setSummary(null));
    travelApi.mobileBookings().then((r) => setBookings(r.data.results)).catch(() => setBookings([]));
  }, []);
  return <PageLayout title="Field operations" description="Mobile-ready view for travel agents." breadcrumbs={["Travel", "Field"]}>
    <KpiGrid columns={3}>
      <KpiCard index={0} accent="primary" title="Today's bookings" value={String(summary?.todays_bookings ?? "—")} />
      <KpiCard index={1} accent="warning" title="Open visas" value={String(summary?.open_visas ?? "—")} />
      <KpiCard index={2} accent="info" title="Pending commissions" value={String(summary?.pending_commissions ?? "—")} />
    </KpiGrid>
    <ContentSection title="Confirmed upcoming bookings">
      <div className="space-y-2">{bookings.map((booking) => <div key={booking.id} className="rounded border p-3">
        <div>{booking.booking_code} · {String(booking.travel_date ?? "Date pending")}</div>
        <div className="mt-2 flex gap-2"><Button size="sm" asChild><Link to={`/travel/bookings/${booking.id}`}>Open booking</Link></Button><Button size="sm" variant="outline" asChild><Link to={`/travel/payments/new?booking_id=${booking.id}`}>Record payment</Link></Button><Button size="sm" variant="outline" asChild><Link to="/travel/visas">Update visa note</Link></Button></div>
      </div>)}</div>
    </ContentSection>
  </PageLayout>;
}

export function TravelReportsPage() {
  const [summary, setSummary] = useState<TravelSummary | null>(null);
  useEffect(() => { travelApi.summary().then((r) => setSummary(r.data)).catch(() => setSummary(null)); }, []);
  return <PageLayout title="Travel reports" description="Travel KPIs and shared finance reporting." breadcrumbs={["Travel", "Reports"]}>
    <KpiGrid columns={3}>
      <KpiCard index={0} accent="primary" title="Total bookings" value={String(summary?.total_bookings ?? "—")} />
      <KpiCard index={1} accent="warning" title="Outstanding amount" value={String(summary?.outstanding_amount ?? "—")} />
      <KpiCard index={2} accent="info" title="Pending visas" value={String(summary?.pending_visas ?? "—")} />
    </KpiGrid>
    <ContentSection title="Shared finance engine"><div className="flex gap-2"><Button asChild><Link to="/travel/finance">Travel finance</Link></Button></div></ContentSection>
  </PageLayout>;
}
