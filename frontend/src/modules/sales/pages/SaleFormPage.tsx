import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Plus, Trash2 } from "lucide-react";
import { PageLayout } from "@/components/layout/PageLayout";
import { FormField, FormSection, FormGrid } from "@/components/forms/FormField";
import { FormPageLayout, FormActions } from "@/components/forms/FormPageLayout";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { salesApi } from "@/services/api/sales";
import { customersApi } from "@/services/api/partners";
import { productsApi } from "@/services/api/catalog";
import { settingsApi } from "@/services/api/admin";
import { formatCurrency } from "@/utils/cn";
import type { Product } from "@/types/models/catalog";

interface LineItem {
  product_id: string;
  quantity: string;
  unit_price: string;
}

interface SaleFormPageProps {
  type: "invoice" | "quotation";
  editId?: string;
}

export function SaleFormPage({ type, editId }: SaleFormPageProps) {
  const navigate = useNavigate();
  const isInvoice = type === "invoice";
  const [loading, setLoading] = useState(!!editId);
  const [saving, setSaving] = useState(false);
  const [customers, setCustomers] = useState<{ id: string; full_name: string }[]>([]);
  const [branches, setBranches] = useState<{ id: string; name: string }[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [form, setForm] = useState({
    customer_id: "", branch_id: "", status: "draft",
    due_date: "", valid_until: "", notes: "",
  });
  const [items, setItems] = useState<LineItem[]>([{ product_id: "", quantity: "1", unit_price: "0" }]);

  useEffect(() => {
    Promise.all([
      customersApi.list({ page_size: 100 }),
      settingsApi.branches(),
      productsApi.list({ page_size: 100 }),
    ]).then(([cust, br, prod]) => {
      setCustomers(cust.data.results);
      setBranches(br.data);
      setProducts(prod.data.results);
      if (cust.data.results.length) setForm((f) => ({ ...f, customer_id: f.customer_id || cust.data.results[0].id }));
      if (br.data.length) setForm((f) => ({ ...f, branch_id: f.branch_id || br.data[0].id }));
    });
  }, []);

  useEffect(() => {
    if (!editId) return;
    const fetcher = isInvoice ? salesApi.getInvoice : salesApi.getQuotation;
    fetcher(editId).then((res) => {
      const doc = res.data;
      setForm({
        customer_id: doc.customer_id,
        branch_id: doc.branch_id,
        status: doc.status,
        due_date: isInvoice && "due_date" in doc ? (doc.due_date || "") : "",
        valid_until: !isInvoice && "valid_until" in doc ? (doc.valid_until || "") : "",
        notes: doc.notes,
      });
      if (doc.items?.length) {
        setItems(doc.items.map((i) => ({
          product_id: i.product_id,
          quantity: String(i.quantity),
          unit_price: String(i.unit_price),
        })));
      }
      setLoading(false);
    });
  }, [editId, isInvoice]);

  const addLine = () => setItems([...items, { product_id: "", quantity: "1", unit_price: "0" }]);
  const removeLine = (idx: number) => setItems(items.filter((_, i) => i !== idx));
  const updateLine = (idx: number, patch: Partial<LineItem>) => {
    setItems(items.map((item, i) => (i === idx ? { ...item, ...patch } : item)));
  };
  const onProductSelect = (idx: number, productId: string) => {
    const product = products.find((p) => p.id === productId);
    updateLine(idx, { product_id: productId, unit_price: product ? String(product.selling_price) : "0" });
  };

  const lineTotal = items.reduce((s, i) => s + (parseFloat(i.quantity) || 0) * (parseFloat(i.unit_price) || 0), 0);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      const payload = {
        customer_id: form.customer_id,
        branch_id: form.branch_id,
        status: form.status,
        notes: form.notes,
        ...(isInvoice
          ? { due_date: form.due_date || undefined, issue_date: new Date().toISOString().slice(0, 10) }
          : { valid_until: form.valid_until || undefined }),
        items: items.filter((i) => i.product_id).map((i) => ({
          product_id: i.product_id,
          quantity: parseFloat(i.quantity),
          unit_price: parseFloat(i.unit_price),
        })),
      };
      if (editId) {
        if (isInvoice) await salesApi.updateInvoice(editId, payload);
        else await salesApi.updateQuotation(editId, payload);
      } else {
        if (isInvoice) await salesApi.createInvoice(payload);
        else await salesApi.createQuotation(payload);
      }
      navigate("/sales");
    } catch (err) {
      alert(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <PageLayout title="Loading..." breadcrumbs={["Home", "Sales"]}>
        <div className="h-64 animate-pulse rounded-2xl bg-muted" />
      </PageLayout>
    );
  }

  const title = editId
    ? (isInvoice ? "Edit Invoice" : "Edit Quotation")
    : (isInvoice ? "New Invoice" : "New Quotation");

  const statusOptions = isInvoice
    ? ["draft", "sent", "paid", "overdue", "cancelled"]
    : ["draft", "sent", "accepted", "rejected", "expired", "cancelled"];

  return (
    <PageLayout
      title={title}
      description={isInvoice ? "Create a customer invoice with line items." : "Create a quotation for a customer."}
      breadcrumbs={["Home", "Sales", editId ? "Edit" : "New"]}
    >
      <form onSubmit={handleSubmit}>
        <FormPageLayout
          main={
            <>
              <FormSection title="Document Details">
                <FormGrid>
                  <FormField label="Customer" required>
                    <Select value={form.customer_id} onValueChange={(v) => setForm({ ...form, customer_id: v })}>
                      <SelectTrigger><SelectValue placeholder="Select customer" /></SelectTrigger>
                      <SelectContent>
                        {customers.map((c) => (
                          <SelectItem key={c.id} value={c.id}>{c.full_name}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </FormField>
                  <FormField label="Branch" required>
                    <Select value={form.branch_id} onValueChange={(v) => setForm({ ...form, branch_id: v })}>
                      <SelectTrigger><SelectValue placeholder="Select branch" /></SelectTrigger>
                      <SelectContent>
                        {branches.map((b) => (
                          <SelectItem key={b.id} value={b.id}>{b.name}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </FormField>
                  <FormField label="Status">
                    <Select value={form.status} onValueChange={(v) => setForm({ ...form, status: v })}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        {statusOptions.map((s) => (
                          <SelectItem key={s} value={s} className="capitalize">{s}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </FormField>
                  {isInvoice ? (
                    <FormField label="Due Date">
                      <Input type="date" value={form.due_date} onChange={(e) => setForm({ ...form, due_date: e.target.value })} />
                    </FormField>
                  ) : (
                    <FormField label="Valid Until">
                      <Input type="date" value={form.valid_until} onChange={(e) => setForm({ ...form, valid_until: e.target.value })} />
                    </FormField>
                  )}
                  <FormField label="Notes" className="md:col-span-2">
                    <Input value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} placeholder="Optional notes..." />
                  </FormField>
                </FormGrid>
              </FormSection>

              <FormSection title="Line Items">
                <div className="space-y-3">
                  {items.map((item, idx) => (
                    <div key={idx} className="grid grid-cols-1 gap-3 rounded-xl border border-border p-4 md:grid-cols-12 md:items-end">
                      <FormField label="Product" className="md:col-span-5">
                        <Select value={item.product_id} onValueChange={(v) => onProductSelect(idx, v)}>
                          <SelectTrigger><SelectValue placeholder="Select product" /></SelectTrigger>
                          <SelectContent>
                            {products.map((p) => (
                              <SelectItem key={p.id} value={p.id}>{p.name} ({p.sku})</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </FormField>
                      <FormField label="Qty" className="md:col-span-2">
                        <Input type="number" min="0.01" step="0.01" value={item.quantity}
                          onChange={(e) => updateLine(idx, { quantity: e.target.value })} />
                      </FormField>
                      <FormField label="Unit Price" className="md:col-span-2">
                        <Input type="number" min="0" step="0.01" value={item.unit_price}
                          onChange={(e) => updateLine(idx, { unit_price: e.target.value })} />
                      </FormField>
                      <div className="md:col-span-2 text-sm font-semibold pb-2">
                        {formatCurrency((parseFloat(item.quantity) || 0) * (parseFloat(item.unit_price) || 0))}
                      </div>
                      <div className="md:col-span-1 flex justify-end pb-1">
                        {items.length > 1 && (
                          <Button type="button" variant="ghost" size="sm" onClick={() => removeLine(idx)}>
                            <Trash2 className="h-4 w-4 text-destructive" />
                          </Button>
                        )}
                      </div>
                    </div>
                  ))}
                  <Button type="button" variant="secondary" size="sm" onClick={addLine}>
                    <Plus className="h-4 w-4" /> Add Line
                  </Button>
                </div>
              </FormSection>
            </>
          }
          aside={
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-base">{isInvoice ? "Invoice" : "Quotation"} Summary</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex justify-between text-lg font-bold">
                  <span>Total</span>
                  <span className="text-primary">{formatCurrency(lineTotal)}</span>
                </div>
              </CardContent>
            </Card>
          }
          actions={
            <FormActions>
              <Button type="submit" loading={saving}>
                {editId ? "Save Changes" : (isInvoice ? "Create Invoice" : "Create Quotation")}
              </Button>
              <Button type="button" variant="secondary" onClick={() => navigate("/sales")}>Cancel</Button>
            </FormActions>
          }
        />
      </form>
    </PageLayout>
  );
}

export function InvoiceFormPage({ editId }: { editId?: string }) {
  return <SaleFormPage type="invoice" editId={editId} />;
}

export function QuotationFormPage({ editId }: { editId?: string }) {
  return <SaleFormPage type="quotation" editId={editId} />;
}
