import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { Plus, Trash2 } from "lucide-react";
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
  type ProjectBudget,
  type ProjectBudgetLine,
} from "@/services/api/projects";
import { formatCurrency } from "@/utils/cn";

const CATEGORIES = [
  { value: "labor", label: "Labor" },
  { value: "materials", label: "Materials" },
  { value: "equipment", label: "Equipment" },
  { value: "subcontract", label: "Subcontract" },
  { value: "overhead", label: "Overhead" },
  { value: "other", label: "Other" },
];

const EMPTY_LINE = (): ProjectBudgetLine => ({
  category: "other",
  description: "",
  planned_amount: 0,
});

export function ProjectBudgetListPage() {
  const navigate = useNavigate();
  const branchId = useAuthStore((s) => s.user?.branch?.id);
  const [searchParams] = useSearchParams();
  const projectFilter = searchParams.get("project_id") || "";
  const { hasPermission } = usePermissions();
  const canCreate = hasPermission("project.budget.create");
  const [rows, setRows] = useState<ProjectBudget[]>([]);
  const [loading, setLoading] = useState(true);

  const reload = useCallback(async () => {
    if (!branchId) return;
    setLoading(true);
    try {
      const res = await projectsApi.budgets(1, projectFilter || undefined, branchId);
      setRows(res.data.results);
    } finally {
      setLoading(false);
    }
  }, [branchId, projectFilter]);

  useEffect(() => {
    void reload();
  }, [reload]);

  const columns: Column<ProjectBudget>[] = [
    {
      key: "name",
      header: "Budget",
      cell: (row) => (
        <button
          type="button"
          className="font-medium text-primary hover:underline"
          onClick={() => navigate(`/project/budgets/${row.id}`)}
        >
          {row.name}
        </button>
      ),
    },
    { key: "project_code", header: "Project", cell: (row) => row.project_code },
    { key: "version", header: "Version", cell: (row) => `v${row.version}` },
    { key: "status", header: "Status", cell: (row) => <Badge variant="secondary">{row.status}</Badge> },
    { key: "total_planned", header: "Planned", cell: (row) => formatCurrency(row.total_planned) },
    { key: "variance", header: "Variance", cell: (row) => formatCurrency(row.variance) },
  ];

  return (
    <PageLayout
      title="Project Budgets"
      description="Versioned budgets with category lines and approval workflow."
      breadcrumbs={["Home", "Project Management", "Budgets"]}
      actions={
        canCreate ? (
          <Button asChild size="sm">
            <Link to={`/project/budgets/new${projectFilter ? `?project_id=${projectFilter}` : ""}`}>
              <Plus className="mr-2 h-4 w-4" />
              New budget
            </Link>
          </Button>
        ) : null
      }
    >
      <DataTable columns={columns} data={rows} loading={loading} emptyMessage="No budgets yet." />
    </PageLayout>
  );
}

