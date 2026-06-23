import { useEffect, useState } from "react";
import { AlertTriangle, CreditCard, Pencil, Plus, RefreshCw } from "lucide-react";
import { PageLayout } from "@/components/layout/PageLayout";
import { DataTable, type Column } from "@/components/data/DataTable";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { FormSection } from "@/components/forms/FormField";
import {
  buildSubscriptionPayload,
  EMPTY_SUBSCRIPTION_FORM,
  SubscriptionEditModal,
  SubscriptionFormFields,
  useTenantUsers,
  type SubscriptionFormValues,
} from "@/components/platform/SubscriptionForm";
import {
  platformApi,
  type PlatformPlanRow,
  type PlatformSubscriptionRow,
  type PlatformTenantRow,
  type SubscriptionAlert,
} from "@/services/api/platform";
import { formatCurrency } from "@/utils/cn";

export function PlatformSubscriptionsPage() {
  const [subscriptions, setSubscriptions] = useState<PlatformSubscriptionRow[]>([]);
  const [shops, setShops] = useState<PlatformTenantRow[]>([]);
  const [alerts, setAlerts] = useState<SubscriptionAlert[]>([]);
  const [plans, setPlans] = useState<PlatformPlanRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState<SubscriptionFormValues>(EMPTY_SUBSCRIPTION_FORM);
  const [durationDays, setDurationDays] = useState("30");
  const [renewingId, setRenewingId] = useState<string | null>(null);
  const [editing, setEditing] = useState<PlatformSubscriptionRow | null>(null);
  const createUsers = useTenantUsers(form.tenant_id || undefined);

  const load = () => {
    setLoading(true);
    Promise.all([
      platformApi.subscriptions(),
      platformApi.tenants("month"),
      platformApi.subscriptionAlerts(),
      platformApi.plans(),
    ])
      .then(([subsRes, tenantsRes, alertsRes, plansRes]) => {
        setSubscriptions(subsRes.data);
        setShops(tenantsRes.data);
        setAlerts(alertsRes.data);
        setPlans(plansRes.data);
      })
      .catch(() => {
        setSubscriptions([]);
        setShops([]);
        setAlerts([]);
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, []);

  const createSubscription = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      await platformApi.createSubscription(buildSubscriptionPayload(form, durationDays));
      setShowForm(false);
      setForm(EMPTY_SUBSCRIPTION_FORM);
      load();
    } finally {
      setSaving(false);
    }
  };

  const renew = async (subscriptionId: string) => {
    setRenewingId(subscriptionId);
    try {
      await platformApi.renewSubscription(subscriptionId);
      load();
    } finally {
      setRenewingId(null);
    }
  };

  const columns: Column<PlatformSubscriptionRow>[] = [
    {
      key: "reference",
      header: "Reference",
      cell: (r) => <span className="font-mono text-sm">{r.reference_code}</span>,
    },
    {
      key: "shop",
      header: "Shop",
      cell: (r) => r.tenant_name ?? <span className="text-muted-foreground">Unassigned</span>,
    },
    {
      key: "contact",
      header: "Contact user",
      cell: (r) => r.contact_user?.full_name ?? "—",
    },
    { key: "plan", header: "Plan", cell: (r) => r.plan },
    {
      key: "status",
      header: "Status",
      cell: (r) => <Badge variant={r.is_usable ? "success" : "destructive"}>{r.status}</Badge>,
    },
    {
      key: "expires",
      header: "Expires",
      cell: (r) => r.expires_at ?? "—",
    },
    {
      key: "paid",
      header: "Payment",
      cell: (r) =>
        r.is_payment_current ? (
          <Badge variant="success">Paid</Badge>
        ) : (
          <Badge variant="destructive">Due</Badge>
        ),
    },
    {
      key: "price",
      header: "Monthly fee",
      cell: (r) => formatCurrency(r.monthly_fee),
    },
    {
      key: "actions",
      header: "Actions",
      cell: (r) => (
        <div className="flex flex-wrap gap-2">
          <Button size="sm" variant="secondary" onClick={() => setEditing(r)}>
            <Pencil className="h-3 w-3" />
            Edit
          </Button>
          {r.tenant_id && (
            <Button size="sm" loading={renewingId === r.id} onClick={() => renew(r.id)}>
              <CreditCard className="h-3 w-3" />
              Renew
            </Button>
          )}
        </div>
      ),
    },
  ];

  return (
    <PageLayout
      title="Platform — Subscriptions"
      description="Create and edit subscriptions, set custom fees, assign shops and users, and manage alert text."
      breadcrumbs={["Home", "Platform", "Subscriptions"]}
      actions={
        <div className="flex gap-2">
          <Button variant="secondary" size="sm" onClick={load}>
            <RefreshCw className="h-4 w-4" /> Refresh
          </Button>
          <Button size="sm" onClick={() => setShowForm((v) => !v)}>
            <Plus className="h-4 w-4" /> New Subscription
          </Button>
        </div>
      }
    >
      <SubscriptionEditModal
        subscription={editing}
        shops={shops}
        plans={plans}
        open={!!editing}
        onClose={() => setEditing(null)}
        onSaved={load}
      />

      {alerts.length > 0 && (
        <div className="mb-6 space-y-3">
          {alerts.map((alert) => (
            <div
              key={alert.subscription_id}
              className={`flex items-start gap-3 rounded-lg border p-4 ${
                alert.severity === "critical"
                  ? "border-destructive/50 bg-destructive/10"
                  : "border-amber-500/50 bg-amber-500/10"
              }`}
            >
              <AlertTriangle
                className={`mt-0.5 h-5 w-5 shrink-0 ${
                  alert.severity === "critical" ? "text-destructive" : "text-amber-600"
                }`}
              />
              <div>
                <p className="font-medium">{alert.title}</p>
                <p className="text-sm text-muted-foreground">{alert.tenant_name}</p>
                <p className="text-sm">{alert.message}</p>
                <p className="mt-1 text-xs text-muted-foreground">
                  {alert.reference_code} · ${alert.monthly_fee}/mo · expires {alert.expires_at}
                </p>
              </div>
            </div>
          ))}
        </div>
      )}

      {showForm && (
        <form onSubmit={createSubscription} className="mb-6">
          <FormSection title="New Subscription" description="Create a license, then assign it to a shop.">
            <SubscriptionFormFields
              form={form}
              setForm={setForm}
              plans={plans}
              shops={shops}
              users={createUsers}
              mode="create"
              showDuration
              durationDays={durationDays}
              setDurationDays={setDurationDays}
              onPlanCreated={(plan) => {
                setPlans((prev) => {
                  if (prev.some((p) => p.code === plan.code)) return prev;
                  return [...prev, plan].sort((a, b) => a.monthly_price - b.monthly_price);
                });
              }}
            />
            <div className="mt-4">
              <Button type="submit" loading={saving}>
                Create Subscription
              </Button>
            </div>
          </FormSection>
        </form>
      )}

      <DataTable
        exportTitle="Subscriptions"
        columns={columns}
        data={subscriptions}
        loading={loading}
        emptyMessage="No subscriptions yet. Create one and assign it to a shop."
        defaultPageSize={10}
      />
    </PageLayout>
  );
}
