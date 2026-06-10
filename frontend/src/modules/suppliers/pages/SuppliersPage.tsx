import { useEffect, useState } from "react";
import { usePaginatedList } from "@/hooks/usePaginatedList";
import { Link, useNavigate } from "react-router-dom";
import { Truck, Plus, DollarSign, Package, Pencil, Trash2 } from "lucide-react";
import { PageLayout } from "@/components/layout/PageLayout";
import { FormField, FormSection, FormGrid } from "@/components/forms/FormField";
import { KpiCard, KpiGrid } from "@/components/data/KpiCard";
import { ContentSection } from "@/components/layout/ContentSection";
import { DataTable, type Column } from "@/components/data/DataTable";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import { suppliersApi } from "@/services/api/partners";
import { formatCurrency } from "@/utils/cn";
import type { Supplier, SupplierSummary } from "@/types/models/partners";

export function SuppliersPage() {
  const navigate = useNavigate();
  const [summary, setSummary] = useState<SupplierSummary | null>(null);
  const [summaryLoading, setSummaryLoading] = useState(true);
  const [search, setSearch] = useState("");

  const { data: suppliers, loading, page, setPage, pageSize, setPageSize, total, reload } =
    usePaginatedList(suppliersApi.list, { search });

  useEffect(() => {
    suppliersApi.summary()
      .then((sum) => setSummary(sum.data))
      .catch(() => setSummary(null))
      .finally(() => setSummaryLoading(false));
  }, []);

  const handleDelete = async (id: string) => {
    if (!confirm("Delete this supplier?")) return;
    await suppliersApi.delete(id);
    reload();
  };

  const columns: Column<Supplier>[] = [
    {
      key: "name",
      header: "Supplier",
      cell: (r) => (
        <div>
          <p className="font-medium">{r.company_name}</p>
          <p className="text-xs text-muted-foreground font-mono">{r.supplier_code}</p>
        </div>
      ),
      exportValue: (r) => r.company_name,
    },
    { key: "contact", header: "Contact", cell: (r) => r.contact_person || "—", exportValue: (r) => r.contact_person || "—" },
    { key: "email", header: "Email", cell: (r) => r.email || "—", exportValue: (r) => r.email || "—" },
    { key: "phone", header: "Phone", cell: (r) => r.phone || "—", exportValue: (r) => r.phone || "—" },
    {
      key: "balance",
      header: "Payable",
      cell: (r) => (
        <span className={r.outstanding_balance > 0 ? "text-destructive font-medium" : ""}>
          {formatCurrency(r.outstanding_balance)}
        </span>
      ),
      exportValue: (r) => formatCurrency(r.outstanding_balance),
    },
    {
      key: "status",
      header: "Status",
      cell: (r) => <Badge variant={r.is_active ? "success" : "secondary"}>{r.is_active ? "Active" : "Inactive"}</Badge>,
      exportValue: (r) => (r.is_active ? "Active" : "Inactive"),
    },
    {
      key: "actions",
      header: "",
      cell: (r) => (
        <div className="flex gap-1 justify-end">
          <Button variant="ghost" size="sm" onClick={() => navigate(`/suppliers/${r.id}/edit`)}>
            <Pencil className="h-4 w-4" />
          </Button>
          <Button variant="ghost" size="sm" onClick={() => handleDelete(r.id)}>
            <Trash2 className="h-4 w-4 text-destructive" />
          </Button>
        </div>
      ),
    },
  ];

  return (
    <PageLayout
      title="Suppliers"
      description="Supplier records, balances, and payment tracking."
      breadcrumbs={["Home", "Suppliers"]}
      actions={
        <Button asChild>
          <Link to="/suppliers/new"><Plus className="h-4 w-4" /> Add Supplier</Link>
        </Button>
      }
    >
      <KpiGrid>
        <KpiCard title="Total Suppliers" value={String(summary?.total ?? 0)} icon={<Truck className="h-5 w-5" />} loading={summaryLoading} />
        <KpiCard title="Active Vendors" value={String(summary?.active ?? 0)} icon={<Truck className="h-5 w-5" />} loading={summaryLoading} />
        <KpiCard title="Payables" value={formatCurrency(summary?.payables ?? 0)} icon={<DollarSign className="h-5 w-5" />} trendUp={false} loading={summaryLoading} />
        <KpiCard title="Listed" value={String(total)} icon={<Package className="h-5 w-5" />} loading={loading} />
      </KpiGrid>

      <ContentSection title="Supplier Directory" noPadding>
        <DataTable
          embedded
          exportTitle="Suppliers"
          columns={columns}
          data={suppliers}
          loading={loading}
          page={page}
          pageSize={pageSize}
          total={total}
          onPageChange={setPage}
          onPageSizeChange={setPageSize}
          searchPlaceholder="Search suppliers..."
          searchValue={search}
          onSearchChange={setSearch}
          emptyMessage="No suppliers found. Add your first supplier to get started."
        />
      </ContentSection>
    </PageLayout>
  );
}

