import { useEffect, useState } from "react";
import { usePaginatedList } from "@/hooks/usePaginatedList";
import { Link, useNavigate } from "react-router-dom";
import { Users, UserPlus, CreditCard, ShoppingBag, Mail, Phone, Pencil, Trash2, Printer, FileDown, Loader2, FileOutput } from "lucide-react";
import { useCustomerListPrint } from "../hooks/useCustomerListPrint";
import { PageLayout } from "@/components/layout/PageLayout";
import { FormField, FormSection, FormGrid } from "@/components/forms/FormField";
import { KpiCard, KpiGrid } from "@/components/data/KpiCard";
import { ContentSection } from "@/components/layout/ContentSection";
import { DataTable, type Column } from "@/components/data/DataTable";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { customersApi } from "@/services/api/partners";
import { settingsApi } from "@/services/api/admin";
import { formatCurrency } from "@/utils/cn";
import type { Customer, CustomerSummary } from "@/types/models/partners";

export function CustomersPage() {
  const navigate = useNavigate();
  const [summary, setSummary] = useState<CustomerSummary | null>(null);
  const [summaryLoading, setSummaryLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState("");

  const {
    data: customers,
    loading,
    page,
    setPage,
    pageSize,
    setPageSize,
    total,
    reload,
  } = usePaginatedList(customersApi.list, { search, customer_type: typeFilter });
  const { printing, printCustomerList, downloadCustomerList } = useCustomerListPrint({
    search,
    customer_type: typeFilter,
  });

  useEffect(() => {
    setSummaryLoading(true);
    customersApi.summary()
      .then((sum) => setSummary(sum.data))
      .catch(() => setSummary(null))
      .finally(() => setSummaryLoading(false));
  }, []);

  const handleDelete = async (id: string) => {
    if (!confirm("Delete this customer?")) return;
    await customersApi.delete(id);
    reload();
  };

  const columns: Column<Customer>[] = [
    {
      key: "name",
      header: "Customer",
      cell: (r) => (
        <div>
          <p className="font-medium">{r.full_name}</p>
          <p className="text-xs text-muted-foreground font-mono">{r.customer_code}</p>
        </div>
      ),
      exportValue: (r) => r.full_name,
    },
    {
      key: "contact",
      header: "Contact",
      cell: (r) => (
        <div className="text-sm">
          {r.email && <p className="flex items-center gap-1"><Mail className="h-3 w-3" /> {r.email}</p>}
          {r.phone && <p className="flex items-center gap-1 text-muted-foreground"><Phone className="h-3 w-3" /> {r.phone}</p>}
        </div>
      ),
      exportValue: (r) => [r.email, r.phone].filter(Boolean).join(" / "),
    },
    { key: "type", header: "Type", cell: (r) => <Badge variant="secondary" className="capitalize">{r.customer_type}</Badge>, exportValue: (r) => r.customer_type },
    {
      key: "balance",
      header: "Balance",
      cell: (r) => (
        <span className={r.outstanding_balance > 0 ? "text-warning font-medium" : ""}>
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
          <Button variant="ghost" size="sm" onClick={() => navigate(`/customers/${r.id}/edit`)}>
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
      title="Customers"
      description="Customer profiles, credit accounts, and purchase history."
      breadcrumbs={["Home", "Customers"]}
      backTo="/dashboard"
      backLabel="Dashboard"
      actions={
        <div className="flex gap-2">
          <Button
            variant="secondary"
            disabled={printing}
            onClick={() => void printCustomerList()}
          >
            {printing ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileOutput className="h-4 w-4" />}
            Print Report
          </Button>
          <Button
            variant="secondary"
            disabled={printing}
            onClick={() => void downloadCustomerList()}
          >
            {printing ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileDown className="h-4 w-4" />}
            PDF
          </Button>
          <Button asChild>
            <Link to="/customers/new"><UserPlus className="h-4 w-4" /> Add Customer</Link>
          </Button>
        </div>
      }
    >
      <KpiGrid>
        <KpiCard title="Total Customers" value={String(summary?.total ?? 0)} icon={<Users className="h-5 w-5" />} loading={summaryLoading} />
        <KpiCard title="Active Accounts" value={String(summary?.active ?? 0)} icon={<Users className="h-5 w-5" />} loading={summaryLoading} />
        <KpiCard title="Credit Outstanding" value={formatCurrency(summary?.credit_outstanding ?? 0)} icon={<CreditCard className="h-5 w-5" />} loading={summaryLoading} />
        <KpiCard title="Listed" value={String(total)} icon={<ShoppingBag className="h-5 w-5" />} loading={loading} />
      </KpiGrid>

      <ContentSection
        title="Customer Directory"
        noPadding
        action={
          <div className="flex gap-2">
            <Button variant="secondary" size="sm" disabled={printing} onClick={() => void printCustomerList()}>
              {printing ? <Loader2 className="h-4 w-4 animate-spin" /> : <Printer className="h-4 w-4" />}
              Print
            </Button>
            <Button size="sm" disabled={printing} onClick={() => void downloadCustomerList()}>
              {printing ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileDown className="h-4 w-4" />}
              PDF
            </Button>
          </div>
        }
      >
        <DataTable
          embedded
          exportTitle="Customers"
          listPrint={false}
          listPdf={false}
          columns={columns}
          data={customers}
          loading={loading}
          page={page}
          pageSize={pageSize}
          total={total}
          onPageChange={setPage}
          onPageSizeChange={setPageSize}
          searchPlaceholder="Search by name, email, or phone..."
          searchValue={search}
          onSearchChange={setSearch}
          filters={[{
            key: "type", label: "Type", value: typeFilter, onChange: setTypeFilter,
            options: [
              { label: "All Types", value: "" },
              { label: "Retail", value: "retail" },
              { label: "Wholesale", value: "wholesale" },
              { label: "Corporate", value: "corporate" },
            ],
          }]}
          emptyMessage="No customers found. Add your first customer to get started."
        />
      </ContentSection>
    </PageLayout>
  );
}

export function CustomerFormPage({ editId }: { editId?: string }) {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(!!editId);
  const [saving, setSaving] = useState(false);
  const [branches, setBranches] = useState<{ id: string; name: string }[]>([]);
  const [form, setForm] = useState({
    full_name: "", email: "", phone: "", address: "",
    customer_type: "retail", credit_limit: "0", branch_id: "", is_active: true,
  });

  useEffect(() => {
    settingsApi.branches().then((res) => setBranches(res.data));
  }, []);

  useEffect(() => {
    if (!editId) return;
    customersApi.get(editId).then((res) => {
      const c = res.data;
      setForm({
        full_name: c.full_name, email: c.email, phone: c.phone, address: c.address,
        customer_type: c.customer_type, credit_limit: String(c.credit_limit),
        branch_id: c.branch_id || "", is_active: c.is_active,
      });
      setLoading(false);
    });
  }, [editId]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      const payload = {
        ...form,
        credit_limit: parseFloat(form.credit_limit) || 0,
        branch_id: form.branch_id || undefined,
      };
      if (editId) await customersApi.update(editId, payload);
      else await customersApi.create(payload);
      navigate("/customers");
    } catch (err) {
      alert(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <PageLayout title="Loading..." breadcrumbs={["Home", "Customers"]}>
        <div className="h-64 animate-pulse rounded-2xl bg-muted" />
      </PageLayout>
    );
  }

  return (
    <PageLayout
      title={editId ? "Edit Customer" : "Add Customer"}
      description="Manage customer profile and credit settings."
      breadcrumbs={["Home", "Customers", editId ? "Edit" : "New"]}
    >
      <form onSubmit={handleSubmit}>
        <FormSection title="Customer Information">
          <FormGrid>
            <FormField label="Full Name" required>
              <Input required value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} />
            </FormField>
            <FormField label="Customer Type">
              <Select value={form.customer_type} onValueChange={(v) => setForm({ ...form, customer_type: v })}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="retail">Retail</SelectItem>
                  <SelectItem value="wholesale">Wholesale</SelectItem>
                  <SelectItem value="corporate">Corporate</SelectItem>
                </SelectContent>
              </Select>
            </FormField>
            <FormField label="Email"><Input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></FormField>
            <FormField label="Phone"><Input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} /></FormField>
            <FormField label="Credit Limit"><Input type="number" min="0" step="0.01" value={form.credit_limit} onChange={(e) => setForm({ ...form, credit_limit: e.target.value })} /></FormField>
            <FormField label="Branch">
              <Select value={form.branch_id || "none"} onValueChange={(v) => setForm({ ...form, branch_id: v === "none" ? "" : v })}>
                <SelectTrigger><SelectValue placeholder="Select branch" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">None</SelectItem>
                  {branches.map((b) => <SelectItem key={b.id} value={b.id}>{b.name}</SelectItem>)}
                </SelectContent>
              </Select>
            </FormField>
            <FormField label="Address" className="md:col-span-2">
              <Input value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} />
            </FormField>
          </FormGrid>
          <label className="mt-6 flex items-center gap-3 cursor-pointer">
            <Checkbox checked={form.is_active} onCheckedChange={(v) => setForm({ ...form, is_active: !!v })} />
            <span className="text-sm font-medium">Active customer</span>
          </label>
        </FormSection>
        <div className="mt-6 flex gap-3">
          <Button type="submit" loading={saving}>{editId ? "Save Changes" : "Create Customer"}</Button>
          <Button type="button" variant="secondary" onClick={() => navigate("/customers")}>Cancel</Button>
        </div>
      </form>
    </PageLayout>
  );
}
