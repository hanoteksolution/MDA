import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import {
  AlertTriangle,
  CheckCircle2,
  CreditCard,
  Pencil,
  Plus,
  QrCode,
  RefreshCw,
  Trash2,
  Upload,
} from "lucide-react";
import { Link } from "react-router-dom";
import { PageLayout } from "@/components/layout/PageLayout";
import { DataTable, type Column } from "@/components/data/DataTable";
import { KpiCard, KpiGrid } from "@/components/data/KpiCard";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { FormField, FormSection } from "@/components/forms/FormField";
import { PlatformConfirmDialog } from "@/components/platform/PlatformConfirmDialog";
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
  type SubscriptionPaymentConfig,
  type SubscriptionPaymentRow,
} from "@/services/api/platform";
import { formatCurrency } from "@/utils/cn";
import { appDialog } from "@/components/feedback/AppDialog";
import { resolveMediaUrl } from "@/config/api";

const EMPTY_PAYMENT_CONFIG: SubscriptionPaymentConfig = {
  company_name: "SAFARI TECHNOLOGY SOLUTIONS",
  merchant_number: "608833",
  ussd_template: "*789*{merchant}*{amount}#",
  qr_image_url: "",
  qr_payload_template: "tel:*789*{merchant}*{amount}%23",
  provider_label: "Waafi / EVC Plus",
  instructions_title: "Pay with Waafi or EVC Plus",
  instructions: [
    "Scan the QR code — your phone dials *789*merchant*amount# automatically",
    "Confirm the USSD payment in Waafi / EVC Plus",
    "Or dial the USSD code shown below manually",
  ],
  contact_phone: "Call 141 | 101",
  dialog_title_override: "",
  dialog_message_override: "",
  auto_renew_enabled: true,
};

