import { useEffect, useState } from "react";
import { Plus } from "lucide-react";
import { FormField, FormGrid } from "@/components/forms/FormField";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import {
  ALERT_TEMPLATE_PLACEHOLDERS,
  platformApi,
  type PlatformPlanRow,
  type PlatformSubscriptionRow,
  type PlatformTenantRow,
  type PlatformUserOption,
} from "@/services/api/platform";

export interface SubscriptionFormValues {
  plan_code: string;
  status: string;
  tenant_id: string;
  contact_user_id: string;
  monthly_fee: string;
  started_at: string;
  expires_at: string;
  last_paid_at: string;
  billing_period_days: string;
  warning_days: string;
  grace_period_days: string;
  alert_title: string;
  alert_message_template: string;
  notes: string;
}

export function subscriptionToForm(sub: PlatformSubscriptionRow): SubscriptionFormValues {
  return {
    plan_code: sub.plan_code,
    status: sub.status,
    tenant_id: sub.tenant_id ?? "",
    contact_user_id: sub.contact_user?.id ?? "",
    monthly_fee: sub.custom_monthly_fee != null ? String(sub.custom_monthly_fee) : "",
    started_at: sub.started_at ?? "",
    expires_at: sub.expires_at ?? "",
    last_paid_at: sub.last_paid_at ?? "",
    billing_period_days: String(sub.billing_period_days),
    warning_days: String(sub.warning_days),
    grace_period_days: String(sub.grace_period_days),
    alert_title: sub.alert_title ?? "",
    alert_message_template: sub.alert_message_template ?? "",
    notes: sub.notes ?? "",
  };
}

export const EMPTY_SUBSCRIPTION_FORM: SubscriptionFormValues = {
  plan_code: "",
  status: "trial",
  tenant_id: "",
  contact_user_id: "",
  monthly_fee: "",
  started_at: "",
  expires_at: "",
  last_paid_at: "",
  billing_period_days: "30",
  warning_days: "5",
  grace_period_days: "5",
  alert_title: "",
  alert_message_template: "",
  notes: "",
};

interface SubscriptionFormProps {
  form: SubscriptionFormValues;
  setForm: (v: SubscriptionFormValues) => void;
  plans: PlatformPlanRow[];
  shops: PlatformTenantRow[];
  users: PlatformUserOption[];
  mode: "create" | "edit";
  showDuration?: boolean;
  durationDays?: string;
  setDurationDays?: (v: string) => void;
  onPlanCreated?: (plan: PlatformPlanRow) => void;
}

export function PlanCreateInline({ onCreated }: { onCreated: (plan: PlatformPlanRow) => void }) {
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [planForm, setPlanForm] = useState({
    name: "",
    code: "",
    monthly_price: "",
    max_users: "10",
    max_branches: "3",
    description: "",
  });

  const create = async () => {
    if (!planForm.name.trim()) return;
    setSaving(true);
    try {
      const res = await platformApi.createPlan({
        name: planForm.name.trim(),
        code: planForm.code.trim() || undefined,
        monthly_price: Number(planForm.monthly_price) || 0,
        max_users: Number(planForm.max_users) || 10,
        max_branches: Number(planForm.max_branches) || 3,
        description: planForm.description.trim(),
      });
      onCreated(res.data);
      setPlanForm({ name: "", code: "", monthly_price: "", max_users: "10", max_branches: "3", description: "" });
      setOpen(false);
    } catch (err) {
      alert(err instanceof Error ? err.message : "Could not create plan.");
    } finally {
      setSaving(false);
    }
  };

  if (!open) {
    return (
      <Button type="button" variant="secondary" size="sm" onClick={() => setOpen(true)}>
        <Plus className="h-4 w-4" />
        New plan
      </Button>
    );
  }

  return (
    <div className="rounded-lg border border-border bg-muted/30 p-4 md:col-span-2">
      <p className="mb-3 text-sm font-medium">Create subscription plan</p>
      <FormGrid>
        <FormField label="Plan name" required>
          <Input
            value={planForm.name}
            onChange={(e) => setPlanForm({ ...planForm, name: e.target.value })}
            placeholder="e.g. Futsal + Cafeteria"
          />
        </FormField>
        <FormField label="Code" hint="Auto-generated from name if empty.">
          <Input
            value={planForm.code}
            onChange={(e) => setPlanForm({ ...planForm, code: e.target.value })}
            placeholder="futsal-cafeteria"
          />
        </FormField>
        <FormField label="Default monthly price ($)">
          <Input
            type="number"
            min={0}
            step="0.01"
            value={planForm.monthly_price}
            onChange={(e) => setPlanForm({ ...planForm, monthly_price: e.target.value })}
          />
        </FormField>
        <FormField label="Max users">
          <Input
            type="number"
            min={1}
            value={planForm.max_users}
            onChange={(e) => setPlanForm({ ...planForm, max_users: e.target.value })}
          />
        </FormField>
        <FormField label="Max branches">
          <Input
            type="number"
            min={1}
            value={planForm.max_branches}
            onChange={(e) => setPlanForm({ ...planForm, max_branches: e.target.value })}
          />
        </FormField>
        <FormField label="Description" className="md:col-span-2">
          <Input
            value={planForm.description}
            onChange={(e) => setPlanForm({ ...planForm, description: e.target.value })}
          />
        </FormField>
      </FormGrid>
      <div className="mt-3 flex gap-2">
        <Button type="button" loading={saving} onClick={create}>
          Save plan
        </Button>
        <Button type="button" variant="secondary" onClick={() => setOpen(false)}>
          Cancel
        </Button>
      </div>
    </div>
  );
}

