import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { Plus } from "lucide-react";
import { PageLayout } from "@/components/layout/PageLayout";
import { ContentSection } from "@/components/layout/ContentSection";
import { DataTable, type Column } from "@/components/data/DataTable";
import { FormActions, FormPageLayout } from "@/components/forms/FormPageLayout";
import { FormField, FormGrid, FormSection } from "@/components/forms/FormField";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { appDialog } from "@/components/feedback/AppDialog";
import { useAuthStore } from "@/store/authStore";
import { usePermissions } from "@/hooks/usePermissions";
import {
  projectsApi,
  type Project,
  type ProjectOperation,
  type ProjectOperationKind,
} from "@/services/api/projects";
import { formatCurrency } from "@/utils/cn";

type Field = { key: string; label: string; type?: "date" | "number" | "select"; options?: string[]; required?: boolean };
type OperationConfig = {
  kind: ProjectOperationKind;
  path: string;
  title: string;
  singular: string;
  permission: string;
  name: (row: ProjectOperation) => string;
  fields: Field[];
  statuses: string[];
};

const LEVELS = ["low", "medium", "high", "critical"];
const CONFIGS: Record<string, OperationConfig> = {
  procurement: {
    kind: "material-requests", path: "procurement", title: "Material Requests", singular: "material request", permission: "project.materials",
    name: (row) => String(row.code || "Material request"),
    fields: [{ key: "code", label: "Request code" }, { key: "notes", label: "Notes" }],
    statuses: ["draft", "submitted", "approved", "ordered", "received", "cancelled"],
  },
  equipment: {
    kind: "equipment", path: "equipment", title: "Project Equipment", singular: "equipment record", permission: "project.equipment",
    name: (row) => String(row.name || row.code || "Equipment"),
    fields: [{ key: "code", label: "Equipment code" }, { key: "name", label: "Name", required: true }, { key: "equipment_type", label: "Type", required: true }, { key: "daily_cost", label: "Daily cost", type: "number" }, { key: "notes", label: "Notes" }],
    statuses: ["available", "assigned", "maintenance", "retired"],
  },
  expenses: {
    kind: "expenses", path: "expenses", title: "Project Expenses", singular: "expense", permission: "project.expenses",
    name: (row) => String(row.description || "Expense"),
    fields: [{ key: "category", label: "Category", required: true }, { key: "description", label: "Description", required: true }, { key: "amount", label: "Amount", type: "number", required: true }, { key: "expense_date", label: "Expense date", type: "date", required: true }, { key: "notes", label: "Notes" }],
    statuses: ["draft", "submitted", "approved", "rejected", "paid"],
  },
  "change-orders": {
    kind: "change-orders", path: "change-orders", title: "Change Orders", singular: "change order", permission: "project.change_orders",
    name: (row) => String(row.code || row.title || "Change order"),
    fields: [{ key: "code", label: "Change order code" }, { key: "title", label: "Title", required: true }, { key: "description", label: "Description" }, { key: "amount_delta", label: "Value change", type: "number" }, { key: "notes", label: "Notes" }],
    statuses: ["draft", "submitted", "approved", "rejected", "implemented"],
  },
  "site-reports": {
    kind: "site-reports", path: "site-reports", title: "Site Reports", singular: "site report", permission: "project.site_reports",
    name: (row) => String(row.report_date || "Site report"),
    fields: [{ key: "report_date", label: "Report date", type: "date", required: true }, { key: "weather", label: "Weather" }, { key: "summary", label: "Summary", required: true }, { key: "progress_notes", label: "Progress notes" }, { key: "issues_notes", label: "Issues noted" }],
    statuses: ["draft", "submitted"],
  },
  quality: {
    kind: "quality-inspections", path: "quality", title: "Quality Inspections", singular: "inspection", permission: "project.quality",
    name: (row) => String(row.title || "Inspection"),
    fields: [{ key: "title", label: "Title", required: true }, { key: "inspection_date", label: "Inspection date", type: "date", required: true }, { key: "result", label: "Result", type: "select", options: ["pass", "fail", "conditional"], required: true }, { key: "findings", label: "Findings" }, { key: "notes", label: "Notes" }],
    statuses: ["open", "closed"],
  },
  safety: {
    kind: "safety-incidents", path: "safety", title: "Safety Incidents", singular: "safety incident", permission: "project.safety",
    name: (row) => String(row.title || "Safety incident"),
    fields: [{ key: "incident_date", label: "Incident date", type: "date", required: true }, { key: "title", label: "Title", required: true }, { key: "severity", label: "Severity", type: "select", options: LEVELS, required: true }, { key: "description", label: "Description", required: true }, { key: "notes", label: "Notes" }],
    statuses: ["open", "investigating", "closed"],
  },
  risks: {
    kind: "risks", path: "risks", title: "Project Risks", singular: "risk", permission: "project.risks",
    name: (row) => String(row.code || row.title || "Risk"),
    fields: [{ key: "code", label: "Risk code" }, { key: "title", label: "Title", required: true }, { key: "probability", label: "Probability", type: "select", options: ["low", "medium", "high"], required: true }, { key: "impact", label: "Impact", type: "select", options: LEVELS, required: true }, { key: "mitigation_plan", label: "Mitigation plan" }, { key: "notes", label: "Notes" }],
    statuses: ["open", "mitigating", "closed"],
  },
  issues: {
    kind: "issues", path: "issues", title: "Project Issues", singular: "issue", permission: "project.issues",
    name: (row) => String(row.code || row.title || "Issue"),
    fields: [{ key: "code", label: "Issue code" }, { key: "title", label: "Title", required: true }, { key: "description", label: "Description" }, { key: "priority", label: "Priority", type: "select", options: LEVELS }, { key: "notes", label: "Notes" }],
    statuses: ["open", "in_progress", "resolved", "closed"],
  },
  billing: {
    kind: "invoices", path: "billing", title: "Project Billing", singular: "invoice", permission: "project.invoices",
    name: (row) => String(row.invoice_number || "Invoice"),
    fields: [{ key: "invoice_number", label: "Invoice number", required: true }, { key: "invoice_date", label: "Invoice date", type: "date", required: true }, { key: "amount", label: "Amount before tax", type: "number", required: true }, { key: "tax_amount", label: "Tax amount", type: "number" }, { key: "total_amount", label: "Total amount", type: "number", required: true }, { key: "due_date", label: "Due date", type: "date" }, { key: "notes", label: "Notes" }],
    statuses: ["draft", "issued", "paid", "void"],
  },
};