export function PlatformSubscriptionsPage() {
  const [subscriptions, setSubscriptions] = useState<PlatformSubscriptionRow[]>([]);
  const [shops, setShops] = useState<PlatformTenantRow[]>([]);
  const [alerts, setAlerts] = useState<SubscriptionAlert[]>([]);
  const [plans, setPlans] = useState<PlatformPlanRow[]>([]);
  const [pendingPayments, setPendingPayments] = useState<SubscriptionPaymentRow[]>([]);
  const [paymentConfig, setPaymentConfig] = useState<SubscriptionPaymentConfig>(EMPTY_PAYMENT_CONFIG);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [showPaymentSettings, setShowPaymentSettings] = useState(false);
  const [saving, setSaving] = useState(false);
  const [savingPayment, setSavingPayment] = useState(false);
  const [uploadingQr, setUploadingQr] = useState(false);
  const [confirmingId, setConfirmingId] = useState<string | null>(null);
  const [form, setForm] = useState<SubscriptionFormValues>(EMPTY_SUBSCRIPTION_FORM);
  const [durationDays, setDurationDays] = useState("30");
  const [renewingId, setRenewingId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [pendingDelete, setPendingDelete] = useState<PlatformSubscriptionRow | null>(null);
  const [editing, setEditing] = useState<PlatformSubscriptionRow | null>(null);
  const createUsers = useTenantUsers(form.tenant_id || undefined);

  const load = () => {
    setLoading(true);
    Promise.all([
      platformApi.subscriptions(),
      platformApi.tenants("month"),
      platformApi.subscriptionAlerts(),
      platformApi.plans(),
      platformApi.getSubscriptionPaymentConfig().catch(() => null),
      platformApi.pendingSubscriptionPayments().catch(() => null),
    ])
      .then(([subsRes, tenantsRes, alertsRes, plansRes, payCfgRes, pendingRes]) => {
        setSubscriptions(subsRes.data);
        setShops(tenantsRes.data);
        setAlerts(alertsRes.data);
        setPlans(plansRes.data);
        if (payCfgRes?.data) setPaymentConfig({ ...EMPTY_PAYMENT_CONFIG, ...payCfgRes.data });
        setPendingPayments(pendingRes?.data ?? []);
      })
      .catch(() => {
        setSubscriptions([]);
        setShops([]);
        setAlerts([]);
        setPendingPayments([]);
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, []);

  const stats = useMemo(() => {
    const due = subscriptions.filter((s) => !s.is_payment_current).length;
    const unassigned = subscriptions.filter((s) => !s.tenant_id).length;
    const mrr = subscriptions.reduce((sum, s) => sum + (s.monthly_fee || 0), 0);
    return {
      total: subscriptions.length,
      due,
      unassigned,
      mrr,
      alerts: alerts.length,
      pending: pendingPayments.length,
    };
  }, [subscriptions, alerts, pendingPayments]);

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

  const confirmDelete = async () => {
    if (!pendingDelete) return;
    setDeletingId(pendingDelete.id);
    try {
      await platformApi.deleteSubscription(pendingDelete.id);
      setPendingDelete(null);
      load();
    } catch (err) {
      await appDialog.alert(err instanceof Error ? err.message : "Could not delete subscription.");
    } finally {
      setDeletingId(null);
    }
  };

  const savePaymentConfig = async (e: React.FormEvent) => {
    e.preventDefault();
    setSavingPayment(true);
    try {
      const res = await platformApi.saveSubscriptionPaymentConfig({
        ...paymentConfig,
        instructions: Array.isArray(paymentConfig.instructions)
          ? paymentConfig.instructions
          : String(paymentConfig.instructions || "")
              .split("\n")
              .map((l) => l.trim())
              .filter(Boolean),
      });
      setPaymentConfig({ ...EMPTY_PAYMENT_CONFIG, ...res.data });
      await appDialog.alert("Payment & alert dialog settings saved.", {
        title: "Saved",
        tone: "success",
      });
    } catch (err) {
      await appDialog.alert(err instanceof Error ? err.message : "Could not save payment settings.", {
        tone: "danger",
      });
    } finally {
      setSavingPayment(false);
    }
  };

  const uploadQr = async (file: File | null) => {
    if (!file) return;
    setUploadingQr(true);
    try {
      const res = await platformApi.uploadSubscriptionQr(file);
      setPaymentConfig({ ...EMPTY_PAYMENT_CONFIG, ...res.data.config });
      await appDialog.alert("QR image uploaded. Shops will see it on expiry alerts.", {
        tone: "success",
      });
    } catch (err) {
      await appDialog.alert(err instanceof Error ? err.message : "QR upload failed.", { tone: "danger" });
    } finally {
      setUploadingQr(false);
    }
  };

  const confirmPayment = async (paymentId: string) => {
    setConfirmingId(paymentId);
    try {
      await platformApi.confirmSubscriptionPayment(paymentId, {
        notes: "Confirmed from platform subscriptions console",
      });
      await appDialog.alert("Payment confirmed — subscription auto-renewed.", {
        title: "Renewed",
        tone: "success",
      });
      load();
    } catch (err) {
      await appDialog.alert(err instanceof Error ? err.message : "Could not confirm payment.", {
        tone: "danger",
      });
    } finally {
      setConfirmingId(null);
    }
  };

  const columns: Column<PlatformSubscriptionRow>[] = [
    {
      key: "reference",
      header: "Reference",
      cell: (r) => (
        <div>
          <p className="font-mono text-sm font-medium">{r.reference_code}</p>
          <p className="text-[11px] text-muted-foreground">{r.plan}</p>
        </div>
      ),
    },
    {
      key: "shop",
      header: "Shop",
      cell: (r) =>
        r.tenant_id ? (
          <Link
            to={`/platform/shops/${r.tenant_id}`}
            className="font-medium text-primary underline-offset-2 hover:underline"
          >
            {r.tenant_name}
          </Link>
        ) : (
          <span className="text-muted-foreground">Unassigned</span>
        ),
    },
    {
      key: "contact",
      header: "Contact",
      cell: (r) => r.contact_user?.full_name ?? "—",
    },
    {
      key: "status",
      header: "Status",
      cell: (r) => (
        <div className="flex flex-wrap gap-1.5">
          <Badge variant={r.is_usable ? "success" : "destructive"}>{r.status}</Badge>
          <Badge variant={r.is_payment_current ? "success" : "destructive"}>
            {r.is_payment_current ? "Paid" : "Due"}
          </Badge>
        </div>
      ),
    },
    {
      key: "expires",
      header: "Expires",
      cell: (r) => r.expires_at ?? "—",
    },
    {
      key: "price",
      header: "Monthly fee",
      cell: (r) => <span className="font-semibold">{formatCurrency(r.monthly_fee)}</span>,
    },
    {
      key: "actions",
      header: "Actions",
      cell: (r) => (
        <div className="flex flex-wrap gap-1.5">
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
          <Button
            size="sm"
            variant="ghost"
            className="text-destructive hover:bg-destructive/10 hover:text-destructive"
            onClick={() => setPendingDelete(r)}
          >
            <Trash2 className="h-3 w-3" />
          </Button>
        </div>
      ),
    },
  ];

  const instructionsText = Array.isArray(paymentConfig.instructions)
    ? paymentConfig.instructions.join("\n")
    : String(paymentConfig.instructions || "");

  return (
    <PageLayout
      title="Subscriptions"
      description="Licenses, Waafi/EVC payment QR, billing cadence, and auto-renew tracking"
      breadcrumbs={["Home", "Platform", "Subscriptions"]}
      actions={
        <div className="flex flex-wrap gap-2">
          <Button variant="secondary" size="sm" onClick={load}>
            <RefreshCw className="h-4 w-4" /> Refresh
          </Button>
          <Button variant="secondary" size="sm" onClick={() => setShowPaymentSettings((v) => !v)}>
            <QrCode className="h-4 w-4" /> Payment & alert
          </Button>
          <Button size="sm" onClick={() => setShowForm((v) => !v)}>
            <Plus className="h-4 w-4" /> New Subscription
          </Button>
        </div>
      }
    >
      <div className="platform-shell space-y-6">
        <SubscriptionEditModal
          subscription={editing}
          shops={shops}
          plans={plans}
          open={!!editing}
          onClose={() => setEditing(null)}
          onSaved={load}
        />

        <PlatformConfirmDialog
          open={!!pendingDelete}
          title="Delete subscription?"
          description={
            pendingDelete
              ? `Remove ${pendingDelete.reference_code}${
                  pendingDelete.tenant_name ? ` (${pendingDelete.tenant_name})` : ""
                }. This cannot be undone from here.`
              : ""
          }
          confirmLabel="Delete"
          tone="danger"
          loading={deletingId === pendingDelete?.id}
          onCancel={() => setPendingDelete(null)}
          onConfirm={() => void confirmDelete()}
        />

        <motion.section
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="platform-hero p-6 sm:p-7"
        >
          <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <p className="text-xs font-medium uppercase tracking-[0.14em] text-primary">Billing control</p>
              <h2 className="mt-1 text-2xl font-semibold tracking-tight">Platform subscriptions</h2>
              <p className="mt-1 max-w-xl text-sm text-muted-foreground">
                Merchant {paymentConfig.merchant_number || "—"} · QR pay · track online · auto-renew when confirmed.
              </p>
            </div>
          </div>
        </motion.section>

        <KpiGrid>
          <KpiCard
            title="Subscriptions"
            value={String(stats.total)}
            icon={<CreditCard className="h-5 w-5" />}
            loading={loading}
            index={0}
            accent="primary"
          />
          <KpiCard
            title="Monthly fees"
            value={formatCurrency(stats.mrr)}
            icon={<CreditCard className="h-5 w-5" />}
            loading={loading}
            index={1}
            accent="success"
          />
          <KpiCard
            title="Payment due"
            value={String(stats.due)}
            icon={<AlertTriangle className="h-5 w-5" />}
            loading={loading}
            index={2}
            accent="warning"
          />
          <KpiCard
            title="Pending payments"
            value={String(stats.pending)}
            icon={<QrCode className="h-5 w-5" />}
            loading={loading}
            index={3}
            accent="info"
          />
        </KpiGrid>

        {showPaymentSettings && (
          <motion.form
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            onSubmit={savePaymentConfig}
            className="platform-panel p-5 sm:p-6"
          >
            <FormSection
              title="Waafi / EVC payment & alert dialog"
              description="Merchant number, QR image, instructions, and optional title/message overrides shown when a shop subscription expires."
            >
              <div className="grid gap-4 md:grid-cols-2">
                <FormField label="Company name" htmlFor="pay-company">
                  <Input
                    id="pay-company"
                    value={paymentConfig.company_name}
                    onChange={(e) => setPaymentConfig((c) => ({ ...c, company_name: e.target.value }))}
                  />
                </FormField>
                <FormField label="Merchant number" htmlFor="pay-merchant" required>
                  <Input
                    id="pay-merchant"
                    value={paymentConfig.merchant_number}
                    onChange={(e) => setPaymentConfig((c) => ({ ...c, merchant_number: e.target.value }))}
                  />
                </FormField>
                <FormField label="Provider label" htmlFor="pay-provider">
                  <Input
                    id="pay-provider"
                    value={paymentConfig.provider_label}
                    onChange={(e) => setPaymentConfig((c) => ({ ...c, provider_label: e.target.value }))}
                  />
                </FormField>
                <FormField label="Contact line" htmlFor="pay-contact">
                  <Input
                    id="pay-contact"
                    value={paymentConfig.contact_phone}
                    onChange={(e) => setPaymentConfig((c) => ({ ...c, contact_phone: e.target.value }))}
                  />
                </FormField>
                <FormField
                  label="USSD template"
                  htmlFor="pay-ussd"
                  hint="Use {merchant}, {amount}, {reference}"
                >
                  <Input
                    id="pay-ussd"
                    value={paymentConfig.ussd_template}
                    onChange={(e) => setPaymentConfig((c) => ({ ...c, ussd_template: e.target.value }))}
                  />
                </FormField>
                <FormField
                  label="QR dial template"
                  htmlFor="pay-qr-payload"
                  hint="Use {merchant} and {amount}. tel:…%23 opens the dialer when scanned (plan fee fills {amount})."
                >
                  <Input
                    id="pay-qr-payload"
                    value={paymentConfig.qr_payload_template}
                    onChange={(e) =>
                      setPaymentConfig((c) => ({ ...c, qr_payload_template: e.target.value }))
                    }
                  />
                </FormField>
                <FormField label="Instructions title" htmlFor="pay-inst-title">
                  <Input
                    id="pay-inst-title"
                    value={paymentConfig.instructions_title}
                    onChange={(e) =>
                      setPaymentConfig((c) => ({ ...c, instructions_title: e.target.value }))
                    }
                  />
                </FormField>
                <FormField label="Auto-renew on confirm" htmlFor="pay-auto">
                  <label className="flex items-center gap-2 text-sm">
                    <input
                      id="pay-auto"
                      type="checkbox"
                      className="h-4 w-4 rounded border-border"
                      checked={paymentConfig.auto_renew_enabled}
                      onChange={(e) =>
                        setPaymentConfig((c) => ({ ...c, auto_renew_enabled: e.target.checked }))
                      }
                    />
                    Confirm payment → renew subscription automatically
                  </label>
                </FormField>
                <FormField
                  label="Payment steps (one per line)"
                  htmlFor="pay-steps"
                  className="md:col-span-2 xl:col-span-3"
                >
                  <textarea
                    id="pay-steps"
                    className="min-h-[96px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                    value={instructionsText}
                    onChange={(e) =>
                      setPaymentConfig((c) => ({
                        ...c,
                        instructions: e.target.value.split("\n"),
                      }))
                    }
                  />
                </FormField>
                <FormField
                  label="Dialog title override (optional)"
                  htmlFor="pay-title"
                  hint="Replaces the default expiry alert title for all shops"
                >
                  <Input
                    id="pay-title"
                    value={paymentConfig.dialog_title_override}
                    onChange={(e) =>
                      setPaymentConfig((c) => ({ ...c, dialog_title_override: e.target.value }))
                    }
                    placeholder="e.g. Renew your MDA subscription"
                  />
                </FormField>
                <FormField
                  label="Dialog message override (optional)"
                  htmlFor="pay-msg"
                  hint="Placeholders: {shop_name}, {plan}, {monthly_fee}, {days_left}, …"
                >
                  <Input
                    id="pay-msg"
                    value={paymentConfig.dialog_message_override}
                    onChange={(e) =>
                      setPaymentConfig((c) => ({ ...c, dialog_message_override: e.target.value }))
                    }
                  />
                </FormField>
                <div className="md:col-span-2 flex flex-wrap items-center gap-4">
                  {paymentConfig.qr_image_url ? (
                    <img
                      src={resolveMediaUrl(paymentConfig.qr_image_url)}
                      alt="Subscription QR"
                      className="h-28 w-28 rounded-lg border border-border bg-white object-contain p-1"
                    />
                  ) : (
                    <div className="flex h-28 w-28 items-center justify-center rounded-lg border border-dashed border-border text-xs text-muted-foreground">
                      No QR image
                    </div>
                  )}
                  <div className="space-y-2">
                    <label className="inline-flex cursor-pointer items-center gap-2 rounded-md border border-input bg-secondary px-3 py-2 text-sm font-medium hover:bg-secondary/80">
                      {uploadingQr ? (
                        <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                      ) : (
                        <Upload className="h-3.5 w-3.5" />
                      )}
                      Upload QR image
                      <input
                        type="file"
                        accept="image/*"
                        className="hidden"
                        disabled={uploadingQr}
                        onChange={(e) => void uploadQr(e.target.files?.[0] ?? null)}
                      />
                    </label>
                    <p className="text-xs text-muted-foreground">
                      Prefer the placard QR. Otherwise shops get a generated QR from the USSD payload.
                    </p>
                  </div>
                </div>
              </div>
              <div className="mt-4 flex gap-2">
                <Button type="submit" loading={savingPayment}>
                  Save payment settings
                </Button>
                <Button type="button" variant="secondary" onClick={() => setShowPaymentSettings(false)}>
                  Close
                </Button>
              </div>
            </FormSection>
          </motion.form>
        )}

        {pendingPayments.length > 0 && (
          <div className="space-y-3">
            <p className="text-sm font-semibold tracking-tight">Pending Waafi / EVC payments</p>
            <div className="grid gap-3 lg:grid-cols-2">
              {pendingPayments.map((p) => (
                <div key={p.id} className="platform-panel flex items-start justify-between gap-3 p-4">
                  <div className="min-w-0">
                    <p className="font-medium">{p.tenant_name || "Shop"}</p>
                    <p className="font-mono text-xs text-muted-foreground">{p.payment_reference}</p>
                    <p className="mt-1 text-sm">
                      {formatCurrency(p.amount)} → merchant {p.merchant_number || "—"}
                    </p>
                    {p.payer_phone && (
                      <p className="text-xs text-muted-foreground">Payer: {p.payer_phone}</p>
                    )}
                  </div>
                  <Button
                    size="sm"
                    loading={confirmingId === p.id}
                    onClick={() => void confirmPayment(p.id)}
                  >
                    <CheckCircle2 className="h-3.5 w-3.5" />
                    Confirm & renew
                  </Button>
                </div>
              ))}
            </div>
          </div>
        )}

        {alerts.length > 0 && (
          <div className="space-y-3">
            <p className="text-sm font-semibold tracking-tight">Attention required</p>
            <div className="grid gap-3 lg:grid-cols-2">
              {alerts.map((alert, index) => (
                <motion.div
                  key={alert.subscription_id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.04 }}
                  className={`platform-panel flex items-start gap-3 p-4 ${
                    alert.severity === "critical"
                      ? "border-destructive/40"
                      : "border-amber-500/35"
                  }`}
                >
                  <div
                    className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl ${
                      alert.severity === "critical"
                        ? "bg-destructive/10 text-destructive"
                        : "bg-amber-500/10 text-amber-700"
                    }`}
                  >
                    <AlertTriangle className="h-5 w-5" />
                  </div>
                  <div className="min-w-0">
                    <p className="font-medium">{alert.title}</p>
                    <p className="text-sm text-muted-foreground">{alert.tenant_name || "Unassigned"}</p>
                    <p className="mt-1 text-sm">{alert.message}</p>
                    <p className="mt-2 text-xs text-muted-foreground">
                      {alert.reference_code} · {formatCurrency(alert.monthly_fee)}/mo · expires{" "}
                      {alert.expires_at}
                      {alert.payment?.merchant_number
                        ? ` · merchant ${alert.payment.merchant_number}`
                        : ""}
                    </p>
                  </div>
                </motion.div>
              ))}
            </div>
          </div>
        )}

        {showForm && (
          <motion.form
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            onSubmit={createSubscription}
            className="platform-panel p-5 sm:p-6"
          >
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
              <div className="mt-4 flex gap-2">
                <Button type="submit" loading={saving}>
                  Create Subscription
                </Button>
                <Button type="button" variant="secondary" onClick={() => setShowForm(false)}>
                  Cancel
                </Button>
              </div>
            </FormSection>
          </motion.form>
        )}

        <DataTable
          exportTitle="Subscriptions"
          columns={columns}
          data={subscriptions}
          loading={loading}
          emptyMessage="No subscriptions yet. Create one and assign it to a shop."
          defaultPageSize={10}
        />
      </div>
    </PageLayout>
  );
}