export function SubscriptionFormFields({
  form,
  setForm,
  plans,
  shops,
  users,
  mode,
  showDuration,
  durationDays,
  setDurationDays,
  onPlanCreated,
}: SubscriptionFormProps) {
  const shopsForAssign = shops.filter((s) => !s.subscription || s.id === form.tenant_id);

  return (
    <FormGrid>
      <FormField label="Plan" required className="md:col-span-2">
        <div className="flex flex-wrap items-start gap-2">
          <div className="min-w-[220px] flex-1">
            <Select
              value={form.plan_code || undefined}
              onValueChange={(v) => setForm({ ...form, plan_code: v })}
            >
              <SelectTrigger>
                <SelectValue placeholder={plans.length ? "Select plan" : "No plans — create one"} />
              </SelectTrigger>
              <SelectContent>
                {plans.map((plan) => (
                  <SelectItem key={plan.code} value={plan.code}>
                    {plan.name} (default ${plan.monthly_price}/mo)
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          {onPlanCreated && (
            <PlanCreateInline
              onCreated={(plan) => {
                onPlanCreated(plan);
                setForm({ ...form, plan_code: plan.code });
              }}
            />
          )}
        </div>
      </FormField>
      <FormField label="Monthly fee ($)" hint="Leave empty to use the plan default price.">
        <Input
          type="number"
          min={0}
          step="0.01"
          value={form.monthly_fee}
          onChange={(e) => setForm({ ...form, monthly_fee: e.target.value })}
          placeholder="Custom amount"
        />
      </FormField>
      <FormField label="Status">
        <Select value={form.status} onValueChange={(v) => setForm({ ...form, status: v })}>
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="trial">Trial</SelectItem>
            <SelectItem value="active">Active</SelectItem>
            <SelectItem value="expired">Expired</SelectItem>
            <SelectItem value="suspended">Suspended</SelectItem>
          </SelectContent>
        </Select>
      </FormField>
      <FormField label="Assigned shop">
        <Select
          value={form.tenant_id || "none"}
          onValueChange={(v) =>
            setForm({ ...form, tenant_id: v === "none" ? "" : v, contact_user_id: "" })
          }
        >
          <SelectTrigger>
            <SelectValue placeholder="Unassigned" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="none">Unassigned</SelectItem>
            {shopsForAssign.map((shop) => (
              <SelectItem key={shop.id} value={shop.id}>
                {shop.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </FormField>
      <FormField label="Contact user" hint="User who receives the payment alert for this shop.">
        <Select
          value={form.contact_user_id || "none"}
          onValueChange={(v) => setForm({ ...form, contact_user_id: v === "none" ? "" : v })}
          disabled={!form.tenant_id}
        >
          <SelectTrigger>
            <SelectValue placeholder={form.tenant_id ? "Select user" : "Assign a shop first"} />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="none">None (all shop users)</SelectItem>
            {users.map((u) => (
              <SelectItem key={u.id} value={u.id}>
                {u.full_name} ({u.username})
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </FormField>
      {showDuration && setDurationDays && (
        <FormField label="Initial duration (days)">
          <Input
            type="number"
            min={1}
            value={durationDays}
            onChange={(e) => setDurationDays(e.target.value)}
          />
        </FormField>
      )}
      {mode === "edit" && (
        <>
          <FormField label="Started">
            <Input
              type="date"
              value={form.started_at}
              onChange={(e) => setForm({ ...form, started_at: e.target.value })}
            />
          </FormField>
          <FormField label="Expires">
            <Input
              type="date"
              value={form.expires_at}
              onChange={(e) => setForm({ ...form, expires_at: e.target.value })}
            />
          </FormField>
          <FormField label="Last paid">
            <Input
              type="date"
              value={form.last_paid_at}
              onChange={(e) => setForm({ ...form, last_paid_at: e.target.value })}
            />
          </FormField>
        </>
      )}
      <FormField label="Billing period (days)">
        <Input
          type="number"
          min={1}
          value={form.billing_period_days}
          onChange={(e) => setForm({ ...form, billing_period_days: e.target.value })}
        />
      </FormField>
      <FormField label="Warning days">
        <Input
          type="number"
          min={1}
          value={form.warning_days}
          onChange={(e) => setForm({ ...form, warning_days: e.target.value })}
        />
      </FormField>
      <FormField label="Extension days">
        <Input
          type="number"
          min={0}
          value={form.grace_period_days}
          onChange={(e) => setForm({ ...form, grace_period_days: e.target.value })}
        />
      </FormField>
      <FormField label="Alert title" hint="Shown at the top of the payment alert dialog.">
        <Input
          value={form.alert_title}
          onChange={(e) => setForm({ ...form, alert_title: e.target.value })}
          placeholder="Subscription Payment Required"
        />
      </FormField>
      <FormField
        label="Alert message"
        className="md:col-span-2"
        hint={`Use placeholders: ${ALERT_TEMPLATE_PLACEHOLDERS}`}
      >
        <textarea
          className="flex min-h-[100px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
          value={form.alert_message_template}
          onChange={(e) => setForm({ ...form, alert_message_template: e.target.value })}
          placeholder="Payment due for {shop_name}. {days_left} days left. Monthly fee: ${monthly_fee}."
        />
      </FormField>
      <FormField label="Notes" className="md:col-span-2">
        <Input value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
      </FormField>
    </FormGrid>
  );
}

export function useTenantUsers(tenantId: string | undefined) {
  const [users, setUsers] = useState<PlatformUserOption[]>([]);
  useEffect(() => {
    if (!tenantId) {
      setUsers([]);
      return;
    }
    platformApi.tenantUsers(tenantId).then((res) => setUsers(res.data)).catch(() => setUsers([]));
  }, [tenantId]);
  return users;
}

export function buildSubscriptionPayload(
  form: SubscriptionFormValues,
  durationDays?: string
): Record<string, unknown> {
  const payload: Record<string, unknown> = {
    plan_code: form.plan_code,
    status: form.status,
    billing_period_days: Number(form.billing_period_days) || 30,
    warning_days: Number(form.warning_days) || 5,
    grace_period_days: Number(form.grace_period_days) || 5,
    alert_title: form.alert_title,
    alert_message_template: form.alert_message_template,
    notes: form.notes,
    tenant_id: form.tenant_id || null,
    contact_user_id: form.contact_user_id || null,
  };
  if (form.monthly_fee !== "") {
    payload.monthly_fee = Number(form.monthly_fee);
  } else {
    payload.monthly_fee = null;
  }
  if (form.started_at) payload.started_at = form.started_at;
  if (form.expires_at) payload.expires_at = form.expires_at;
  if (form.last_paid_at) payload.last_paid_at = form.last_paid_at;
  if (durationDays) payload.duration_days = Number(durationDays) || 30;
  return payload;
}

interface SubscriptionEditModalProps {
  subscription: PlatformSubscriptionRow | null;
  shops: PlatformTenantRow[];
  plans: PlatformPlanRow[];
  open: boolean;
  onClose: () => void;
  onSaved: () => void;
}

export function SubscriptionEditModal({
  subscription,
  shops,
  plans,
  open,
  onClose,
  onSaved,
}: SubscriptionEditModalProps) {
  const [form, setForm] = useState<SubscriptionFormValues>(EMPTY_SUBSCRIPTION_FORM);
  const [saving, setSaving] = useState(false);
  const users = useTenantUsers(form.tenant_id || undefined);

  useEffect(() => {
    if (subscription && open) {
      setForm(subscriptionToForm(subscription));
    }
  }, [subscription, open]);

  if (!open || !subscription) return null;

  const save = async () => {
    setSaving(true);
    try {
      await platformApi.updateSubscriptionRecord(subscription.id, buildSubscriptionPayload(form));
      onSaved();
      onClose();
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[90] flex items-center justify-center bg-black/50 p-4">
      <div className="max-h-[90vh] w-full max-w-3xl overflow-y-auto rounded-xl border border-border bg-card p-6 shadow-xl">
        <h2 className="text-lg font-semibold">Edit Subscription — {subscription.reference_code}</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Update plan, fee, shop assignment, contact user, and alert text.
        </p>
        <div className="mt-6">
          <SubscriptionFormFields
            form={form}
            setForm={setForm}
            plans={plans}
            shops={shops}
            users={users}
            mode="edit"
          />
        </div>
        <div className="mt-6 flex justify-end gap-2">
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button loading={saving} onClick={save}>
            Save Changes
          </Button>
        </div>
      </div>
    </div>
  );
}