function configFor(path?: string) {
  return CONFIGS[path || ""] || CONFIGS.procurement;
}

function display(value: unknown) {
  if (value == null || value === "") return "—";
  return typeof value === "number" && /amount|cost/.test(String(value)) ? formatCurrency(value) : String(value);
}

export function ProjectOperationsListPage() {
  const { operation } = useParams();
  const config = configFor(operation);
  const navigate = useNavigate();
  const branchId = useAuthStore((s) => s.user?.branch?.id);
  const { hasPermission } = usePermissions();
  const [searchParams] = useSearchParams();
  const projectId = searchParams.get("project_id") || undefined;
  const [rows, setRows] = useState<ProjectOperation[]>([]);
  const [loading, setLoading] = useState(true);
  const reload = useCallback(async () => {
    if (!branchId) return;
    setLoading(true);
    try { setRows((await projectsApi.operations(config.kind, 1, projectId, branchId)).data.results); }
    finally { setLoading(false); }
  }, [branchId, config.kind, projectId]);
  useEffect(() => { void reload(); }, [reload]);
  const columns: Column<ProjectOperation>[] = [
    { key: "record", header: config.singular, cell: (row) => <button type="button" className="text-left font-medium text-primary hover:underline" onClick={() => navigate(`/project/${config.path}/${row.id}`)}>{config.name(row)}</button> },
    { key: "project_id", header: "Project", cell: (row) => String(row.project_id) },
    { key: "status", header: "Status", cell: (row) => <Badge variant="outline">{String(row.status || "—").replace(/_/g, " ")}</Badge> },
    { key: "value", header: "Value", cell: (row) => formatCurrency(Number(row.total_amount ?? row.amount ?? row.amount_delta ?? row.daily_cost ?? 0)) },
    { key: "created_at", header: "Created", cell: (row) => String(row.created_at || "—").slice(0, 10) },
  ];
  return <PageLayout title={config.title} description={`Create, review, and track ${config.title.toLowerCase()}.`} breadcrumbs={["Home", "Project Management", config.title]} actions={hasPermission(`${config.permission}.create`) ? <Button asChild size="sm"><Link to={`/project/${config.path}/new`}><Plus className="mr-2 h-4 w-4" />New {config.singular}</Link></Button> : null}><DataTable columns={columns} data={rows} loading={loading} emptyMessage={`No ${config.title.toLowerCase()} yet.`} /></PageLayout>;
}