export function SupplierFormPage({ editId }: { editId?: string }) {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(!!editId);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({
    company_name: "", contact_person: "", email: "", phone: "",
    address: "", payment_terms: "30", is_active: true,
  });

  useEffect(() => {
    if (!editId) return;
    suppliersApi.get(editId).then((res) => {
      const s = res.data;
      setForm({
        company_name: s.company_name, contact_person: s.contact_person,
        email: s.email, phone: s.phone, address: s.address,
        payment_terms: String(s.payment_terms), is_active: s.is_active,
      });
      setLoading(false);
    });
  }, [editId]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      const payload = { ...form, payment_terms: parseInt(form.payment_terms, 10) || 30 };
      if (editId) await suppliersApi.update(editId, payload);
      else await suppliersApi.create(payload);
      navigate("/suppliers");
    } catch (err) {
      alert(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <PageLayout title="Loading..." breadcrumbs={["Home", "Suppliers"]}>
        <div className="h-64 animate-pulse rounded-2xl bg-muted" />
      </PageLayout>
    );
  }

  return (
    <PageLayout
      title={editId ? "Edit Supplier" : "Add Supplier"}
      description="Manage vendor contact details and payment terms."
      breadcrumbs={["Home", "Suppliers", editId ? "Edit" : "New"]}
    >
      <form onSubmit={handleSubmit}>
        <FormSection title="Supplier Information">
          <FormGrid>
            <FormField label="Company Name" required>
              <Input required value={form.company_name} onChange={(e) => setForm({ ...form, company_name: e.target.value })} />
            </FormField>
            <FormField label="Contact Person">
              <Input value={form.contact_person} onChange={(e) => setForm({ ...form, contact_person: e.target.value })} />
            </FormField>
            <FormField label="Email"><Input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></FormField>
            <FormField label="Phone"><Input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} /></FormField>
            <FormField label="Payment Terms (days)">
              <Input type="number" min="0" value={form.payment_terms} onChange={(e) => setForm({ ...form, payment_terms: e.target.value })} />
            </FormField>
            <FormField label="Address" className="md:col-span-2">
              <Input value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} />
            </FormField>
          </FormGrid>
          <label className="mt-6 flex items-center gap-3 cursor-pointer">
            <Checkbox checked={form.is_active} onCheckedChange={(v) => setForm({ ...form, is_active: !!v })} />
            <span className="text-sm font-medium">Active supplier</span>
          </label>
        </FormSection>
        <div className="mt-6 flex gap-3">
          <Button type="submit" loading={saving}>{editId ? "Save Changes" : "Create Supplier"}</Button>
          <Button type="button" variant="secondary" onClick={() => navigate("/suppliers")}>Cancel</Button>
        </div>
      </form>
    </PageLayout>
  );
}
