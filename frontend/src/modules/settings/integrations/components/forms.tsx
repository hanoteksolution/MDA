import { useState } from "react";
import type { ReactNode } from "react";
import { KeyRound, Plus, Send, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { FormField } from "@/components/forms/FormField";
import type {
  IntegrationCredential,
  PaymentProvider,
  PaymentProviderInput,
  SmsProvider,
  SmsProviderInput,
} from "@/services/api/integrations";
import type { CredentialDraft } from "../credentialFlow";
import { emptyCredentialDraft, scrubDraft } from "../credentialFlow";
import {
  MOCK_MODES,
  PAYMENT_MOCK_MODES,
  PAYMENT_PROVIDER_TYPES,
  SMS_PLACEHOLDERS,
  SMS_PROVIDER_TYPES,
  buildPaymentProviderInput,
  buildSmsProviderInput,
  describeCredential,
  emptyPaymentProviderForm,
  emptySmsProviderForm,
  extractPlaceholders,
  paymentFormFromProvider,
  smsFormFromProvider,
  validatePaymentProviderForm,
  validateSmsProviderForm,
  validateTemplateForm,
  validateTestSms,
} from "../lib";
import type { FormErrors, KvRow, PaymentProviderForm, SmsProviderForm, TemplateForm } from "../lib";
import { Notice, Panel } from "./primitives";

const selectClass = "h-11 w-full rounded-lg border border-input bg-background px-3 text-sm";
const NEW = "__new__";

export interface BranchOption {
  id: string;
  name: string;
}

/** What the container reports back after a save attempt. */
export interface SaveResult {
  error?: string;
  /** Credentials created during this attempt, so a retry links them instead of creating duplicates. */
  createdCredentialIds?: { api?: string; webhook?: string };
}

// ─── building blocks ────────────────────────────────────────────────────────────

function BranchSelect({ value, onChange, branches, id }: { value: string; onChange: (v: string) => void; branches: BranchOption[]; id: string }) {
  return (
    <select id={id} className={selectClass} value={value} onChange={(e) => onChange(e.target.value)}>
      <option value="">All branches (company-wide)</option>
      {branches.map((b) => (
        <option key={b.id} value={b.id}>{b.name}</option>
      ))}
    </select>
  );
}

function Toggle({ id, checked, onChange, label, hint }: { id: string; checked: boolean; onChange: (v: boolean) => void; label: string; hint?: string }) {
  return (
    <label htmlFor={id} className="flex cursor-pointer items-start gap-3 rounded-xl border border-border p-3">
      <input id={id} type="checkbox" className="mt-0.5 h-4 w-4" checked={checked} onChange={(e) => onChange(e.target.checked)} />
      <span>
        <span className="block text-sm font-medium text-foreground">{label}</span>
        {hint && <span className="block text-xs text-muted-foreground">{hint}</span>}
      </span>
    </label>
  );
}

export function KvEditor({
  rows,
  onChange,
  keyLabel = "Name",
  valueLabel = "Value",
  addLabel = "Add row",
}: {
  rows: KvRow[];
  onChange: (rows: KvRow[]) => void;
  keyLabel?: string;
  valueLabel?: string;
  addLabel?: string;
}) {
  const set = (i: number, patch: Partial<KvRow>) => onChange(rows.map((r, idx) => (idx === i ? { ...r, ...patch } : r)));
  return (
    <div className="space-y-2">
      {rows.map((row, i) => (
        <div key={i} className="flex gap-2">
          <Input aria-label={`${keyLabel} ${i + 1}`} placeholder={keyLabel} value={row.key} onChange={(e) => set(i, { key: e.target.value })} />
          <Input aria-label={`${valueLabel} ${i + 1}`} placeholder={valueLabel} value={row.value} onChange={(e) => set(i, { value: e.target.value })} />
          <Button type="button" variant="ghost" size="icon" aria-label={`Remove row ${i + 1}`} onClick={() => onChange(rows.filter((_, idx) => idx !== i))}>
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      ))}
      <Button type="button" variant="outline" size="sm" onClick={() => onChange([...rows, { key: "", value: "" }])}>
        <Plus className="mr-1.5 h-3.5 w-3.5" />{addLabel}
      </Button>
    </div>
  );
}

/**
 * Pick, create or rotate a credential. The secret input is write-only: it is never prefilled,
 * and for an existing credential only its label and masked tail are ever displayed.
 */
export function CredentialPicker({
  idPrefix,
  label,
  hint,
  credentials,
  selectedId,
  onSelect,
  draft,
  onDraft,
  errors,
  canCreate,
}: {
  idPrefix: string;
  label: string;
  hint?: string;
  credentials: IntegrationCredential[];
  selectedId: string;
  onSelect: (id: string) => void;
  draft: CredentialDraft;
  onDraft: (d: CredentialDraft) => void;
  errors?: FormErrors;
  canCreate: boolean;
}) {
  const selected = credentials.find((c) => c.id === selectedId);
  const value = draft.mode === "new" ? NEW : selectedId;
  return (
    <div className="space-y-3 rounded-xl border border-border p-3">
      <FormField label={label} htmlFor={`${idPrefix}-select`} hint={hint} error={errors?.[idPrefix]}>
        <select
          id={`${idPrefix}-select`}
          className={selectClass}
          value={value}
          onChange={(e) => {
            if (e.target.value === NEW) onDraft({ mode: "new", label: "", secret: "" });
            else {
              onDraft(emptyCredentialDraft());
              onSelect(e.target.value);
            }
          }}
        >
          <option value="">No credential</option>
          {credentials.map((c) => (
            <option key={c.id} value={c.id}>{describeCredential(c)}</option>
          ))}
          {canCreate && <option value={NEW}>＋ Create new credential…</option>}
        </select>
      </FormField>
      {draft.mode === "new" && (
        <div className="grid gap-3 md:grid-cols-2">
          <FormField label="Credential label" htmlFor={`${idPrefix}-label`} required error={errors?.label}>
            <Input id={`${idPrefix}-label`} value={draft.label} onChange={(e) => onDraft({ ...draft, label: e.target.value })} placeholder="e.g. Gateway API key" />
          </FormField>
          <FormField label="Secret value" htmlFor={`${idPrefix}-secret`} required error={errors?.secret} hint="Encrypted on save. It cannot be viewed again.">
            <Input id={`${idPrefix}-secret`} type="password" autoComplete="new-password" spellCheck={false} value={draft.secret} onChange={(e) => onDraft({ ...draft, secret: e.target.value })} />
          </FormField>
        </div>
      )}
      {draft.mode === "existing" && selected && canCreate && (
        <FormField label="Replace secret (optional)" htmlFor={`${idPrefix}-rotate`} hint={`Currently ${selected.has_secret ? (selected.masked_tail || "stored") : "empty"}. Leave blank to keep it.`}>
          <Input id={`${idPrefix}-rotate`} type="password" autoComplete="new-password" spellCheck={false} value={draft.secret} onChange={(e) => onDraft({ ...draft, secret: e.target.value })} placeholder="Enter a new secret to rotate" />
        </FormField>
      )}
    </div>
  );
}

function FormShell({
  title,
  description,
  children,
  saving,
  serverError,
  submitLabel,
  onCancel,
  onSubmit,
}: {
  title: string;
  description?: string;
  children: ReactNode;
  saving: boolean;
  serverError: string | null;
  submitLabel: string;
  onCancel: () => void;
  onSubmit: () => void;
}) {
  return (
    <Panel title={title} description={description}>
      <form
        noValidate
        className="space-y-5 p-4"
        onSubmit={(e) => {
          e.preventDefault();
          onSubmit();
        }}
      >
        {children}
        {serverError && (
          <p role="alert" className="rounded-xl border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
            {serverError}
          </p>
        )}
        <div className="flex justify-end gap-2 border-t border-border pt-4">
          <Button type="button" variant="outline" onClick={onCancel} disabled={saving}>Cancel</Button>
          <Button type="submit" loading={saving}>{submitLabel}</Button>
        </div>
      </form>
    </Panel>
  );
}

// ─── SMS provider ───────────────────────────────────────────────────────────────

export function SmsProviderFormView({
  initial,
  credentials,
  branches,
  canManageCredentials,
  onSave,
  onCancel,
}: {
  initial: SmsProvider | null;
  credentials: IntegrationCredential[];
  branches: BranchOption[];
  canManageCredentials: boolean;
  onSave: (input: SmsProviderInput, credential: CredentialDraft) => Promise<SaveResult>;
  onCancel: () => void;
}) {
  const [form, setForm] = useState<SmsProviderForm>(() => (initial ? smsFormFromProvider(initial) : emptySmsProviderForm()));
  const [draft, setDraft] = useState<CredentialDraft>(emptyCredentialDraft());
  const [errors, setErrors] = useState<FormErrors>({});
  const [serverError, setServerError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const patch = (p: Partial<SmsProviderForm>) => setForm((f) => ({ ...f, ...p }));
  const isMock = form.provider_type === "MOCK";

  const submit = async () => {
    const found = validateSmsProviderForm(form);
    if (draft.mode === "new") {
      if (!draft.label.trim()) found.label = "A label is required.";
      if (!draft.secret.trim()) found.secret = "A secret value is required.";
    }
    setErrors(found);
    if (Object.keys(found).length) return;
    setSaving(true);
    setServerError(null);
    const result = await onSave(buildSmsProviderInput(form), draft);
    setSaving(false);
    setDraft((d) => scrubDraft(d)); // the secret never outlives the submit
    if (result.createdCredentialIds?.api) {
      patch({ credential_id: result.createdCredentialIds.api });
      setDraft(emptyCredentialDraft());
    }
    if (result.error) setServerError(result.error);
  };

  return (
    <FormShell
      title={initial ? `Edit ${initial.name}` : "Add SMS provider"}
      description="Describe any HTTPS SMS gateway. No provider is built in — you supply the request template."
      saving={saving}
      serverError={serverError}
      submitLabel={initial ? "Save changes" : "Create provider"}
      onCancel={onCancel}
      onSubmit={submit}
    >
      <div className="grid gap-4 md:grid-cols-2">
        <FormField label="Name" htmlFor="sms-name" required error={errors.name}>
          <Input id="sms-name" value={form.name} onChange={(e) => patch({ name: e.target.value })} placeholder="e.g. Primary SMS gateway" />
        </FormField>
        <FormField label="Provider type" htmlFor="sms-type" hint={SMS_PROVIDER_TYPES.find((t) => t.value === form.provider_type)?.hint}>
          <select id="sms-type" className={selectClass} value={form.provider_type} onChange={(e) => patch({ provider_type: e.target.value as SmsProviderForm["provider_type"] })}>
            {SMS_PROVIDER_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
          </select>
        </FormField>
        <FormField label="Branch scope" htmlFor="sms-branch" hint="A branch-specific provider overrides the company-wide one for that branch.">
          <BranchSelect id="sms-branch" value={form.branch_id} onChange={(v) => patch({ branch_id: v })} branches={branches} />
        </FormField>
        <FormField label="Sender ID" htmlFor="sms-sender" error={errors.sender_id} hint="As registered with your provider. Falls back to the branch code when blank.">
          <Input id="sms-sender" maxLength={32} value={form.sender_id} onChange={(e) => patch({ sender_id: e.target.value })} />
        </FormField>
      </div>

      {isMock ? (
        <FormField label="Simulated outcome" htmlFor="sms-mode" hint="Testing only — nothing leaves the server.">
          <select id="sms-mode" className={selectClass} value={form.mock_mode} onChange={(e) => patch({ mock_mode: e.target.value })}>
            {MOCK_MODES.map((m) => <option key={m} value={m}>{m}</option>)}
          </select>
        </FormField>
      ) : (
        <>
          <div className="grid gap-4 md:grid-cols-3">
            <FormField label="Endpoint URL" htmlFor="sms-url" required error={errors.url} className="md:col-span-3">
              <Input id="sms-url" inputMode="url" value={form.url} onChange={(e) => patch({ url: e.target.value })} placeholder="https://api.provider.example/v1/sms" />
            </FormField>
            <FormField label="HTTP method" htmlFor="sms-method">
              <select id="sms-method" className={selectClass} value={form.method} onChange={(e) => patch({ method: e.target.value as "POST" | "GET" })}>
                <option value="POST">POST</option>
                <option value="GET">GET</option>
              </select>
            </FormField>
            <FormField label="Body format" htmlFor="sms-format">
              <select id="sms-format" className={selectClass} value={form.body_format} onChange={(e) => patch({ body_format: e.target.value as "json" | "form" })}>
                <option value="json">JSON</option>
                <option value="form">Form (urlencoded)</option>
              </select>
            </FormField>
            <FormField label="Timeout (seconds)" htmlFor="sms-timeout" error={errors.timeout_seconds}>
              <Input id="sms-timeout" inputMode="numeric" value={form.timeout_seconds} onChange={(e) => patch({ timeout_seconds: e.target.value })} />
            </FormField>
          </div>
          <Notice>
            Placeholders filled at send time: {SMS_PLACEHOLDERS.join("  ")}. Reference the credential only as{" "}
            <code>{"{secret}"}</code> — never paste a key into a header or field.
          </Notice>
          <FormField label="Headers" htmlFor="sms-headers" error={errors.headers}>
            <KvEditor rows={form.headers} onChange={(rows) => patch({ headers: rows })} keyLabel="Header" valueLabel="Value" addLabel="Add header" />
          </FormField>
          <FormField label="Request body fields" htmlFor="sms-body" error={errors.body} hint="Map your provider's field names to the placeholders above.">
            <KvEditor rows={form.body} onChange={(rows) => patch({ body: rows })} keyLabel="Field" valueLabel="Value" addLabel="Add field" />
          </FormField>
          <div className="grid gap-4 md:grid-cols-2">
            <FormField label="Success status codes" htmlFor="sms-success" error={errors.success_statuses} hint="Leave blank to accept any 2xx.">
              <Input id="sms-success" value={form.success_statuses} onChange={(e) => patch({ success_statuses: e.target.value })} placeholder="200, 201, 202" />
            </FormField>
            <FormField label="Message-ID path in reply" htmlFor="sms-refpath" hint="Dotted path into the JSON reply, e.g. data.id.">
              <Input id="sms-refpath" value={form.reference_path} onChange={(e) => patch({ reference_path: e.target.value })} />
            </FormField>
          </div>
          <CredentialPicker
            idPrefix="credential_id"
            label="API credential"
            hint="Injected as {secret} when a message is sent."
            credentials={credentials}
            selectedId={form.credential_id}
            onSelect={(id) => patch({ credential_id: id })}
            draft={draft}
            onDraft={setDraft}
            errors={errors}
            canCreate={canManageCredentials}
          />
        </>
      )}

      <div className="grid gap-3 md:grid-cols-2">
        <Toggle id="sms-active" checked={form.is_active} onChange={(v) => patch({ is_active: v })} label="Enabled" hint="Disabled providers are never used to send." />
        <Toggle id="sms-default" checked={form.is_default} onChange={(v) => patch({ is_default: v })} label="Default for this scope" hint="Only one default per scope; the server rejects a second." />
      </div>
    </FormShell>
  );
}

// ─── payment provider ───────────────────────────────────────────────────────────

export function PaymentProviderFormView({
  initial,
  credentials,
  branches,
  canManageCredentials,
  onSave,
  onCancel,
}: {
  initial: PaymentProvider | null;
  credentials: IntegrationCredential[];
  branches: BranchOption[];
  canManageCredentials: boolean;
  onSave: (input: PaymentProviderInput, api: CredentialDraft, webhook: CredentialDraft) => Promise<SaveResult>;
  onCancel: () => void;
}) {
  const [form, setForm] = useState<PaymentProviderForm>(() => (initial ? paymentFormFromProvider(initial) : emptyPaymentProviderForm()));
  const [apiDraft, setApiDraft] = useState<CredentialDraft>(emptyCredentialDraft());
  const [whDraft, setWhDraft] = useState<CredentialDraft>(emptyCredentialDraft());
  const [errors, setErrors] = useState<FormErrors>({});
  const [serverError, setServerError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const patch = (p: Partial<PaymentProviderForm>) => setForm((f) => ({ ...f, ...p }));

  const submit = async () => {
    const found = validatePaymentProviderForm(form);
    setErrors(found);
    if (Object.keys(found).length) return;
    for (const [d, prefix] of [[apiDraft, "api"], [whDraft, "webhook"]] as const) {
      if (d.mode === "new" && (!d.label.trim() || !d.secret.trim())) {
        setErrors({ ...found, [`${prefix}_credential`]: "Enter a label and a secret for the new credential." });
        return;
      }
    }
    setSaving(true);
    setServerError(null);
    const result = await onSave(buildPaymentProviderInput(form), apiDraft, whDraft);
    setSaving(false);
    setApiDraft((d) => scrubDraft(d));
    setWhDraft((d) => scrubDraft(d));
    if (result.createdCredentialIds?.api) {
      patch({ credential_id: result.createdCredentialIds.api });
      setApiDraft(emptyCredentialDraft());
    }
    if (result.createdCredentialIds?.webhook) {
      patch({ webhook_credential_id: result.createdCredentialIds.webhook });
      setWhDraft(emptyCredentialDraft());
    }
    if (result.error) setServerError(result.error);
  };

  return (
    <FormShell
      title={initial ? `Edit ${initial.name}` : "Add payment provider"}
      description="Provider-agnostic merchant configuration. Secrets are stored encrypted and never displayed."
      saving={saving}
      serverError={serverError}
      submitLabel={initial ? "Save changes" : "Create provider"}
      onCancel={onCancel}
      onSubmit={submit}
    >
      <div className="grid gap-4 md:grid-cols-2">
        <FormField label="Name" htmlFor="pay-name" required error={errors.name}>
          <Input id="pay-name" value={form.name} onChange={(e) => patch({ name: e.target.value })} placeholder="e.g. Mobile money merchant" />
        </FormField>
        <FormField label="Provider type" htmlFor="pay-type" hint={PAYMENT_PROVIDER_TYPES[0].hint}>
          <select id="pay-type" className={selectClass} value={form.provider_type} disabled>
            {PAYMENT_PROVIDER_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
          </select>
        </FormField>
        <FormField label="Branch scope" htmlFor="pay-branch" hint="A branch-specific merchant is used only for that branch.">
          <BranchSelect id="pay-branch" value={form.branch_id} onChange={(v) => patch({ branch_id: v })} branches={branches} />
        </FormField>
        <FormField label="Simulated outcome" htmlFor="pay-mode" hint="Test gateway behaviour on payment creation.">
          <select id="pay-mode" className={selectClass} value={form.mock_mode} onChange={(e) => patch({ mock_mode: e.target.value })}>
            {PAYMENT_MOCK_MODES.map((m) => <option key={m} value={m}>{m}</option>)}
          </select>
        </FormField>
      </div>
      <FormField label="Provider metadata (not secret)" htmlFor="pay-meta" error={errors.metadata} hint="Non-sensitive identifiers such as a merchant ID or region. Stored unencrypted.">
        <KvEditor rows={form.metadata} onChange={(rows) => patch({ metadata: rows })} keyLabel="Key" valueLabel="Value" addLabel="Add metadata" />
      </FormField>
      <div className="grid gap-4 lg:grid-cols-2">
        <CredentialPicker
          idPrefix="api_credential"
          label="API credential"
          hint="Used for calls from the ERP to the provider."
          credentials={credentials}
          selectedId={form.credential_id}
          onSelect={(id) => patch({ credential_id: id })}
          draft={apiDraft}
          onDraft={setApiDraft}
          errors={{ api_credential: errors.api_credential ?? "" }}
          canCreate={canManageCredentials}
        />
        <CredentialPicker
          idPrefix="webhook_credential"
          label="Webhook signing secret"
          hint="Verifies callbacks from the provider. Use a different secret from the API credential."
          credentials={credentials}
          selectedId={form.webhook_credential_id}
          onSelect={(id) => patch({ webhook_credential_id: id })}
          draft={whDraft}
          onDraft={setWhDraft}
          errors={{ webhook_credential: errors.webhook_credential_id ?? errors.webhook_credential ?? "" }}
          canCreate={canManageCredentials}
        />
      </div>
      {initial && (
        <Notice>
          Give your provider this webhook path (appended to your API host): <code className="break-all">{initial.webhook_path}</code>
        </Notice>
      )}
      <Toggle id="pay-active" checked={form.is_active} onChange={(v) => patch({ is_active: v })} label="Enabled" hint="Disabled providers cannot start new payments." />
    </FormShell>
  );
}

// ─── template ───────────────────────────────────────────────────────────────────

export function TemplateFormView({
  onSave,
  onCancel,
}: {
  onSave: (input: { code: string; name: string; body: string }) => Promise<string | null>;
  onCancel: () => void;
}) {
  const [form, setForm] = useState<TemplateForm>({ code: "", name: "", body: "" });
  const [errors, setErrors] = useState<FormErrors>({});
  const [serverError, setServerError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const placeholders = extractPlaceholders(form.body);

  const submit = async () => {
    const found = validateTemplateForm(form);
    setErrors(found);
    if (Object.keys(found).length) return;
    setSaving(true);
    setServerError(null);
    const error = await onSave({ code: form.code.trim(), name: form.name.trim() || form.code.trim(), body: form.body });
    setSaving(false);
    if (error) setServerError(error);
  };

  return (
    <FormShell title="Add SMS template" description="Templates cannot be edited after creation yet — add a new code to change wording." saving={saving} serverError={serverError} submitLabel="Create template" onCancel={onCancel} onSubmit={submit}>
      <div className="grid gap-4 md:grid-cols-2">
        <FormField label="Code" htmlFor="tpl-code" required error={errors.code} hint="Referenced by business events, e.g. invoice_paid.">
          <Input id="tpl-code" value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value })} />
        </FormField>
        <FormField label="Name" htmlFor="tpl-name" error={errors.name}>
          <Input id="tpl-name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        </FormField>
      </div>
      <FormField label="Message" htmlFor="tpl-body" required error={errors.body} hint={placeholders.length ? `Placeholders: ${placeholders.map((p) => `{${p}}`).join(" ")}` : "Use {customer}, {amount}… for values."}>
        <textarea id="tpl-body" rows={4} className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm" value={form.body} onChange={(e) => setForm({ ...form, body: e.target.value })} />
      </FormField>
    </FormShell>
  );
}

// ─── test SMS ───────────────────────────────────────────────────────────────────

export function TestSmsPanel({
  branches,
  onSend,
}: {
  branches: BranchOption[];
  onSend: (input: { to: string; body: string; branch_id?: string }) => Promise<{ ok: boolean; message: string }>;
}) {
  const [to, setTo] = useState("");
  const [body, setBody] = useState("Test message from your ERP.");
  const [branch, setBranch] = useState("");
  const [errors, setErrors] = useState<FormErrors>({});
  const [result, setResult] = useState<{ ok: boolean; message: string } | null>(null);
  const [sending, setSending] = useState(false);

  const submit = async () => {
    const found = validateTestSms({ to, body });
    setErrors(found);
    if (Object.keys(found).length) return;
    setSending(true);
    setResult(null);
    setResult(await onSend({ to: to.trim(), body, branch_id: branch || undefined }));
    setSending(false);
  };

  return (
    <Panel title="Send a test SMS" description="Queues a real message through the active provider for the chosen branch. Check the message log for the outcome.">
      <form noValidate className="grid gap-4 p-4 md:grid-cols-2" onSubmit={(e) => { e.preventDefault(); void submit(); }}>
        <FormField label="Phone number" htmlFor="test-to" required error={errors.to} hint="International format, e.g. +2526XXXXXXX.">
          <Input id="test-to" inputMode="tel" value={to} onChange={(e) => setTo(e.target.value)} />
        </FormField>
        <FormField label="Branch" htmlFor="test-branch" hint="Selects which provider is used.">
          <BranchSelect id="test-branch" value={branch} onChange={setBranch} branches={branches} />
        </FormField>
        <FormField label="Message" htmlFor="test-body" required error={errors.body} className="md:col-span-2">
          <textarea id="test-body" rows={2} className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm" value={body} onChange={(e) => setBody(e.target.value)} />
        </FormField>
        <div className="flex items-center justify-between gap-3 md:col-span-2">
          <p role="status" className={result ? (result.ok ? "text-sm text-success" : "text-sm text-destructive") : "sr-only"}>
            {result?.message}
          </p>
          <Button type="submit" loading={sending}><Send className="mr-2 h-4 w-4" />Send test</Button>
        </div>
      </form>
      <p className="flex items-center gap-2 border-t border-border px-4 py-3 text-xs text-muted-foreground">
        <KeyRound className="h-3.5 w-3.5" />
        There is no dry-run “test connection” API yet — this sends one real message.
      </p>
    </Panel>
  );
}