export function ProjectOperationFormPage() {
  const { operation, id } = useParams();
  const config = configFor(operation);
  const edit = Boolean(id);
  const navigate = useNavigate();
  const branchId = useAuthStore((s) => s.user?.branch?.id);
  const [projects, setProjects] = useState<Project[]>([]);
  const [values, setValues] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(edit);
  const [saving, setSaving] = useState(false);
  useEffect(() => { if (branchId) projectsApi.list(1, branchId).then((res) => setProjects(res.data.results)).catch(() => undefined); }, [branchId]);
  useEffect(() => {
    if (!id) return;
    projectsApi.operation(config.kind, id).then((res) => {
      const data = res.data;
      setValues(Object.fromEntries([["project_id", String(data.project_id)], ...config.fields.map((field) => [field.key, String(data[field.key] ?? "")])]));
    }).catch((err) => appDialog.alert(err instanceof Error ? err.message : "Record not found.")).finally(() => setLoading(false));
  }, [config, id]);
  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!values.project_id) return;
    setSaving(true);
    const payload = Object.fromEntries(Object.entries(values).map(([key, value]) => [key, ["amount", "total_amount", "tax_amount", "amount_delta", "daily_cost"].includes(key) ? Number(value || 0) : value || undefined]));
    try {
      const res = edit && id ? await projectsApi.updateOperation(config.kind, id, payload) : await projectsApi.createOperation(config.kind, payload);
      navigate(`/project/${config.path}/${res.data.id}`);
    } catch (err) { await appDialog.alert(err instanceof Error ? err.message : "Save failed."); }
    finally { setSaving(false); }
  };
  if (loading) return <PageLayout title="Loading..." breadcrumbs={["Home", "Project Management", config.title]}><div className="h-64 animate-pulse rounded-2xl bg-muted" /></PageLayout>;
  return <PageLayout title={edit ? `Edit ${config.singular}` : `New ${config.singular}`} breadcrumbs={["Home", "Project Management", config.title, edit ? "Edit" : "New"]}><form onSubmit={submit}><FormPageLayout main={<FormSection title="Details"><FormGrid><FormField label="Project" required><Select value={values.project_id || ""} onValueChange={(value) => setValues((current) => ({ ...current, project_id: value }))} disabled={edit}><SelectTrigger><SelectValue placeholder="Select project" /></SelectTrigger><SelectContent>{projects.map((project) => <SelectItem key={project.id} value={project.id}>{project.project_code} — {project.name}</SelectItem>)}</SelectContent></Select></FormField>{config.fields.map((field) => <FormField key={field.key} label={field.label} required={field.required}><OperationInput field={field} value={values[field.key] || ""} onChange={(value) => setValues((current) => ({ ...current, [field.key]: value }))} /></FormField>)}</FormGrid></FormSection>} actions={<FormActions><div className="flex gap-3"><Button type="submit" loading={saving}>{edit ? "Save changes" : `Create ${config.singular}`}</Button><Button type="button" variant="secondary" onClick={() => navigate(`/project/${config.path}`)}>Cancel</Button></div></FormActions>} /></form></PageLayout>;
}

function OperationInput({ field, value, onChange }: { field: Field; value: string; onChange: (value: string) => void }) {
  if (field.type === "select") return <Select value={value} onValueChange={onChange}><SelectTrigger><SelectValue placeholder={`Select ${field.label.toLowerCase()}`} /></SelectTrigger><SelectContent>{field.options?.map((option) => <SelectItem key={option} value={option}>{option.replace(/_/g, " ")}</SelectItem>)}</SelectContent></Select>;
  return <Input type={field.type || "text"} required={field.required} min={field.type === "number" ? "0" : undefined} step={field.type === "number" ? "0.01" : undefined} value={value} onChange={(event) => onChange(event.target.value)} />;
}

