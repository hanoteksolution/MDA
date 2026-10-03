import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { PageLayout } from "@/components/layout/PageLayout";
import { ContentSection } from "@/components/layout/ContentSection";
import { DataTable, type Column } from "@/components/data/DataTable";
import { Button } from "@/components/ui/button";
import {
  platformBillingApi,
  type BillingInvoiceRow,
  type BillingPaymentRow,
  type BillingReconciliationRow,
  type TenantBillingDetail,
} from "@/services/api/platformBilling";
import { BillingBadge, ErrorNote, RecoveryDialog, date, humanize, money } from "./billingUi";

/** Platform Admin → Billing → tenant: plan, timeline, invoices, payments, renewals, reconciliation and audit. */
export function PlatformBillingTenantPage() {
  const { tenantId = "" } = useParams();
  const [data, setData] = useState<TenantBillingDetail>();
  const [error, setError] = useState("");
  const [reload, setReload] = useState(0);
  const [recovering, setRecovering] = useState(false);
  useEffect(() => {
    setError("");
    platformBillingApi
      .tenant(tenantId)
      .then((r) => setData(r.data))
      .catch((e: unknown) => setError(e instanceof Error ? e.message : "Could not load tenant billing."));
  }, [tenantId, reload]);

  const sub = data?.subscription;
  const invoiceColumns: Column<BillingInvoiceRow>[] = [
    { key: "number", header: "Invoice", cell: (r) => <span className="font-medium">{r.invoice_number}</span> },
    { key: "issued", header: "Issued", cell: (r) => date(r.issue_date) },
    { key: "total", header: "Total", cell: (r) => money(r.total_amount, r.currency) },
    { key: "paid", header: "Paid", cell: (r) => money(r.amount_paid, r.currency) },
    { key: "status", header: "Status", cell: (r) => <BillingBadge status={r.status} /> },
  ];
  const paymentColumns: Column<BillingPaymentRow>[] = [
    { key: "ref", header: "Reference", cell: (r) => <span className="font-mono text-xs">{r.payment_reference}</span> },
    { key: "kind", header: "Type", cell: (r) => (r.kind === "checkout" ? "Online checkout" : "Manual / legacy") },
    { key: "amount", header: "Amount", cell: (r) => money(r.amount, r.currency) },
    { key: "status", header: "Status", cell: (r) => <BillingBadge status={r.status} /> },
    { key: "created", header: "Created", cell: (r) => date(r.created_at) },
    { key: "confirmed", header: "Confirmed", cell: (r) => date(r.confirmed_at) },
  ];
  const reconColumns: Column<BillingReconciliationRow>[] = [
    { key: "kind", header: "Issue", cell: (r) => r.kind_label },
    { key: "ref", header: "Payment", cell: (r) => r.payment_reference ?? "—" },
    { key: "provider", header: "Provider", cell: (r) => `${humanize(r.provider_status)} ${money(r.provider_amount)}` },
    { key: "ledger", header: "Ledger", cell: (r) => `${humanize(r.ledger_status)} ${money(r.ledger_amount)}` },
    { key: "status", header: "Status", cell: (r) => <BillingBadge status={r.status} /> },
    { key: "found", header: "Found", cell: (r) => date(r.created_at) },
  ];
  type AuditRow = TenantBillingDetail["audit"][number];
  const auditColumns: Column<AuditRow>[] = [
    { key: "at", header: "When", cell: (r) => date(r.at) },
    { key: "event", header: "Event", cell: (r) => humanize(r.event ?? r.action) },
    { key: "entity", header: "Record", cell: (r) => r.entity_type },
    { key: "user", header: "By", cell: (r) => r.user ?? "System" },
  ];

  return (
    <PageLayout
      title={data ? `${data.tenant.name} — Billing` : "Tenant billing"}
      description={data?.tenant.workspace ? `Workspace: ${data.tenant.workspace}` : "Subscription billing for one tenant."}
      breadcrumbs={["Platform", "Billing", data?.tenant.name ?? "Tenant"]}
      backTo="/platform/billing?section=subscriptions"
      backLabel="Billing"
      actions={data?.can_recover && sub ? <Button size="sm" variant="secondary" onClick={() => setRecovering(true)}>Manual recovery</Button> : undefined}
    >
      <ErrorNote message={error} onRetry={() => setReload((v) => v + 1)} />
      {data && (
        <>
          <ContentSection title="Current plan">
            {sub && data.plan ? (
              <dl className="grid gap-4 text-sm sm:grid-cols-2 lg:grid-cols-4">
                <Item label="Plan" value={`${data.plan.name} (${money(sub.monthly_fee)}/mo)`} />
                <Item label="Subscription" value={<BillingBadge status={sub.status} />} />
                <Item label="Billing" value={<BillingBadge status={sub.billing_status} />} />
                <Item label="Reference" value={sub.reference_code} />
                <Item label="Started" value={date(sub.started_at)} />
                <Item label="Expires" value={date(sub.expires_at)} />
                <Item label="Next billing" value={date(sub.next_billing_at)} />
                <Item label="Last paid" value={date(sub.last_paid_at)} />
                <Item label="Limits" value={`${data.plan.max_users} users · ${data.plan.max_branches} branches`} />
                <Item label="Period / grace" value={`${sub.billing_period_days} days / ${sub.grace_period_days} days`} />
              </dl>
            ) : (
              <p className="text-sm text-muted-foreground">This tenant has no subscription.</p>
            )}
          </ContentSection>

          <ContentSection title="Subscription timeline">
            {data.timeline.length ? (
              <ol className="space-y-3 border-l pl-4">
                {data.timeline.map((e, i) => (
                  <li key={`${e.event}-${i}`} className="text-sm">
                    <div className="font-medium">{e.label}</div>
                    <div className="text-xs text-muted-foreground">
                      {date(e.at)}
                      {e.amount ? ` · ${money(e.amount)}` : ""}
                      {e.by ? ` · by ${e.by}` : ""}
                    </div>
                  </li>
                ))}
              </ol>
            ) : (
              <p className="text-sm text-muted-foreground">No billing events recorded.</p>
            )}
          </ContentSection>

          <ContentSection title="Activation / renewal history">
            {data.renewal_history.length ? (
              <ul className="space-y-2 text-sm">
                {data.renewal_history.map((h, i) => (
                  <li key={i} className="flex flex-wrap justify-between gap-2 rounded-lg border px-3 py-2">
                    <span className="font-medium">{humanize(h.event)}</span>
                    <span className="text-muted-foreground">
                      {date(h.at)}{h.by ? ` · ${h.by}` : ""}{h.expires_at ? ` · new expiry ${date(h.expires_at)}` : ""}
                    </span>
                    {h.reason && <span className="w-full text-xs text-muted-foreground">Reason: {h.reason}</span>}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-muted-foreground">No activations or renewals recorded in the audit log.</p>
            )}
          </ContentSection>

          <ContentSection title="Invoices">
            <DataTable embedded columns={invoiceColumns} data={data.invoices} clientPagination emptyMessage="No invoices issued." />
          </ContentSection>
          <ContentSection title="Payments">
            <DataTable embedded columns={paymentColumns} data={data.payments} clientPagination emptyMessage="No payments recorded." />
          </ContentSection>
          <ContentSection title="Reconciliation issues">
            <DataTable embedded columns={reconColumns} data={data.reconciliation} clientPagination emptyMessage="No reconciliation issues." />
          </ContentSection>
          <ContentSection title="Audit history">
            <DataTable embedded columns={auditColumns} data={data.audit} clientPagination emptyMessage="No audit entries." />
          </ContentSection>
        </>
      )}
      <RecoveryDialog
        target={recovering && sub ? { id: sub.id, label: data?.tenant.name ?? sub.reference_code } : null}
        onClose={() => setRecovering(false)}
        onDone={() => setReload((v) => v + 1)}
      />
    </PageLayout>
  );
}

function Item({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <dt className="text-xs uppercase tracking-wide text-muted-foreground">{label}</dt>
      <dd className="mt-1">{value}</dd>
    </div>
  );
}
