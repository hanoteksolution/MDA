import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Home, KeyRound, Plus, Wallet } from "lucide-react";
import { PageLayout } from "@/components/layout/PageLayout";
import { KpiCard, KpiGrid } from "@/components/data/KpiCard";
import { DataTable, type Column } from "@/components/data/DataTable";
import { ContentSection } from "@/components/layout/ContentSection";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { FormField, FormGrid } from "@/components/forms/FormField";
import { usePermissions } from "@/hooks/usePermissions";
import { useAuthStore } from "@/store/authStore";
import {
  housingApi,
  type HousingLease,
  type HousingSummary,
  type LeaseCharge,
} from "@/services/api/housing";
import { propertyApi, type PropertyUnit } from "@/services/api/property";
import { formatCurrency } from "@/utils/cn";

export function HousingPage() {
  const branchId = useAuthStore((s) => s.user?.branch?.id);
  const { hasPermission } = usePermissions();
  const canManage = hasPermission("housing_rental.manage");

  const [summary, setSummary] = useState<HousingSummary | null>(null);
  const [leases, setLeases] = useState<HousingLease[]>([]);
  const [units, setUnits] = useState<PropertyUnit[]>([]);
  const [loading, setLoading] = useState(true);
  const [chargesLease, setChargesLease] = useState<HousingLease | null>(null);
  const [charges, setCharges] = useState<LeaseCharge[]>([]);
  const [chargesLoading, setChargesLoading] = useState(false);
  const [form, setForm] = useState({
    tenant_name: "",
    phone: "",
    unit_id: "",
    start_date: new Date().toISOString().slice(0, 10),
    rent_amount: "",
  });

  const reload = useCallback(async () => {
    if (!branchId) return;
    setLoading(true);
    try {
      const [sumRes, leaseRes, unitRes] = await Promise.all([
        housingApi.summary(branchId),
        housingApi.leases(1, branchId),
        propertyApi.units(1, branchId),
      ]);
      setSummary(sumRes.data);
      setLeases(leaseRes.data.results);
      setUnits(
        unitRes.data.results.filter(
          (u) => u.kind === "residential" || u.kind === "other"
        )
      );
    } finally {
      setLoading(false);
    }
  }, [branchId]);

  useEffect(() => {
    void reload();
  }, [reload]);

  const createLease = async () => {
    if (!branchId || !form.tenant_name || !form.unit_id) return;
    await housingApi.createLease({
      branch_id: branchId,
      tenant_name: form.tenant_name,
      phone: form.phone,
      unit_id: form.unit_id,
      start_date: form.start_date,
      rent_amount: form.rent_amount ? Number(form.rent_amount) : undefined,
      activate: true,
    });
    setForm({
      tenant_name: "",
      phone: "",
      unit_id: "",
      start_date: new Date().toISOString().slice(0, 10),
      rent_amount: "",
    });
    void reload();
  };

  const openCharges = async (lease: HousingLease) => {
    setChargesLease(lease);
    setChargesLoading(true);
    try {
      const res = await housingApi.lease(lease.id);
      setChargesLease(res.data);
      setCharges(res.data.charges || []);
    } catch {
      setCharges([]);
    } finally {
      setChargesLoading(false);
    }
  };

  const columns: Column<HousingLease>[] = [
    {
      key: "number",
      header: "Lease",
      cell: (r) => <span className="font-medium">{r.lease_number}</span>,
    },
    { key: "tenant", header: "Tenant", cell: (r) => r.tenant_name },
    {
      key: "unit",
      header: "Unit",
      cell: (r) => `${r.unit_code}${r.building_name ? ` · ${r.building_name}` : ""}`,
    },
    {
      key: "rent",
      header: "Rent",
      cell: (r) => formatCurrency(r.rent_amount),
    },
    {
      key: "status",
      header: "Status",
      cell: (r) => <Badge variant="secondary">{r.status}</Badge>,
    },
    {
      key: "actions",
      header: "",
      cell: (r) =>
        canManage ? (
          <div className="flex justify-end gap-1">
            {r.status === "draft" ? (
              <Button size="sm" onClick={() => housingApi.activate(r.id).then(reload)}>
                Activate
              </Button>
            ) : null}
            {r.status === "active" ? (
              <>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => housingApi.postRent(r.id).then(reload)}
                >
                  Post rent
                </Button>
                <Button size="sm" variant="secondary" onClick={() => void openCharges(r)}>
                  Charges
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => housingApi.terminate(r.id).then(reload)}
                >
                  Terminate
                </Button>
              </>
            ) : null}
          </div>
        ) : null,
    },
  ];

  const vacantUnits = units.filter((u) => u.status === "vacant" || u.status === "reserved");

  return (
    <PageLayout
      title="Housing"
      description="Residential leases on shared property units — no separate building catalog."
      breadcrumbs={["Home", "Housing"]}
      actions={
        <Button variant="outline" size="sm" asChild>
          <Link to="/property">Property core</Link>
        </Button>
      }
    >
      <KpiGrid columns={4}>
        <KpiCard
          index={0}
          accent="primary"
          title="Active leases"
          value={String(summary?.leases_active ?? 0)}
          icon={<KeyRound className="h-5 w-5" />}
          loading={loading}
        />
        <KpiCard
          index={1}
          accent="success"
          title="Vacant residential"
          value={`${summary?.units_vacant ?? 0}/${summary?.residential_units ?? 0}`}
          icon={<Home className="h-5 w-5" />}
          loading={loading}
        />
        <KpiCard
          index={2}
          accent="warning"
          title="Overdue charges"
          value={String(summary?.charges_overdue ?? 0)}
          icon={<Wallet className="h-5 w-5" />}
          loading={loading}
        />
        <KpiCard
          index={3}
          accent="info"
          title="Rent pending"
          value={formatCurrency(summary?.rent_pending_amount ?? 0)}
          icon={<Wallet className="h-5 w-5" />}
          loading={loading}
        />
      </KpiGrid>

      <ContentSection title="Leases" description="Activate occupies the unit; terminate frees it">
        {canManage ? (
          <FormGrid className="mb-4">
            <FormField label="Tenant name">
              <Input
                value={form.tenant_name}
                onChange={(e) => setForm((f) => ({ ...f, tenant_name: e.target.value }))}
              />
            </FormField>
            <FormField label="Phone">
              <Input
                value={form.phone}
                onChange={(e) => setForm((f) => ({ ...f, phone: e.target.value }))}
              />
            </FormField>
            <FormField label="Unit">
              <Select
                value={form.unit_id}
                onValueChange={(v) => setForm((f) => ({ ...f, unit_id: v }))}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select vacant unit" />
                </SelectTrigger>
                <SelectContent>
                  {vacantUnits.map((u) => (
                    <SelectItem key={u.id} value={u.id}>
                      {u.code} · {u.building_name} ({formatCurrency(u.rent_amount)})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </FormField>
            <FormField label="Start">
              <Input
                type="date"
                value={form.start_date}
                onChange={(e) => setForm((f) => ({ ...f, start_date: e.target.value }))}
              />
            </FormField>
            <FormField label="Rent override">
              <Input
                value={form.rent_amount}
                onChange={(e) => setForm((f) => ({ ...f, rent_amount: e.target.value }))}
                placeholder="Unit default"
              />
            </FormField>
            <div className="flex items-end">
              <Button onClick={createLease}>
                <Plus className="h-4 w-4 mr-1.5" />
                Activate lease
              </Button>
            </div>
          </FormGrid>
        ) : null}
        <DataTable
          columns={columns}
          data={leases}
          loading={loading}
          emptyMessage="No housing leases yet."
        />
      </ContentSection>

      {chargesLease ? (
        <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 p-4 sm:items-center">
          <div className="w-full max-w-lg rounded-2xl border border-border bg-card p-4 shadow-xl">
            <div className="mb-3 flex items-center justify-between">
              <h3 className="text-sm font-semibold">
                Charges · {chargesLease.lease_number}
              </h3>
              <Button size="sm" variant="ghost" onClick={() => setChargesLease(null)}>
                Close
              </Button>
            </div>
            {chargesLoading ? (
              <p className="py-6 text-center text-sm text-muted-foreground">Loading…</p>
            ) : charges.length === 0 ? (
              <p className="py-6 text-center text-sm text-muted-foreground">
                No charges yet. Post rent first.
              </p>
            ) : (
              <ul className="max-h-80 space-y-2 overflow-y-auto">
                {charges.map((c) => (
                  <li
                    key={c.id}
                    className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-border px-3 py-2.5 text-sm"
                  >
                    <div className="min-w-0">
                      <p className="font-medium truncate">{c.description}</p>
                      <p className="text-xs text-muted-foreground">
                        {c.charge_type} · {c.status}
                        {c.invoice_number ? ` · ${c.invoice_number}` : ""}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="tabular-nums font-medium">
                        {formatCurrency(c.amount)}
                      </span>
                      {c.status === "pending" ? (
                        <>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() =>
                              housingApi.invoiceCharge(c.id).then(() => openCharges(chargesLease))
                            }
                          >
                            Invoice
                          </Button>
                          <Button
                            size="sm"
                            onClick={() =>
                              housingApi
                                .markPaid(c.id, { payment_method: "cash" })
                                .then(() => openCharges(chargesLease))
                            }
                          >
                            Collect
                          </Button>
                        </>
                      ) : null}
                      {c.status === "invoiced" ? (
                        <Button
                          size="sm"
                          onClick={() =>
                            housingApi
                              .markPaid(c.id, { payment_method: "cash" })
                              .then(() => openCharges(chargesLease))
                          }
                        >
                          Collect
                        </Button>
                      ) : null}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      ) : null}
    </PageLayout>
  );
}
