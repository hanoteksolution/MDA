import { useCallback, useEffect, useState } from "react";
import { PageLayout } from "@/components/layout/PageLayout";
import { ContentSection } from "@/components/layout/ContentSection";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { FormField, FormGrid } from "@/components/forms/FormField";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useAuthStore } from "@/store/authStore";
import { restaurantApi, type CafeteriaProfile } from "@/services/api/restaurant";

export function CafeteriaSettingsPage() {
  const branchId = useAuthStore((s) => s.user?.branch?.id);
  const [form, setForm] = useState<Partial<CafeteriaProfile>>({
    business_name: "",
    trading_name: "",
    currency: "USD",
    timezone: "UTC",
    language: "en",
    order_prefix: "CF",
    invoice_prefix: "INV-CF",
    kitchen_barista_mode: "both",
    table_service_enabled: true,
    takeaway_enabled: true,
    delivery_enabled: false,
    tips_enabled: true,
    recipe_deduction_enabled: true,
    negative_stock_allowed: false,
    receipt_header: "",
    receipt_footer: "",
  });
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!branchId) return;
    const res = await restaurantApi.cafeteriaProfile(branchId);
    if (res.data) setForm(res.data);
    else setForm((f) => ({ ...f, business_name: "Cafeteria" }));
  }, [branchId]);

  useEffect(() => {
    void load();
  }, [load]);

  const save = async () => {
    if (!branchId) return;
    setSaving(true);
    setMessage(null);
    try {
      await restaurantApi.saveCafeteriaProfile({ ...form, branch_id: branchId });
      setMessage("Profile saved.");
      await load();
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "Save failed");
    } finally {
      setSaving(false);
    }
  };

  const set = (key: keyof CafeteriaProfile, value: string | boolean) =>
    setForm((f) => ({ ...f, [key]: value }));

  return (
    <PageLayout
      title="Cafeteria Settings"
      description="Workspace profile, order prefixes, and café feature toggles."
      actions={
        <Button onClick={() => void save()} disabled={saving}>
          {saving ? "Saving…" : "Save changes"}
        </Button>
      }
    >
      {message ? <p className="mb-4 text-sm text-muted-foreground">{message}</p> : null}
      <ContentSection title="Identity">
        <FormGrid>
          <FormField label="Business name" required>
            <Input
              value={form.business_name || ""}
              onChange={(e) => set("business_name", e.target.value)}
            />
          </FormField>
          <FormField label="Trading name">
            <Input
              value={form.trading_name || ""}
              onChange={(e) => set("trading_name", e.target.value)}
            />
          </FormField>
          <FormField label="Currency">
            <Input value={form.currency || ""} onChange={(e) => set("currency", e.target.value)} />
          </FormField>
          <FormField label="Timezone">
            <Input value={form.timezone || ""} onChange={(e) => set("timezone", e.target.value)} />
          </FormField>
          <FormField label="Order prefix">
            <Input
              value={form.order_prefix || ""}
              onChange={(e) => set("order_prefix", e.target.value)}
            />
          </FormField>
          <FormField label="Invoice prefix">
            <Input
              value={form.invoice_prefix || ""}
              onChange={(e) => set("invoice_prefix", e.target.value)}
            />
          </FormField>
          <FormField label="Kitchen / barista mode">
            <Select
              value={form.kitchen_barista_mode || "both"}
              onValueChange={(v) => set("kitchen_barista_mode", v)}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="both">Both</SelectItem>
                <SelectItem value="barista">Barista only</SelectItem>
                <SelectItem value="kitchen">Kitchen only</SelectItem>
              </SelectContent>
            </Select>
          </FormField>
        </FormGrid>
      </ContentSection>

      <ContentSection title="Features">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {(
            [
              ["table_service_enabled", "Table service"],
              ["takeaway_enabled", "Takeaway"],
              ["delivery_enabled", "Delivery"],
              ["tips_enabled", "Tips"],
              ["recipe_deduction_enabled", "Recipe stock deduction"],
              ["negative_stock_allowed", "Allow negative stock"],
            ] as const
          ).map(([key, label]) => (
            <label key={key} className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={Boolean(form[key])}
                onChange={(e) => set(key, e.target.checked)}
              />
              {label}
            </label>
          ))}
        </div>
      </ContentSection>

      <ContentSection title="Receipts">
        <FormGrid>
          <FormField label="Receipt header">
            <Input
              value={form.receipt_header || ""}
              onChange={(e) => set("receipt_header", e.target.value)}
            />
          </FormField>
          <FormField label="Receipt footer">
            <Input
              value={form.receipt_footer || ""}
              onChange={(e) => set("receipt_footer", e.target.value)}
            />
          </FormField>
        </FormGrid>
      </ContentSection>
    </PageLayout>
  );
}
