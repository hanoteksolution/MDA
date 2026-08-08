import { useCallback, useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import { AlertTriangle, CalendarClock, ClipboardList, Package, Pill, Plus } from "lucide-react";
import { PageLayout } from "@/components/layout/PageLayout";
import { KpiCard, KpiGrid } from "@/components/data/KpiCard";
import { DataTable, type Column } from "@/components/data/DataTable";
import { ContentSection } from "@/components/layout/ContentSection";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { FormField, FormGrid } from "@/components/forms/FormField";
import { useWorkspaceTab } from "@/hooks/useWorkspaceTab";
import { usePermissions } from "@/hooks/usePermissions";
import { productsApi, inventoryApi } from "@/services/api/catalog";
import type { Product, Warehouse } from "@/types/models/catalog";
import {
  pharmacyApi,
  type PharmacyBatch,
  type PharmacyCategory,
  type PharmacySummary,
  type Prescription,
} from "@/services/api/pharmacy";

type Tab = "batches" | "prescriptions";

const PHARMACY_TAB_PATHS: Record<string, Tab> = {
  batches: "batches",
  expiry: "batches",
  prescriptions: "prescriptions",
};

export function PharmacyPage() {
  const location = useLocation();
  const { hasPermission } = usePermissions();
  const canManage = hasPermission("pharmacy.manage");
  const [tab, setTab] = useWorkspaceTab<Tab>("/pharmacy", PHARMACY_TAB_PATHS, "batches");
  const [summary, setSummary] = useState<PharmacySummary | null>(null);
  const [categories, setCategories] = useState<PharmacyCategory[]>([]);
  const [categoryId, setCategoryId] = useState("");
  const [catalogProducts, setCatalogProducts] = useState<Product[]>([]);
  const [batches, setBatches] = useState<PharmacyBatch[]>([]);
  const [prescriptions, setPrescriptions] = useState<Prescription[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [showExpiringOnly, setShowExpiringOnly] = useState(false);
  const [rxStatus, setRxStatus] = useState("");
  const [showRxForm, setShowRxForm] = useState(false);
  const [showBatchForm, setShowBatchForm] = useState(false);
  const [warehouses, setWarehouses] = useState<Warehouse[]>([]);
  const [batchForm, setBatchForm] = useState({
    product_id: "",
    warehouse_id: "",
    quantity: "1",
    batch_number: "",
    expiry_date: "",
    cost_price: "",
  });
  const [batchError, setBatchError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [dispenseRx, setDispenseRx] = useState<Prescription | null>(null);
  const [fillQtys, setFillQtys] = useState<Record<string, string>>({});
  const [rxForm, setRxForm] = useState({
    patient_name: "",
    patient_phone: "",
    prescribed_by: "",
    product_id: "",
    drug_name: "",
    dosage: "",
    frequency: "",
    quantity: "1",
    notes: "",
  });

  const featureFlags = {
    batches: summary?.features?.batches !== false,
    prescriptions: summary?.features?.prescriptions !== false,
    expiry_alerts: summary?.features?.expiry_alerts !== false,
  };

  useEffect(() => {
    if (tab === "batches" && !featureFlags.batches && featureFlags.prescriptions) {
      setTab("prescriptions");
    } else if (tab === "prescriptions" && !featureFlags.prescriptions && featureFlags.batches) {
      setTab("batches");
    }
  }, [featureFlags.batches, featureFlags.prescriptions, tab, setTab]);

  useEffect(() => {
    setShowExpiringOnly(location.pathname.includes("/expiry"));
  }, [location.pathname]);

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      const sumRes = await pharmacyApi.summary();
      setSummary(sumRes.data);
      const feats = sumRes.data.features;
      const allowBatches = feats?.batches !== false;
      const allowRx = feats?.prescriptions !== false;
      const allowExpiry = feats?.expiry_alerts !== false;
      if (allowBatches) {
        try {
          const catRes = await pharmacyApi.categories();
          setCategories(catRes.data ?? sumRes.data.categories ?? []);
        } catch {
          setCategories(sumRes.data.categories ?? []);
        }
      } else {
        setCategories([]);
      }
      const categoryFilter = categoryId || undefined;
      if (tab === "batches" && allowBatches) {
        const listRes =
          showExpiringOnly && allowExpiry
            ? await pharmacyApi.expiring({ page_size: 100, category_id: categoryFilter })
            : await pharmacyApi.batches({
                page_size: 100,
                search: search || undefined,
                category_id: categoryFilter,
              });
        setBatches(listRes.data.results);
        setPrescriptions([]);
      } else if (tab === "prescriptions" && allowRx) {
        const listRes = await pharmacyApi.prescriptions({
          page_size: 100,
          search: search || undefined,
          status: rxStatus || undefined,
          category_id: categoryFilter,
        });
        setPrescriptions(listRes.data.results);
        setBatches([]);
      } else {
        setBatches([]);
        setPrescriptions([]);
      }
    } catch {
      setSummary(null);
      setBatches([]);
      setPrescriptions([]);
    } finally {
      setLoading(false);
    }
  }, [search, showExpiringOnly, tab, rxStatus, categoryId]);

  useEffect(() => {
    void reload();
  }, [reload]);

  useEffect(() => {
    if (!showRxForm && !showBatchForm) return;
    void productsApi
      .list({
        page_size: 50,
        category: categoryId || undefined,
        is_active: "true",
      })
      .then((res) => setCatalogProducts(res.data.results ?? []))
      .catch(() => setCatalogProducts([]));
  }, [showRxForm, showBatchForm, categoryId]);

  useEffect(() => {
    if (!showBatchForm) return;
    void inventoryApi
      .warehouses()
      .then((res) => setWarehouses(res.data.results ?? []))
      .catch(() => setWarehouses([]));
  }, [showBatchForm]);

  const handleCreateBatch = async (e: React.FormEvent) => {
    e.preventDefault();
    const qty = Number(batchForm.quantity);
    if (!batchForm.product_id || !batchForm.warehouse_id || !Number.isFinite(qty) || qty <= 0) {
      setBatchError("Product, warehouse, and quantity are required.");
      return;
    }
    setSaving(true);
    setBatchError(null);
    try {
      await pharmacyApi.createBatch({
        product_id: batchForm.product_id,
        warehouse_id: batchForm.warehouse_id,
        quantity: qty,
        batch_number: batchForm.batch_number || undefined,
        expiry_date: batchForm.expiry_date || undefined,
        cost_price: batchForm.cost_price ? Number(batchForm.cost_price) : undefined,
      });
      setShowBatchForm(false);
      setBatchForm({
        product_id: "",
        warehouse_id: "",
        quantity: "1",
        batch_number: "",
        expiry_date: "",
        cost_price: "",
      });
      await reload();
    } catch (err) {
      setBatchError(err instanceof Error ? err.message : "Could not receive batch.");
    } finally {
      setSaving(false);
    }
  };

  const handleCreateRx = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!rxForm.patient_name.trim() || (!rxForm.drug_name.trim() && !rxForm.product_id)) return;
    setSaving(true);
    try {
      await pharmacyApi.createPrescription({
        patient_name: rxForm.patient_name.trim(),
        patient_phone: rxForm.patient_phone.trim() || undefined,
        prescribed_by: rxForm.prescribed_by.trim() || undefined,
        notes: rxForm.notes.trim() || undefined,
        product_id: rxForm.product_id || undefined,
        drug_name: rxForm.drug_name.trim(),
        dosage: rxForm.dosage.trim() || undefined,
        frequency: rxForm.frequency.trim() || undefined,
        quantity: Number(rxForm.quantity) || 1,
      });
      setRxForm({
        patient_name: "",
        patient_phone: "",
        prescribed_by: "",
        product_id: "",
        drug_name: "",
        dosage: "",
        frequency: "",
        quantity: "1",
        notes: "",
      });
      setShowRxForm(false);
      await reload();
    } finally {
      setSaving(false);
    }
  };

  const openDispense = (rx: Prescription) => {
    const initial: Record<string, string> = {};
    for (const line of rx.lines) {
      const remaining =
        line.quantity_remaining ?? Math.max(0, line.quantity - (line.quantity_dispensed ?? 0));
      initial[line.id] = String(remaining);
    }
    setFillQtys(initial);
    setDispenseRx(rx);
  };

  const handleDispense = async () => {
    if (!dispenseRx) return;
    setSaving(true);
    try {
      const lines = dispenseRx.lines
        .map((line) => ({
          id: line.id,
          quantity: Number(fillQtys[line.id] ?? 0),
        }))
        .filter((row) => row.quantity > 0);
      if (!lines.length) return;
      await pharmacyApi.dispensePrescription(dispenseRx.id, { lines });
      setDispenseRx(null);
      await reload();
    } finally {
      setSaving(false);
    }
  };

  const batchColumns: Column<PharmacyBatch>[] = [
    {
      key: "product",
      header: "Product",
      cell: (r) => (
        <div>
          <p className="font-medium">{r.product_name}</p>
          <p className="text-xs text-muted-foreground font-mono">{r.product_sku}</p>
        </div>
      ),
    },
    {
      key: "category",
      header: "Category",
      cell: (r) => r.category_name || "—",
    },
    {
      key: "batch",
      header: "Batch",
      cell: (r) => <span className="font-mono text-xs">{r.batch_number}</span>,
    },
    {
      key: "expiry",
      header: "Expiry",
      cell: (r) => r.expiry_date || "—",
    },
    {
      key: "qty",
      header: "Qty",
      cell: (r) => r.quantity,
    },
    {
      key: "warehouse",
      header: "Warehouse",
      cell: (r) => r.warehouse_name,
    },
    {
      key: "status",
      header: "Status",
      cell: (r) => (
        <Badge
          variant={
            r.status === "expired" ? "destructive" : r.status === "expiring" ? "warning" : "secondary"
          }
        >
          {r.status === "expired"
            ? "Expired"
            : r.status === "expiring"
              ? `Expiring (${r.days_to_expiry}d)`
              : "OK"}
        </Badge>
      ),
    },
  ];

  const rxColumns: Column<Prescription>[] = [
    {
      key: "rx",
      header: "Rx #",
      cell: (r) => <span className="font-mono text-xs">{r.rx_number}</span>,
    },
    {
      key: "patient",
      header: "Patient",
      cell: (r) => (
        <div>
          <p className="font-medium">{r.patient_name}</p>
          {r.patient_phone ? (
            <p className="text-xs text-muted-foreground">{r.patient_phone}</p>
          ) : null}
        </div>
      ),
    },
    {
      key: "prescriber",
      header: "Prescriber",
      cell: (r) => r.prescribed_by || "—",
    },
    {
      key: "date",
      header: "Prescribed",
      cell: (r) => r.prescribed_at || "—",
    },
    {
      key: "drugs",
      header: "Lines",
      cell: (r) => (
        <span className="text-sm">
          {r.lines
            .map((l) => {
              const rem =
                l.quantity_remaining ?? Math.max(0, l.quantity - (l.quantity_dispensed ?? 0));
              const cat = l.category_name ? ` · ${l.category_name}` : "";
              return `${l.drug_name} (${rem}/${l.quantity})${cat}`;
            })
            .join(", ") || `${r.line_count} line(s)`}
        </span>
      ),
    },
    {
      key: "status",
      header: "Status",
      cell: (r) => (
        <Badge
          variant={
            r.status === "dispensed"
              ? "secondary"
              : r.status === "cancelled"
                ? "destructive"
                : "warning"
          }
        >
          {r.status}
        </Badge>
      ),
    },
    {
      key: "actions",
      header: "",
      cell: (r) =>
        r.status === "active" || r.status === "draft" ? (
          <Button
            size="sm"
            variant="secondary"
            disabled={saving}
            onClick={() => openDispense(r)}
          >
            Dispense
          </Button>
        ) : null,
    },
  ];

  return (
    <PageLayout
      title="Pharmacy"
      description="Batches, FEFO, expiry alerts, and prescriptions — filter by product category."
      breadcrumbs={["Home", "Pharmacy"]}
    >
      <KpiGrid>
        {featureFlags.batches ? (
          <>
            <KpiCard
              title="Active batches"
              value={String(summary?.batch_count ?? 0)}
              icon={<Package className="h-5 w-5" />}
            />
            <KpiCard
              title="Units on batches"
              value={String(summary?.total_quantity ?? 0)}
              icon={<Pill className="h-5 w-5" />}
            />
          </>
        ) : null}
        {featureFlags.expiry_alerts ? (
          <>
            <KpiCard
              title={`Expiring ≤${summary?.expiry_alert_days ?? 30}d`}
              value={String(summary?.expiring_count ?? 0)}
              icon={<CalendarClock className="h-5 w-5" />}
              accent="warning"
            />
            <KpiCard
              title="Expired"
              value={String(summary?.expired_count ?? 0)}
              icon={<AlertTriangle className="h-5 w-5" />}
              accent="warning"
            />
          </>
        ) : null}
        {featureFlags.prescriptions ? (
          <KpiCard
            title="Active Rx"
            value={String(summary?.prescriptions_active ?? 0)}
            icon={<ClipboardList className="h-5 w-5" />}
          />
        ) : null}
      </KpiGrid>

      <div className="mt-4 flex flex-wrap gap-2">
        {(["batches", "prescriptions"] as Tab[])
          .filter((t) => (t === "batches" ? featureFlags.batches : featureFlags.prescriptions))
          .map((t) => (
          <Button
            key={t}
            variant={tab === t ? "default" : "secondary"}
            size="sm"
            onClick={() => {
              setTab(t);
              setSearch("");
            }}
          >
            {t === "batches" ? "Batches" : "Prescriptions"}
          </Button>
        ))}
      </div>

      {categories.length ? (
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <Button
            size="sm"
            variant={categoryId ? "secondary" : "default"}
            onClick={() => setCategoryId("")}
          >
            All categories
          </Button>
          {categories.map((c) => (
            <Button
              key={c.id}
              size="sm"
              variant={categoryId === c.id ? "default" : "secondary"}
              onClick={() => setCategoryId(categoryId === c.id ? "" : c.id)}
            >
              {c.name}
              <span className="ml-1 text-xs opacity-70">({c.batch_count})</span>
            </Button>
          ))}
        </div>
      ) : null}

      {tab === "batches" && featureFlags.batches && (
        <ContentSection
          title="Batches"
          description="Lots sorted by expiry (FEFO). Sales deduct earliest expiry first."
          action={
            <div className="flex flex-wrap items-center gap-2">
              <Input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search product or batch…"
                className="h-9 w-56"
                disabled={showExpiringOnly}
              />
              <select
                className="h-9 rounded-md border bg-background px-2 text-sm"
                value={categoryId}
                onChange={(e) => setCategoryId(e.target.value)}
                disabled={showExpiringOnly}
              >
                <option value="">All categories</option>
                {categories.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
              {featureFlags.expiry_alerts ? (
              <label className="flex items-center gap-2 text-sm text-muted-foreground">
                <input
                  type="checkbox"
                  checked={showExpiringOnly}
                  onChange={(e) => {
                    const next = e.target.checked;
                    setShowExpiringOnly(next);
                    if (next) setTab("batches");
                  }}
                />
                Expiring / expired only
              </label>
              ) : null}
              {canManage ? (
                <Button size="sm" onClick={() => setShowBatchForm((v) => !v)}>
                  <Plus className="h-4 w-4 mr-1" />
                  {showBatchForm ? "Cancel" : "New batch"}
                </Button>
              ) : null}
            </div>
          }
        >
          {showBatchForm && canManage ? (
            <form onSubmit={handleCreateBatch} className="mb-4 rounded-xl border border-border/70 p-4">
              <FormGrid>
                <FormField label="Medicine">
                  <select
                    className="h-9 w-full rounded-md border bg-background px-2 text-sm"
                    value={batchForm.product_id}
                    onChange={(e) => setBatchForm((f) => ({ ...f, product_id: e.target.value }))}
                  >
                    <option value="">Select product</option>
                    {catalogProducts.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.name}
                      </option>
                    ))}
                  </select>
                </FormField>
                <FormField label="Warehouse">
                  <select
                    className="h-9 w-full rounded-md border bg-background px-2 text-sm"
                    value={batchForm.warehouse_id}
                    onChange={(e) => setBatchForm((f) => ({ ...f, warehouse_id: e.target.value }))}
                  >
                    <option value="">Select warehouse</option>
                    {warehouses.map((w) => (
                      <option key={w.id} value={w.id}>
                        {w.name}
                      </option>
                    ))}
                  </select>
                </FormField>
                <FormField label="Quantity">
                  <Input
                    type="number"
                    min="0.01"
                    step="0.01"
                    value={batchForm.quantity}
                    onChange={(e) => setBatchForm((f) => ({ ...f, quantity: e.target.value }))}
                  />
                </FormField>
                <FormField label="Batch number">
                  <Input
                    value={batchForm.batch_number}
                    onChange={(e) => setBatchForm((f) => ({ ...f, batch_number: e.target.value }))}
                    placeholder="Optional"
                  />
                </FormField>
                <FormField label="Expiry">
                  <Input
                    type="date"
                    value={batchForm.expiry_date}
                    onChange={(e) => setBatchForm((f) => ({ ...f, expiry_date: e.target.value }))}
                  />
                </FormField>
                <FormField label="Cost">
                  <Input
                    type="number"
                    min="0"
                    step="0.01"
                    value={batchForm.cost_price}
                    onChange={(e) => setBatchForm((f) => ({ ...f, cost_price: e.target.value }))}
                  />
                </FormField>
                <div className="flex items-end">
                  <Button type="submit" size="sm" disabled={saving}>
                    {saving ? "Saving…" : "Receive batch"}
                  </Button>
                </div>
              </FormGrid>
              {batchError ? <p className="mt-2 text-sm text-destructive">{batchError}</p> : null}
            </form>
          ) : null}
          <DataTable
            columns={batchColumns}
            data={batches}
            loading={loading}
            emptyMessage="No batches yet. Receive a batch or post a pharmacy GRN."
          />
        </ContentSection>
      )}

      {tab === "prescriptions" && featureFlags.prescriptions && (
        <ContentSection
          title="Prescriptions"
          description="Create Rx, partial-fill dispense (FEFO when product-linked), track remaining qty."
          action={
            <div className="flex flex-wrap items-center gap-2">
              <Input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search Rx or patient…"
                className="h-9 w-56"
              />
              <select
                className="h-9 rounded-md border bg-background px-2 text-sm"
                value={categoryId}
                onChange={(e) => setCategoryId(e.target.value)}
              >
                <option value="">All categories</option>
                {categories.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
              <select
                className="h-9 rounded-md border bg-background px-2 text-sm"
                value={rxStatus}
                onChange={(e) => setRxStatus(e.target.value)}
              >
                <option value="">All statuses</option>
                <option value="active">Active</option>
                <option value="dispensed">Dispensed</option>
                <option value="draft">Draft</option>
                <option value="cancelled">Cancelled</option>
              </select>
              <Button size="sm" onClick={() => setShowRxForm((v) => !v)}>
                {showRxForm ? "Cancel" : "New Rx"}
              </Button>
            </div>
          }
        >
          {dispenseRx && (
            <div className="mb-4 space-y-3 rounded-lg border border-amber-500/30 bg-amber-500/5 p-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <p className="font-medium">
                    Dispense {dispenseRx.rx_number} — {dispenseRx.patient_name}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Enter qty to fill per line (defaults to remaining). Leave 0 to skip.
                  </p>
                </div>
                <Button size="sm" variant="secondary" onClick={() => setDispenseRx(null)}>
                  Close
                </Button>
              </div>
              <div className="grid gap-2 sm:grid-cols-2">
                {dispenseRx.lines.map((line) => {
                  const remaining =
                    line.quantity_remaining ??
                    Math.max(0, line.quantity - (line.quantity_dispensed ?? 0));
                  return (
                    <label key={line.id} className="flex flex-col gap-1 text-sm">
                      <span>
                        {line.drug_name}{" "}
                        <span className="text-muted-foreground">
                          (remaining {remaining})
                        </span>
                      </span>
                      <Input
                        type="number"
                        min="0"
                        max={remaining}
                        step="any"
                        value={fillQtys[line.id] ?? "0"}
                        onChange={(e) =>
                          setFillQtys((prev) => ({ ...prev, [line.id]: e.target.value }))
                        }
                      />
                    </label>
                  );
                })}
              </div>
              <div className="flex gap-2">
                <Button size="sm" loading={saving} onClick={() => void handleDispense()}>
                  Confirm dispense
                </Button>
                <Button
                  size="sm"
                  variant="secondary"
                  disabled={saving}
                  onClick={() => {
                    const full: Record<string, string> = {};
                    for (const line of dispenseRx.lines) {
                      const rem =
                        line.quantity_remaining ??
                        Math.max(0, line.quantity - (line.quantity_dispensed ?? 0));
                      full[line.id] = String(rem);
                    }
                    setFillQtys(full);
                  }}
                >
                  Fill all remaining
                </Button>
              </div>
            </div>
          )}
          {showRxForm && (
            <form
              onSubmit={(e) => void handleCreateRx(e)}
              className="mb-4 grid gap-3 rounded-lg border p-4 sm:grid-cols-2 lg:grid-cols-3"
            >
              <Input
                required
                placeholder="Patient name *"
                value={rxForm.patient_name}
                onChange={(e) => setRxForm({ ...rxForm, patient_name: e.target.value })}
              />
              <Input
                placeholder="Phone"
                value={rxForm.patient_phone}
                onChange={(e) => setRxForm({ ...rxForm, patient_phone: e.target.value })}
              />
              <Input
                placeholder="Prescribed by"
                value={rxForm.prescribed_by}
                onChange={(e) => setRxForm({ ...rxForm, prescribed_by: e.target.value })}
              />
              <select
                className="h-9 rounded-md border bg-background px-2 text-sm"
                value={rxForm.product_id}
                onChange={(e) => {
                  const productId = e.target.value;
                  const product = catalogProducts.find((p) => p.id === productId);
                  setRxForm({
                    ...rxForm,
                    product_id: productId,
                    drug_name: product?.name || rxForm.drug_name,
                  });
                }}
              >
                <option value="">Product (optional)</option>
                {catalogProducts.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                    {p.category_name ? ` · ${p.category_name}` : ""}
                  </option>
                ))}
              </select>
              <Input
                required={!rxForm.product_id}
                placeholder="Drug name *"
                value={rxForm.drug_name}
                onChange={(e) => setRxForm({ ...rxForm, drug_name: e.target.value })}
              />
              <Input
                placeholder="Dosage"
                value={rxForm.dosage}
                onChange={(e) => setRxForm({ ...rxForm, dosage: e.target.value })}
              />
              <Input
                placeholder="Frequency"
                value={rxForm.frequency}
                onChange={(e) => setRxForm({ ...rxForm, frequency: e.target.value })}
              />
              <Input
                type="number"
                min="0.0001"
                step="any"
                placeholder="Quantity"
                value={rxForm.quantity}
                onChange={(e) => setRxForm({ ...rxForm, quantity: e.target.value })}
              />
              <Input
                className="sm:col-span-2"
                placeholder="Notes"
                value={rxForm.notes}
                onChange={(e) => setRxForm({ ...rxForm, notes: e.target.value })}
              />
              <div className="flex items-center gap-2">
                <Button type="submit" size="sm" loading={saving}>
                  Save prescription
                </Button>
              </div>
            </form>
          )}
          <DataTable
            columns={rxColumns}
            data={prescriptions}
            loading={loading}
            emptyMessage="No prescriptions yet."
          />
        </ContentSection>
      )}
    </PageLayout>
  );
}