export function ProjectBudgetFormPage({ editId }: { editId?: string }) {
  const navigate = useNavigate();
  const branchId = useAuthStore((s) => s.user?.branch?.id);
  const [searchParams] = useSearchParams();
  const [loading, setLoading] = useState(Boolean(editId));
  const [saving, setSaving] = useState(false);
  const [projects, setProjects] = useState<Project[]>([]);
  const [form, setForm] = useState({
    project_id: searchParams.get("project_id") || "",
    name: "",
    notes: "",
    currency: "USD",
    lines: [EMPTY_LINE()],
  });

  useEffect(() => {
    if (!branchId) return;
    projectsApi.list(1, branchId).then((res) => setProjects(res.data.results)).catch(() => undefined);
  }, [branchId]);

  useEffect(() => {
    if (!editId) return;
    projectsApi
      .budget(editId)
      .then((res) => {
        const row = res.data;
        setForm({
          project_id: row.project_id,
          name: row.name,
          notes: row.notes || "",
          currency: row.currency || "USD",
          lines: row.lines.length ? row.lines : [EMPTY_LINE()],
        });
      })
      .catch((err) => appDialog.alert(err instanceof Error ? err.message : "Budget not found."))
      .finally(() => setLoading(false));
  }, [editId]);

  const updateLine = (index: number, patch: Partial<ProjectBudgetLine>) => {
    setForm((prev) => {
      const lines = [...prev.lines];
      lines[index] = { ...lines[index], ...patch };
      return { ...prev, lines };
    });
  };

  const addLine = () => setForm((prev) => ({ ...prev, lines: [...prev.lines, EMPTY_LINE()] }));

  const removeLine = (index: number) =>
    setForm((prev) => ({ ...prev, lines: prev.lines.filter((_, i) => i !== index) }));

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.project_id || !form.name.trim()) return;
    setSaving(true);
    try {
      const payload = {
        project_id: form.project_id,
        name: form.name.trim(),
        notes: form.notes || undefined,
        currency: form.currency,
        lines: form.lines
          .filter((line) => line.description.trim())
          .map((line, idx) => ({
            category: line.category,
            description: line.description.trim(),
            planned_amount: Number(line.planned_amount) || 0,
            sort_order: idx,
            notes: line.notes || undefined,
          })),
      };
      if (editId) {
        const res = await projectsApi.updateBudget(editId, payload);
        navigate(`/project/budgets/${res.data.id}`);
      } else {
        const res = await projectsApi.createBudget(payload);
        navigate(`/project/budgets/${res.data.id}`);
      }
    } catch (err) {
      await appDialog.alert(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <PageLayout title="Loading..." breadcrumbs={["Home", "Project Management", "Budgets"]}>
        <div className="h-64 animate-pulse rounded-2xl bg-muted" />
      </PageLayout>
    );
  }

  return (
    <PageLayout
      title={editId ? "Edit budget" : "New budget"}
      breadcrumbs={["Home", "Project Management", "Budgets", editId ? "Edit" : "New"]}
    >
      <form onSubmit={onSubmit}>
        <FormPageLayout
          main={
            <>
              <FormSection title="Budget header">
                <FormGrid>
                  <FormField label="Project" required>
                    <Select
                      value={form.project_id}
                      onValueChange={(v) => setForm((s) => ({ ...s, project_id: v }))}
                      disabled={Boolean(editId)}
                    >
                      <SelectTrigger><SelectValue placeholder="Select project" /></SelectTrigger>
                      <SelectContent>
                        {projects.map((p) => (
                          <SelectItem key={p.id} value={p.id}>{p.project_code} — {p.name}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </FormField>
                  <FormField label="Name" required>
                    <Input required value={form.name} onChange={(e) => setForm((s) => ({ ...s, name: e.target.value }))} />
                  </FormField>
                  <FormField label="Currency">
                    <Input value={form.currency} onChange={(e) => setForm((s) => ({ ...s, currency: e.target.value }))} />
                  </FormField>
                  <FormField label="Notes" className="md:col-span-2 xl:col-span-3">
                    <Input value={form.notes} onChange={(e) => setForm((s) => ({ ...s, notes: e.target.value }))} />
                  </FormField>
                </FormGrid>
              </FormSection>
              <FormSection title="Budget lines">
                <div className="space-y-3">
                  {form.lines.map((line, index) => (
                    <div key={index} className="grid gap-3 rounded-xl border p-3 sm:grid-cols-12">
                      <div className="sm:col-span-3">
                        <Select value={line.category} onValueChange={(v) => updateLine(index, { category: v })}>
                          <SelectTrigger><SelectValue /></SelectTrigger>
                          <SelectContent>
                            {CATEGORIES.map((c) => (
                              <SelectItem key={c.value} value={c.value}>{c.label}</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                      <div className="sm:col-span-5">
                        <Input
                          placeholder="Description"
                          value={line.description}
                          onChange={(e) => updateLine(index, { description: e.target.value })}
                        />
                      </div>
                      <div className="sm:col-span-3">
                        <Input
                          type="number"
                          min="0"
                          step="0.01"
                          placeholder="Planned amount"
                          value={line.planned_amount || ""}
                          onChange={(e) => updateLine(index, { planned_amount: Number(e.target.value) || 0 })}
                        />
                      </div>
                      <div className="sm:col-span-1 flex items-center">
                        <Button type="button" variant="ghost" size="icon" onClick={() => removeLine(index)}>
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  ))}
                  <Button type="button" variant="outline" size="sm" onClick={addLine}>
                    Add line
                  </Button>
                </div>
              </FormSection>
            </>
          }
          actions={
            <FormActions>
              <div className="flex gap-3">
                <Button type="submit" loading={saving}>{editId ? "Save changes" : "Create budget"}</Button>
                <Button type="button" variant="secondary" onClick={() => navigate("/project/budgets")}>
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

export function ProjectBudgetNewPage() {
  return <ProjectBudgetFormPage />;
}

export function ProjectBudgetEditPage() {
  const { id } = useParams();
  return <ProjectBudgetFormPage editId={id} />;
}

export function ProjectBudgetDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { hasAnyPermission } = usePermissions();
  const canUpdate = hasAnyPermission("project.budget.update", "project.budget.approve");
  const [row, setRow] = useState<ProjectBudget | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    projectsApi
      .budget(id)
      .then((res) => setRow(res.data))
      .catch((err) => appDialog.alert(err instanceof Error ? err.message : "Budget not found."))
      .finally(() => setLoading(false));
  }, [id]);

  const setStatus = async (status: string) => {
    if (!id) return;
    try {
      const res = await projectsApi.setBudgetStatus(id, status);
      setRow(res.data);
    } catch (err) {
      await appDialog.alert(err instanceof Error ? err.message : "Status update failed");
    }
  };

  if (loading || !row) {
    return (
      <PageLayout title={loading ? "Loading..." : "Budget"} breadcrumbs={["Home", "Project Management", "Budgets"]}>
        {loading ? <div className="h-64 animate-pulse rounded-2xl bg-muted" /> : null}
      </PageLayout>
    );
  }

  const nextStatuses: Record<string, string[]> = {
    draft: ["submitted"],
    submitted: ["approved", "draft"],
    approved: ["locked"],
  };

  return (
    <PageLayout
      title={row.name}
      description={`${row.project_code} · v${row.version}`}
      breadcrumbs={["Home", "Project Management", "Budgets", row.name]}
      actions={
        <div className="flex gap-2">
          {canUpdate && row.status === "draft" ? (
            <Button variant="secondary" onClick={() => navigate(`/project/budgets/${row.id}/edit`)}>
              Edit
            </Button>
          ) : null}
          <Button variant="secondary" onClick={() => navigate("/project/budgets")}>
            Back
          </Button>
        </div>
      }
    >
      <ContentSection title="Summary">
        <div className="grid gap-3 sm:grid-cols-2 text-sm">
          <p><span className="text-muted-foreground">Status</span> · <Badge>{row.status}</Badge></p>
          <p><span className="text-muted-foreground">Total planned</span> · {formatCurrency(row.total_planned)}</p>
          <p><span className="text-muted-foreground">Total actual</span> · {formatCurrency(row.total_actual)}</p>
          <p><span className="text-muted-foreground">Variance</span> · {formatCurrency(row.variance)}</p>
        </div>
      </ContentSection>
      <ContentSection title="Lines">
        <DataTable
          columns={[
            { key: "category", header: "Category", cell: (line) => line.category },
            { key: "description", header: "Description", cell: (line) => line.description },
            { key: "planned", header: "Planned", cell: (line) => formatCurrency(line.planned_amount) },
            { key: "actual", header: "Actual", cell: (line) => formatCurrency(line.actual_amount || 0) },
          ]}
          data={row.lines}
          emptyMessage="No lines."
        />
      </ContentSection>
      {canUpdate && (nextStatuses[row.status] || []).length > 0 ? (
        <ContentSection title="Workflow">
          <div className="flex flex-wrap gap-2">
            {(nextStatuses[row.status] || []).map((status) => (
              <Button key={status} size="sm" variant="outline" onClick={() => void setStatus(status)}>
                Move to {status}
              </Button>
            ))}
          </div>
        </ContentSection>
      ) : null}
    </PageLayout>
  );
}