export function ProjectOperationDetailPage() {
  const { operation, id } = useParams();
  const config = configFor(operation);
  const navigate = useNavigate();
  const { hasPermission, hasAnyPermission } = usePermissions();
  const [row, setRow] = useState<ProjectOperation | null>(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => { if (id) projectsApi.operation(config.kind, id).then((res) => setRow(res.data)).catch((err) => appDialog.alert(err instanceof Error ? err.message : "Record not found.")).finally(() => setLoading(false)); }, [config.kind, id]);
  const setStatus = async (status: string) => { if (!id) return; try { setRow((await projectsApi.setOperationStatus(config.kind, id, status)).data); } catch (err) { await appDialog.alert(err instanceof Error ? err.message : "Status update failed."); } };
  const remove = async () => { if (!id || !row || !(await appDialog.confirm(`Delete this ${config.singular}?`))) return; try { await projectsApi.deleteOperation(config.kind, id); navigate(`/project/${config.path}`); } catch (err) { await appDialog.alert(err instanceof Error ? err.message : "Delete failed."); } };
  const preview = async () => { if (!id) return; try { const previewData = (await projectsApi.invoiceAccountingPreview(id)).data; await appDialog.alert(`${previewData.note}\n\n${previewData.lines.map((line) => `${line.account_code}: Dr ${formatCurrency(line.debit)} / Cr ${formatCurrency(line.credit)}`).join("\n")}`); } catch (err) { await appDialog.alert(err instanceof Error ? err.message : "Could not load accounting preview."); } };
  const postLedger = async () => {
    if (!id) return;
    const ok = await appDialog.confirm("Post this invoice to the central ledger?");
    if (!ok) return;
    try {
      setRow((await projectsApi.invoicePostAccounting(id)).data);
      await appDialog.alert("Posted to central ledger.");
    } catch (err) {
      await appDialog.alert(err instanceof Error ? err.message : "Ledger posting failed.");
    }
  };
  if (loading || !row) return <PageLayout title={loading ? "Loading..." : config.singular} breadcrumbs={["Home", "Project Management", config.title]}>{loading ? <div className="h-64 animate-pulse rounded-2xl bg-muted" /> : null}</PageLayout>;
  const canUpdate = hasAnyPermission(`${config.permission}.update`, "project.change_orders.approve");
  const posted = Boolean(row.journal_entry_id);
  return <PageLayout title={config.name(row)} description={`Project: ${row.project_id}`} breadcrumbs={["Home", "Project Management", config.title, config.name(row)]} actions={<div className="flex flex-wrap gap-2">{canUpdate ? <Button variant="secondary" onClick={() => navigate(`/project/${config.path}/${row.id}/edit`)}>Edit</Button> : null}{config.kind === "invoices" ? <Button variant="outline" onClick={() => void preview()}>Accounting preview</Button> : null}{config.kind === "invoices" && canUpdate && !posted ? <Button onClick={() => void postLedger()}>Post to ledger</Button> : null}{hasPermission(`${config.permission}.delete`) ? <Button variant="destructive" onClick={() => void remove()}>Delete</Button> : null}<Button variant="secondary" onClick={() => navigate(`/project/${config.path}`)}>Back</Button></div>}><ContentSection title="Details"><div className="grid gap-3 text-sm sm:grid-cols-2">{config.fields.map((field) => <p key={field.key}><span className="text-muted-foreground">{field.label}</span> · {display(row[field.key])}</p>)}<p><span className="text-muted-foreground">Status</span> · <Badge>{String(row.status || "—").replace(/_/g, " ")}</Badge></p>{config.kind === "invoices" ? <p><span className="text-muted-foreground">Ledger</span> · {posted ? `Posted (${String(row.journal_entry_id)})` : "Not posted"}</p> : null}</div></ContentSection>{canUpdate ? <ContentSection title="Status workflow"><div className="flex flex-wrap gap-2">{config.statuses.filter((status) => status !== row.status).map((status) => <Button key={status} size="sm" variant="outline" onClick={() => void setStatus(status)}>Move to {status.replace(/_/g, " ")}</Button>)}</div></ContentSection> : null}</PageLayout>;
}
