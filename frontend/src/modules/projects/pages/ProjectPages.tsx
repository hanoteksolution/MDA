import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
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
import { projectsApi, type Project } from "@/services/api/projects";
import { formatCurrency } from "@/utils/cn";

const PROJECT_TYPES = [
  { value: "general", label: "General" },
  { value: "construction", label: "Construction" },
  { value: "real_estate", label: "Real Estate" },
  { value: "infrastructure", label: "Infrastructure" },
  { value: "it", label: "IT" },
  { value: "professional", label: "Professional Services" },
];

const STATUS_OPTIONS = [
  "draft",
  "planning",
  "approved",
  "active",
  "on_hold",
  "at_risk",
  "delayed",
  "completed",
  "cancelled",
  "closed",
];

function statusBadge(status: string) {
  const variant =
    status === "active"
      ? "default"
      : status === "completed" || status === "closed"
        ? "secondary"
        : status === "at_risk" || status === "delayed"
          ? "destructive"
          : "outline";
  return <Badge variant={variant}>{status.replace(/_/g, " ")}</Badge>;
}

export function ProjectListPage() {
  const navigate = useNavigate();
  const branchId = useAuthStore((s) => s.user?.branch?.id);
  const { hasPermission } = usePermissions();
  const canCreate = hasPermission("projects.create");
  const [rows, setRows] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");

  const reload = useCallback(async () => {
    if (!branchId) return;
    setLoading(true);
    try {
      const res = await projectsApi.list(1, branchId, {
        search: search || undefined,
        status: statusFilter === "all" ? undefined : statusFilter,
      });
      setRows(res.data.results);
    } finally {
      setLoading(false);
    }
  }, [branchId, search, statusFilter]);

  useEffect(() => {
    void reload();
  }, [reload]);

  const columns: Column<Project>[] = [
    {
      key: "project_code",
      header: "Code",
      cell: (row) => (
        <button
          type="button"
          className="font-medium text-primary hover:underline"
          onClick={() => navigate(`/project/projects/${row.id}`)}
        >
          {row.project_code}
        </button>
      ),
    },
    { key: "name", header: "Name", cell: (row) => row.name },
    { key: "project_type", header: "Type", cell: (row) => row.project_type.replace(/_/g, " ") },
    { key: "status", header: "Status", cell: (row) => statusBadge(row.status) },
    { key: "priority", header: "Priority", cell: (row) => row.priority },
    {
      key: "budget",
      header: "Budget",
      cell: (row) => formatCurrency(row.budget),
    },
    {
      key: "progress",
      header: "Progress",
      cell: (row) => `${row.progress_percent}%`,
    },
  ];

  return (
    <PageLayout
      title="Projects"
      description="Manage project portfolio, lifecycle, and financial baselines."
      breadcrumbs={["Home", "Project Management", "Projects"]}
      actions={
        canCreate ? (
          <Button asChild size="sm">
            <Link to="/project/projects/new">
              <Plus className="mr-2 h-4 w-4" />
              New project
            </Link>
          </Button>
        ) : null
      }
    >
      <ContentSection title="Project list">
        <div className="mb-4 flex flex-wrap gap-3">
          <Input
            placeholder="Search code, name, owner, location..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="max-w-xs"
          />
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-40">
              <SelectValue placeholder="Status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All statuses</SelectItem>
              {STATUS_OPTIONS.map((s) => (
                <SelectItem key={s} value={s}>
                  {s.replace(/_/g, " ")}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button variant="secondary" onClick={() => void reload()}>
            Refresh
          </Button>
        </div>
        <DataTable columns={columns} data={rows} loading={loading} emptyMessage="No projects yet." />
      </ContentSection>
    </PageLayout>
  );
}

export function ProjectFormPage({ editId }: { editId?: string }) {
  const navigate = useNavigate();
  const branchId = useAuthStore((s) => s.user?.branch?.id);
  const [loading, setLoading] = useState(Boolean(editId));
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({
    name: "",
    project_code: "",
    project_type: "general",
    owner_name: "",
    location: "",
    description: "",
    start_date: "",
    planned_end_date: "",
    priority: "medium",
    budget: "",
    contract_value: "",
    expected_revenue: "",
    cost_estimate: "",
    currency: "USD",
    tax_rate: "",
    payment_terms: "",
    notes: "",
  });

  useEffect(() => {
    if (!editId) return;
    projectsApi
      .get(editId)
      .then((res) => {
        const row = res.data;
        setForm({
          name: row.name || "",
          project_code: row.project_code || "",
          project_type: row.project_type || "general",
          owner_name: row.owner_name || "",
          location: row.location || "",
          description: row.description || "",
          start_date: row.start_date || "",
          planned_end_date: row.planned_end_date || "",
          priority: row.priority || "medium",
          budget: String(row.budget || ""),
          contract_value: String(row.contract_value || ""),
          expected_revenue: String(row.expected_revenue || ""),
          cost_estimate: String(row.cost_estimate || ""),
          currency: row.currency || "USD",
          tax_rate: String(row.tax_rate || ""),
          payment_terms: row.payment_terms || "",
          notes: row.notes || "",
        });
      })
      .catch((err) => appDialog.alert(err instanceof Error ? err.message : "Project not found."))
      .finally(() => setLoading(false));
  }, [editId]);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!branchId) return;
    setSaving(true);
    try {
      const payload = {
        branch_id: branchId,
        name: form.name.trim(),
        project_code: form.project_code.trim() || undefined,
        project_type: form.project_type,
        owner_name: form.owner_name.trim() || undefined,
        location: form.location.trim() || undefined,
        description: form.description || undefined,
        start_date: form.start_date || undefined,
        planned_end_date: form.planned_end_date || undefined,
        priority: form.priority,
        budget: Number(form.budget) || 0,
        contract_value: Number(form.contract_value) || 0,
        expected_revenue: Number(form.expected_revenue) || 0,
        cost_estimate: Number(form.cost_estimate) || 0,
        currency: form.currency || "USD",
        tax_rate: Number(form.tax_rate) || 0,
        payment_terms: form.payment_terms || undefined,
        notes: form.notes || undefined,
      };
      if (editId) {
        const res = await projectsApi.update(editId, payload);
        navigate(`/project/projects/${res.data.id}`);
      } else {
        const res = await projectsApi.create(payload);
        navigate(`/project/projects/${res.data.id}`);
      }
    } catch (err) {
      await appDialog.alert(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <PageLayout title="Loading..." breadcrumbs={["Home", "Project Management", "Projects"]}>
        <div className="h-64 animate-pulse rounded-2xl bg-muted" />
      </PageLayout>
    );
  }

  return (
    <PageLayout
      title={editId ? "Edit project" : "New project"}
      breadcrumbs={["Home", "Project Management", "Projects", editId ? "Edit" : "New"]}
    >
      <form onSubmit={onSubmit}>
        <FormPageLayout
          main={
            <>
              <FormSection title="Basic information">
                <FormGrid>
                  <FormField label="Name" required>
                    <Input required value={form.name} onChange={(e) => setForm((s) => ({ ...s, name: e.target.value }))} />
                  </FormField>
                  <FormField label="Project code">
                    <Input
                      value={form.project_code}
                      onChange={(e) => setForm((s) => ({ ...s, project_code: e.target.value }))}
                      placeholder="Auto-generated if empty"
                    />
                  </FormField>
                  <FormField label="Type">
                    <Select value={form.project_type} onValueChange={(v) => setForm((s) => ({ ...s, project_type: v }))}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        {PROJECT_TYPES.map((t) => (
                          <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </FormField>
                  <FormField label="Priority">
                    <Select value={form.priority} onValueChange={(v) => setForm((s) => ({ ...s, priority: v }))}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="low">Low</SelectItem>
                        <SelectItem value="medium">Medium</SelectItem>
                        <SelectItem value="high">High</SelectItem>
                        <SelectItem value="critical">Critical</SelectItem>
                      </SelectContent>
                    </Select>
                  </FormField>
                  <FormField label="Owner / client name">
                    <Input value={form.owner_name} onChange={(e) => setForm((s) => ({ ...s, owner_name: e.target.value }))} />
                  </FormField>
                  <FormField label="Location">
                    <Input value={form.location} onChange={(e) => setForm((s) => ({ ...s, location: e.target.value }))} />
                  </FormField>
                  <FormField label="Start date">
                    <Input type="date" value={form.start_date} onChange={(e) => setForm((s) => ({ ...s, start_date: e.target.value }))} />
                  </FormField>
                  <FormField label="Planned end date">
                    <Input type="date" value={form.planned_end_date} onChange={(e) => setForm((s) => ({ ...s, planned_end_date: e.target.value }))} />
                  </FormField>
                  <FormField label="Description" className="md:col-span-2 xl:col-span-3">
                    <Input value={form.description} onChange={(e) => setForm((s) => ({ ...s, description: e.target.value }))} />
                  </FormField>
                </FormGrid>
              </FormSection>
              <FormSection title="Financial baseline">
                <FormGrid>
                  <FormField label="Budget">
                    <Input type="number" min="0" step="0.01" value={form.budget} onChange={(e) => setForm((s) => ({ ...s, budget: e.target.value }))} />
                  </FormField>
                  <FormField label="Contract value">
                    <Input type="number" min="0" step="0.01" value={form.contract_value} onChange={(e) => setForm((s) => ({ ...s, contract_value: e.target.value }))} />
                  </FormField>
                  <FormField label="Expected revenue">
                    <Input type="number" min="0" step="0.01" value={form.expected_revenue} onChange={(e) => setForm((s) => ({ ...s, expected_revenue: e.target.value }))} />
                  </FormField>
                  <FormField label="Cost estimate">
                    <Input type="number" min="0" step="0.01" value={form.cost_estimate} onChange={(e) => setForm((s) => ({ ...s, cost_estimate: e.target.value }))} />
                  </FormField>
                  <FormField label="Currency">
                    <Input value={form.currency} onChange={(e) => setForm((s) => ({ ...s, currency: e.target.value }))} />
                  </FormField>
                  <FormField label="Tax rate (%)">
                    <Input type="number" min="0" step="0.01" value={form.tax_rate} onChange={(e) => setForm((s) => ({ ...s, tax_rate: e.target.value }))} />
                  </FormField>
                  <FormField label="Payment terms" className="md:col-span-2 xl:col-span-3">
                    <Input value={form.payment_terms} onChange={(e) => setForm((s) => ({ ...s, payment_terms: e.target.value }))} />
                  </FormField>
                  <FormField label="Notes" className="md:col-span-2 xl:col-span-3">
                    <Input value={form.notes} onChange={(e) => setForm((s) => ({ ...s, notes: e.target.value }))} />
                  </FormField>
                </FormGrid>
              </FormSection>
            </>
          }
          actions={
            <FormActions>
              <div className="flex gap-3">
                <Button type="submit" loading={saving}>{editId ? "Save changes" : "Create project"}</Button>
                <Button type="button" variant="secondary" onClick={() => navigate("/project/projects")}>
                  Cancel
                </Button>
              </div>
            </FormActions>
          }
        />
      </form>
    </PageLayout>
  );
}

export function ProjectEditPage() {
  const { id } = useParams();
  return <ProjectFormPage editId={id} />;
}

export function ProjectDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { hasAnyPermission } = usePermissions();
  const canUpdate = hasAnyPermission("projects.update", "projects.approve");
  const canArchive = hasAnyPermission("projects.delete", "projects.archive");
  const canCreate = hasAnyPermission("projects.create");
  const canBudget = hasAnyPermission("project.budget.create");
  const canWbs = hasAnyPermission("project.wbs.view");
  const [row, setRow] = useState<Project | null>(null);
  const [loading, setLoading] = useState(true);

  const reload = useCallback(async () => {
    if (!id) return;
    const res = await projectsApi.get(id);
    setRow(res.data);
  }, [id]);

  useEffect(() => {
    if (!id) return;
    reload()
      .catch((err) => appDialog.alert(err instanceof Error ? err.message : "Project not found."))
      .finally(() => setLoading(false));
  }, [id, reload]);

  const advanceStatus = async (status: string) => {
    if (!id) return;
    try {
      const res = await projectsApi.setStatus(id, status);
      setRow(res.data);
    } catch (err) {
      await appDialog.alert(err instanceof Error ? err.message : "Status update failed");
    }
  };

  const archiveProject = async () => {
    if (!id || !row) return;
    const ok = await appDialog.confirm(`Archive project "${row.name}"?`);
    if (!ok) return;
    await projectsApi.archive(id);
    navigate("/project/projects");
  };

  const duplicateProject = async () => {
    if (!id) return;
    try {
      const res = await projectsApi.duplicate(id);
      navigate(`/project/projects/${res.data.id}`);
    } catch (err) {
      await appDialog.alert(err instanceof Error ? err.message : "Duplicate failed");
    }
  };

  if (loading || !row) {
    return (
      <PageLayout title={loading ? "Loading..." : "Project"} breadcrumbs={["Home", "Project Management", "Projects"]}>
        {loading ? <div className="h-64 animate-pulse rounded-2xl bg-muted" /> : null}
      </PageLayout>
    );
  }

  const nextStatuses: Record<string, string[]> = {
    draft: ["planning", "cancelled"],
    planning: ["approved", "cancelled"],
    approved: ["active", "cancelled"],
    active: ["on_hold", "at_risk", "delayed", "completed", "cancelled"],
    on_hold: ["active", "cancelled"],
    at_risk: ["active", "delayed", "cancelled"],
    delayed: ["active", "completed", "cancelled"],
    completed: ["closed"],
  };

  return (
    <PageLayout
      title={row.name}
      description={`${row.project_code} · ${row.project_type.replace(/_/g, " ")}`}
      breadcrumbs={["Home", "Project Management", "Projects", row.project_code]}
      actions={
        <div className="flex flex-wrap gap-2">
          {canUpdate ? (
            <Button variant="secondary" onClick={() => navigate(`/project/projects/${row.id}/edit`)}>
              Edit
            </Button>
          ) : null}
          {canWbs ? (
            <Button variant="outline" onClick={() => navigate(`/project/wbs?project_id=${row.id}`)}>
              WBS tree
            </Button>
          ) : null}
          {canBudget ? (
            <Button variant="outline" onClick={() => navigate(`/project/budgets/new?project_id=${row.id}`)}>
              Add budget
            </Button>
          ) : null}
          {canCreate ? (
            <Button variant="outline" onClick={() => void duplicateProject()}>
              Duplicate
            </Button>
          ) : null}
          {canArchive ? (
            <Button variant="destructive" onClick={() => void archiveProject()}>
              Archive
            </Button>
          ) : null}
          <Button variant="secondary" onClick={() => navigate("/project/projects")}>
            Back
          </Button>
        </div>
      }
    >
      <ContentSection title="Overview">
        <div className="grid gap-3 sm:grid-cols-2 text-sm">
          <p><span className="text-muted-foreground">Status</span> · {statusBadge(row.status)}</p>
          <p><span className="text-muted-foreground">Health</span> · {row.health.replace(/_/g, " ")}</p>
          <p><span className="text-muted-foreground">Priority</span> · {row.priority}</p>
          <p><span className="text-muted-foreground">Progress</span> · {row.progress_percent}%</p>
          <p><span className="text-muted-foreground">Owner</span> · {row.owner_name || "—"}</p>
          <p><span className="text-muted-foreground">Location</span> · {row.location || "—"}</p>
          <p><span className="text-muted-foreground">Start</span> · {row.start_date || "—"}</p>
          <p><span className="text-muted-foreground">Planned end</span> · {row.planned_end_date || "—"}</p>
        </div>
      </ContentSection>
      <ContentSection title="Financials">
        <div className="grid gap-3 sm:grid-cols-2 text-sm">
          <p><span className="text-muted-foreground">Budget</span> · {formatCurrency(row.budget)}</p>
          <p><span className="text-muted-foreground">Contract</span> · {formatCurrency(row.contract_value)}</p>
          <p><span className="text-muted-foreground">Expected revenue</span> · {formatCurrency(row.expected_revenue)}</p>
          <p><span className="text-muted-foreground">Cost estimate</span> · {formatCurrency(row.cost_estimate)}</p>
          <p><span className="text-muted-foreground">Profit estimate</span> · {formatCurrency(row.profit_estimate)}</p>
          <p><span className="text-muted-foreground">Payment terms</span> · {row.payment_terms || "—"}</p>
        </div>
      </ContentSection>
      {row.description ? (
        <ContentSection title="Description">
          <p className="text-sm text-muted-foreground">{row.description}</p>
        </ContentSection>
      ) : null}
      {canUpdate && (nextStatuses[row.status] || []).length > 0 ? (
        <ContentSection title="Workflow">
          <div className="flex flex-wrap gap-2">
            {(nextStatuses[row.status] || []).map((status) => (
              <Button key={status} size="sm" variant="outline" onClick={() => void advanceStatus(status)}>
                Move to {status.replace(/_/g, " ")}
              </Button>
            ))}
          </div>
        </ContentSection>
      ) : null}
    </PageLayout>
  );
}

export function ProjectFormNewPage() {
  return <ProjectFormPage />;
}
