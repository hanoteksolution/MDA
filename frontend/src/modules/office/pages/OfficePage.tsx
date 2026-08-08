import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Briefcase, Building2, Plus, Wallet } from "lucide-react";
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
import { officeApi, type OfficeLease, type OfficeLeaseCharge, type OfficeSummary } from "@/services/api/office";
import { propertyApi, type PropertyUnit } from "@/services/api/property";
import { formatCurrency } from "@/utils/cn";

export function OfficePage() {
  const branchId = useAuthStore((s) => s.user?.branch?.id);
  const { hasPermission } = usePermissions();
  const canManage = hasPermission("office_rental.manage");

  const [summary, setSummary] = useState<OfficeSummary | null>(null);
  const [leases, setLeases] = useState<OfficeLease[]>([]);
  const [units, setUnits] = useState<PropertyUnit[]>([]);
  const [loading, setLoading] = useState(true);
  const [chargesLease, setChargesLease] = useState<OfficeLease | null>(null);
  const [charges, setCharges] = useState<OfficeLeaseCharge[]>([]);
  const [chargesLoading, setChargesLoading] = useState(false);
  const [form, setForm] = useState({
    company_name: "",
    contact_name: "",
    phone: "",
    unit_id: "",
    start_date: new Date().toISOString().slice(0, 10),
    service_charge: "50",
  });

  const reload = useCallback(async () => {
    if (!branchId) return;
    setLoading(true);
    try {
      const [sumRes, leaseRes, unitRes] = await Promise.all([
        officeApi.summary(branchId),
        officeApi.leases(1, branchId),
        propertyApi.units(1, branchId),
      ]);
      setSummary(sumRes.data);
      setLeases(leaseRes.data.results);
      setUnits(unitRes.data.results.filter((u) => u.kind === "office" || u.kind === "retail"));
    } finally {
      setLoading(false);
    }
  }, [branchId]);

  useEffect(() => {
    void reload();
  }, [reload]);

  const createLease = async () => {
    if (!branchId || !form.company_name || !form.unit_id) return;
    await officeApi.createLease({
      branch_id: branchId,
      company_name: form.company_name,
      contact_name: form.contact_name,
      phone: form.phone,
      unit_id: form.unit_id,
      start_date: form.start_date,
      service_charge: Number(form.service_charge) || 0,
      parking_slots: 1,
      furnished: true,
      internet_included: true,
      activate: true,
    });
    setForm({
      company_name: "",
      contact_name: "",
      phone: "",
      unit_id: "",
      start_date: new Date().toISOString().slice(0, 10),
      service_charge: "50",
    });
    void reload();
  };

  const openCharges = async (lease: OfficeLease) => {
    setChargesLease(lease);
    setChargesLoading(true);
    try {
      const res = await officeApi.lease(lease.id);
      setChargesLease(res.data);
      setCharges(res.data.charges || []);
    } catch {
      setCharges([]);
    } finally {
      setChargesLoading(false);
    }
  };

  const columns: Column<OfficeLease>[] = [
    {
      key: "number",
      header: "Lease",
      cell: (r) => <span className="font-medium">{r.lease_number}</span>,
    },
    { key: "company", header: "Company", cell: (r) => r.company_name },
    {
      key: "unit",
      header: "Unit",
      cell: (r) => `${r.unit_code}${r.building_name ? ` · ${r.building_name}` : ""}`,
    },
    {
      key: "total",
      header: "Monthly",
      cell: (r) => formatCurrency(r.monthly_total),
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
              <Button size="sm" onClick={() => officeApi.activate(r.id).then(reload)}>
                Activate
              </Button>
            ) : null}
            {r.status === "active" ? (
              <>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => officeApi.postRent(r.id).then(reload)}
                >
                  Post rent
                </Button>
                <Button size="sm" variant="secondary" onClick={() => void openCharges(r)}>
                  Charges
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => officeApi.terminate(r.id).then(reload)}
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
      title="Office"
      description="Commercial leases on shared property units — service charge and parking included."
      breadcrumbs={["Home", "Office"]}
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
          icon={<Briefcase className="h-5 w-5" />}
          loading={loading}
        />
        <KpiCard
          index={1}
          accent="success"
          title="Vacant offices"
          value={`${summary?.units_vacant ?? 0}/${summary?.office_units ?? 0}`}
          icon={<Building2 className="h-5 w-5" />}
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

      <ContentSection title="Commercial leases" description="Activate occupies the unit; terminate frees it">
        {canManage ? (
          <FormGrid className="mb-4">
            <FormField label="Company">
              <Input
                value={form.company_name}
                onChange={(e) => setForm((f) => ({ ...f, company_name: e.target.value }))}
              />
            </FormField>
            <FormField label="Contact">
              <Input
                value={form.contact_name}
                onChange={(e) => setForm((f) => ({ ...f, contact_name: e.target.value }))}
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
                  <SelectValue placeholder="Select vacant office" />
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
            <FormField label="Service charge">
              <Input
                value={form.service_charge}
                onChange={(e) => setForm((f) => ({ ...f, service_charge: e.target.value }))}
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
          emptyMessage="No office leases yet."
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
                              officeApi.invoiceCharge(c.id).then(() => openCharges(chargesLease))
                            }
                          >
                            Invoice
                          </Button>
                          <Button
                            size="sm"
                            onClick={() =>
                              officeApi
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
                            officeApi
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
