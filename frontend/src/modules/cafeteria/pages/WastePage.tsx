import { useCallback, useEffect, useState } from "react";
import { PageLayout } from "@/components/layout/PageLayout";
import { ContentSection } from "@/components/layout/ContentSection";
import { DataTable, type Column } from "@/components/data/DataTable";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { FormField, FormGrid } from "@/components/forms/FormField";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { useAuthStore } from "@/store/authStore";
import { restaurantApi } from "@/services/api/restaurant";
import { formatCurrency } from "@/utils/cn";

type WasteRow = {
  id: string;
  waste_date: string;
  waste_type: string;
  ingredient_name: string;
  quantity: number;
  unit: string;
  total_cost: number;
  approval_status: string;
  reason: string;
};

const WASTE_TYPES = [
  "expired",
  "spoiled",
  "prep",
  "spillage",
  "burned",
  "damaged",
  "employee_meal",
  "sample",
  "other",
];

export function WastePage() {
  const branchId = useAuthStore((s) => s.user?.branch?.id);
  const [rows, setRows] = useState<WasteRow[]>([]);
  const [ingredients, setIngredients] = useState<{ id: string; name: string }[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({
    ingredient_id: "",
    quantity: "1",
    waste_type: "spoiled",
    reason: "",
    unit_cost: "",
    auto_approve: true,
  });

  const reload = useCallback(async () => {
    if (!branchId) return;
    setLoading(true);
    try {
      const [wasteRes, ingRes] = await Promise.all([
        restaurantApi.wasteList(1, branchId),
        restaurantApi.ingredients(1, branchId),
      ]);
      setRows((wasteRes.data.results || []) as unknown as WasteRow[]);
      setIngredients(
        (ingRes.data.results || []).map((i: { id: string; name: string }) => ({
          id: i.id,
          name: i.name,
        }))
      );
    } finally {
      setLoading(false);
    }
  }, [branchId]);

  useEffect(() => {
    void reload();
  }, [reload]);

  const create = async () => {
    if (!branchId || !form.ingredient_id) return;
    setSaving(true);
    try {
      await restaurantApi.createWaste({
        branch_id: branchId,
        ingredient_id: form.ingredient_id,
        quantity: form.quantity,
        waste_type: form.waste_type,
        reason: form.reason,
        unit_cost: form.unit_cost || undefined,
        auto_approve: form.auto_approve,
      });
      setForm({
        ingredient_id: "",
        quantity: "1",
        waste_type: "spoiled",
        reason: "",
        unit_cost: "",
        auto_approve: true,
      });
      await reload();
    } finally {
      setSaving(false);
    }
  };

  const approve = async (id: string) => {
    await restaurantApi.approveWaste(id);
    await reload();
  };

  const columns: Column<WasteRow>[] = [
    { key: "waste_date", header: "Date", cell: (r) => r.waste_date || "—" },
    { key: "waste_type", header: "Type", cell: (r) => r.waste_type },
    { key: "ingredient_name", header: "Ingredient", cell: (r) => r.ingredient_name || "—" },
    {
      key: "quantity",
      header: "Qty",
      cell: (r) => `${r.quantity} ${r.unit || ""}`,
    },
    {
      key: "total_cost",
      header: "Cost",
      cell: (r) => formatCurrency(r.total_cost || 0),
    },
    {
      key: "approval_status",
      header: "Status",
      cell: (r) => <Badge variant="secondary">{r.approval_status}</Badge>,
    },
    {
      key: "id",
      header: "",
      cell: (r) =>
        r.approval_status === "draft" ? (
          <Button size="sm" variant="outline" onClick={() => void approve(r.id)}>
            Approve
          </Button>
        ) : (
          "—"
        ),
    },
  ];

  return (
    <PageLayout
      title="Waste / Spoilage"
      description="Record prep loss, expiry, and spillage. Approval posts stock and accounting."
    >
      <ContentSection title="Record waste">
        <FormGrid>
          <FormField label="Ingredient" required>
            <Select
              value={form.ingredient_id}
              onValueChange={(v) => setForm((f) => ({ ...f, ingredient_id: v }))}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select ingredient" />
              </SelectTrigger>
              <SelectContent>
                {ingredients.map((i) => (
                  <SelectItem key={i.id} value={i.id}>
                    {i.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </FormField>
          <FormField label="Type">
            <Select
              value={form.waste_type}
              onValueChange={(v) => setForm((f) => ({ ...f, waste_type: v }))}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {WASTE_TYPES.map((t) => (
                  <SelectItem key={t} value={t}>
                    {t}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </FormField>
          <FormField label="Quantity" required>
            <Input
              value={form.quantity}
              onChange={(e) => setForm((f) => ({ ...f, quantity: e.target.value }))}
            />
          </FormField>
          <FormField label="Unit cost (optional)">
            <Input
              value={form.unit_cost}
              onChange={(e) => setForm((f) => ({ ...f, unit_cost: e.target.value }))}
            />
          </FormField>
          <FormField label="Reason">
            <Input
              value={form.reason}
              onChange={(e) => setForm((f) => ({ ...f, reason: e.target.value }))}
            />
          </FormField>
        </FormGrid>
        <label className="mt-3 flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={form.auto_approve}
            onChange={(e) => setForm((f) => ({ ...f, auto_approve: e.target.checked }))}
          />
          Approve and post stock immediately
        </label>
        <div className="mt-4">
          <Button onClick={() => void create()} disabled={saving || !form.ingredient_id}>
            {saving ? "Saving…" : "Save waste"}
          </Button>
        </div>
      </ContentSection>

      <ContentSection title="Waste log">
        <DataTable columns={columns} data={rows} loading={loading} emptyMessage="No waste recorded." />
      </ContentSection>
    </PageLayout>
  );
}
