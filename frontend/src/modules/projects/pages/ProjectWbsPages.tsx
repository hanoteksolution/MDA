import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { ChevronRight, Plus } from "lucide-react";
import { PageLayout } from "@/components/layout/PageLayout";
import { ContentSection } from "@/components/layout/ContentSection";
import { FormActions, FormPageLayout } from "@/components/forms/FormPageLayout";
import { FormField, FormGrid, FormSection } from "@/components/forms/FormField";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { appDialog } from "@/components/feedback/AppDialog";
import { useAuthStore } from "@/store/authStore";
import { usePermissions } from "@/hooks/usePermissions";
import { projectsApi, type Project, type WbsNode } from "@/services/api/projects";
import { formatCurrency } from "@/utils/cn";

const NODE_TYPES = [
  { value: "phase", label: "Phase" },
  { value: "deliverable", label: "Deliverable" },
  { value: "work_package", label: "Work Package" },
  { value: "activity", label: "Activity" },
];

const STATUS_OPTIONS = [
  "not_started",
  "in_progress",
  "completed",
  "on_hold",
  "cancelled",
];

function statusBadge(status: string) {
  const variant =
    status === "completed"
      ? "secondary"
      : status === "in_progress"
        ? "default"
        : status === "cancelled"
          ? "destructive"
          : "outline";
  return <Badge variant={variant}>{status.replace(/_/g, " ")}</Badge>;
}

function WbsTreeRows({
  nodes,
  depth = 0,
  onSelect,
}: {
  nodes: WbsNode[];
  depth?: number;
  onSelect: (node: WbsNode) => void;
}) {
  return (
    <>
      {nodes.map((node) => (
        <div key={node.id}>
          <button
            type="button"
            className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm hover:bg-muted"
            style={{ paddingLeft: `${depth * 20 + 12}px` }}
            onClick={() => onSelect(node)}
          >
            {node.children?.length ? <ChevronRight className="h-4 w-4 shrink-0" /> : <span className="w-4" />}
            <span className="font-medium text-primary">{node.code}</span>
            <span>{node.name}</span>
            <span className="ml-auto flex items-center gap-2">
              {statusBadge(node.status)}
              <span className="text-muted-foreground">{node.progress_percent}%</span>
            </span>
          </button>
          {node.children?.length ? (
            <WbsTreeRows nodes={node.children} depth={depth + 1} onSelect={onSelect} />
          ) : null}
        </div>
      ))}
    </>
  );
}

export function ProjectWbsListPage() {
  const navigate = useNavigate();
  const branchId = useAuthStore((s) => s.user?.branch?.id);
  const [searchParams, setSearchParams] = useSearchParams();
  const projectId = searchParams.get("project_id") || "";
  const { hasPermission } = usePermissions();
  const canCreate = hasPermission("project.wbs.create");
  const [projects, setProjects] = useState<Project[]>([]);
  const [tree, setTree] = useState<WbsNode[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!branchId) return;
    projectsApi.list(1, branchId).then((res) => {
      setProjects(res.data.results);
      if (!projectId && res.data.results[0]) {
        setSearchParams({ project_id: res.data.results[0].id });
      }
    }).catch(() => undefined);
  }, [branchId, projectId, setSearchParams]);

  const reload = useCallback(async () => {
    if (!branchId || !projectId) {
      setTree([]);
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const res = await projectsApi.wbsTree(projectId, branchId);
      setTree(res.data);
    } finally {
      setLoading(false);
    }
  }, [branchId, projectId]);

  useEffect(() => {
    void reload();
  }, [reload]);

  const selectedProject = projects.find((p) => p.id === projectId);

  return (
    <PageLayout
      title="Work Breakdown Structure"
      description="Hierarchical decomposition of project scope into phases, packages, and activities."
      breadcrumbs={["Home", "Project Management", "WBS"]}
      actions={
        canCreate && projectId ? (
          <Button asChild size="sm">
            <Link to={`/project/wbs/new?project_id=${projectId}`}>
              <Plus className="mr-2 h-4 w-4" />
              New node
            </Link>
          </Button>
        ) : null
      }
    >
      <ContentSection title="Project scope tree">
        <div className="mb-4 flex flex-wrap gap-3">
          <Select
            value={projectId}
            onValueChange={(v) => setSearchParams({ project_id: v })}
          >
            <SelectTrigger className="w-72">
              <SelectValue placeholder="Select project" />
            </SelectTrigger>
            <SelectContent>
              {projects.map((p) => (
                <SelectItem key={p.id} value={p.id}>{p.project_code} — {p.name}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button variant="secondary" onClick={() => void reload()}>Refresh</Button>
        </div>
        {selectedProject ? (
          <p className="mb-3 text-sm text-muted-foreground">
            {selectedProject.project_code} · {selectedProject.name}
          </p>
        ) : null}
        {loading ? (
          <div className="h-48 animate-pulse rounded-2xl bg-muted" />
        ) : tree.length ? (
          <div className="rounded-xl border">
            <WbsTreeRows nodes={tree} onSelect={(node) => navigate(`/project/wbs/${node.id}`)} />
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">No WBS nodes for this project yet.</p>
        )}
      </ContentSection>
    </PageLayout>
  );
}

export function ProjectWbsFormPage({ editId }: { editId?: string }) {
  const navigate = useNavigate();
  const branchId = useAuthStore((s) => s.user?.branch?.id);
  const [searchParams] = useSearchParams();
  const [loading, setLoading] = useState(Boolean(editId));
  const [saving, setSaving] = useState(false);
  const [projects, setProjects] = useState<Project[]>([]);
  const [parents, setParents] = useState<WbsNode[]>([]);
  const [form, setForm] = useState({
    project_id: searchParams.get("project_id") || "",
    parent_id: searchParams.get("parent_id") || "",
    code: "",
    name: "",
    node_type: "work_package",
    description: "",
    status: "not_started",
    sort_order: "0",
    planned_start: "",
    planned_end: "",
    progress_percent: "0",
    estimated_hours: "",
    estimated_cost: "",
    notes: "",
  });

  useEffect(() => {
    if (!branchId) return;
    projectsApi.list(1, branchId).then((res) => setProjects(res.data.results)).catch(() => undefined);
  }, [branchId]);

  useEffect(() => {
    if (!form.project_id || !branchId) return;
    projectsApi.wbsList(1, form.project_id, branchId).then((res) => setParents(res.data.results)).catch(() => undefined);
  }, [form.project_id, branchId]);

  useEffect(() => {
    if (!editId) return;
    projectsApi
      .wbsGet(editId)
      .then((res) => {
        const row = res.data;
        setForm({
          project_id: row.project_id,
          parent_id: row.parent_id || "",
          code: row.code,
          name: row.name,
          node_type: row.node_type,
          description: row.description || "",
          status: row.status,
          sort_order: String(row.sort_order || 0),
          planned_start: row.planned_start || "",
          planned_end: row.planned_end || "",
          progress_percent: String(row.progress_percent || 0),
          estimated_hours: String(row.estimated_hours || ""),
          estimated_cost: String(row.estimated_cost || ""),
          notes: row.notes || "",
        });
      })
      .catch((err) => appDialog.alert(err instanceof Error ? err.message : "WBS node not found."))
      .finally(() => setLoading(false));
  }, [editId]);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.project_id || !form.name.trim()) return;
    setSaving(true);
    try {
      const payload = {
        project_id: form.project_id,
        parent_id: form.parent_id || null,
        code: form.code.trim() || undefined,
        name: form.name.trim(),
        node_type: form.node_type,
        description: form.description || undefined,
        status: form.status,
        sort_order: Number(form.sort_order) || 0,
        planned_start: form.planned_start || undefined,
        planned_end: form.planned_end || undefined,
        progress_percent: Number(form.progress_percent) || 0,
        estimated_hours: Number(form.estimated_hours) || 0,
        estimated_cost: Number(form.estimated_cost) || 0,
        notes: form.notes || undefined,
      };
      if (editId) {
        const res = await projectsApi.wbsUpdate(editId, payload);
        navigate(`/project/wbs/${res.data.id}`);
      } else {
        const res = await projectsApi.wbsCreate(payload);
        navigate(`/project/wbs/${res.data.id}`);
      }
    } catch (err) {
      await appDialog.alert(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <PageLayout title="Loading..." breadcrumbs={["Home", "Project Management", "WBS"]}>
        <div className="h-64 animate-pulse rounded-2xl bg-muted" />
      </PageLayout>
    );
  }

  return (
    <PageLayout
      title={editId ? "Edit WBS node" : "New WBS node"}
      breadcrumbs={["Home", "Project Management", "WBS", editId ? "Edit" : "New"]}
    >
      <form onSubmit={onSubmit}>
        <FormPageLayout
          main={
            <FormSection title="Node details">
              <FormGrid>
                <FormField label="Project" required>
                  <Select
                    value={form.project_id}
                    onValueChange={(v) => setForm((s) => ({ ...s, project_id: v, parent_id: "" }))}
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
                <FormField label="Parent node">
                  <Select
                    value={form.parent_id || "__root__"}
                    onValueChange={(v) => setForm((s) => ({ ...s, parent_id: v === "__root__" ? "" : v }))}
                  >
                    <SelectTrigger><SelectValue placeholder="Root level" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="__root__">Root level</SelectItem>
                      {parents.filter((p) => p.id !== editId).map((p) => (
                        <SelectItem key={p.id} value={p.id}>{p.code} — {p.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </FormField>
                <FormField label="Code">
                  <Input value={form.code} onChange={(e) => setForm((s) => ({ ...s, code: e.target.value }))} placeholder="Auto-generated if empty" />
                </FormField>
                <FormField label="Name" required>
                  <Input required value={form.name} onChange={(e) => setForm((s) => ({ ...s, name: e.target.value }))} />
                </FormField>
                <FormField label="Type">
                  <Select value={form.node_type} onValueChange={(v) => setForm((s) => ({ ...s, node_type: v }))}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {NODE_TYPES.map((t) => (
                        <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </FormField>
                <FormField label="Status">
                  <Select value={form.status} onValueChange={(v) => setForm((s) => ({ ...s, status: v }))}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {STATUS_OPTIONS.map((s) => (
                        <SelectItem key={s} value={s}>{s.replace(/_/g, " ")}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </FormField>
                <FormField label="Sort order">
                  <Input type="number" min="0" value={form.sort_order} onChange={(e) => setForm((s) => ({ ...s, sort_order: e.target.value }))} />
                </FormField>
                <FormField label="Progress %">
                  <Input type="number" min="0" max="100" step="0.01" value={form.progress_percent} onChange={(e) => setForm((s) => ({ ...s, progress_percent: e.target.value }))} />
                </FormField>
                <FormField label="Planned start">
                  <Input type="date" value={form.planned_start} onChange={(e) => setForm((s) => ({ ...s, planned_start: e.target.value }))} />
                </FormField>
                <FormField label="Planned end">
                  <Input type="date" value={form.planned_end} onChange={(e) => setForm((s) => ({ ...s, planned_end: e.target.value }))} />
                </FormField>
                <FormField label="Estimated hours">
                  <Input type="number" min="0" step="0.01" value={form.estimated_hours} onChange={(e) => setForm((s) => ({ ...s, estimated_hours: e.target.value }))} />
                </FormField>
                <FormField label="Estimated cost">
                  <Input type="number" min="0" step="0.01" value={form.estimated_cost} onChange={(e) => setForm((s) => ({ ...s, estimated_cost: e.target.value }))} />
                </FormField>
                <FormField label="Description" className="md:col-span-2 xl:col-span-3">
                  <Input value={form.description} onChange={(e) => setForm((s) => ({ ...s, description: e.target.value }))} />
                </FormField>
                <FormField label="Notes" className="md:col-span-2 xl:col-span-3">
                  <Input value={form.notes} onChange={(e) => setForm((s) => ({ ...s, notes: e.target.value }))} />
                </FormField>
              </FormGrid>
            </FormSection>
          }
          actions={
            <FormActions>
              <div className="flex gap-3">
                <Button type="submit" loading={saving}>{editId ? "Save changes" : "Create node"}</Button>
                <Button type="button" variant="secondary" onClick={() => navigate(`/project/wbs${form.project_id ? `?project_id=${form.project_id}` : ""}`)}>
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

export function ProjectWbsNewPage() {
  return <ProjectWbsFormPage />;
}

export function ProjectWbsEditPage() {
  const { id } = useParams();
  return <ProjectWbsFormPage editId={id} />;
}

export function ProjectWbsDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { hasAnyPermission } = usePermissions();
  const canUpdate = hasAnyPermission("project.wbs.update");
  const canDelete = hasAnyPermission("project.wbs.delete");
  const canCreate = hasAnyPermission("project.wbs.create");
  const [row, setRow] = useState<WbsNode | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    projectsApi
      .wbsGet(id)
      .then((res) => setRow(res.data))
      .catch((err) => appDialog.alert(err instanceof Error ? err.message : "WBS node not found."))
      .finally(() => setLoading(false));
  }, [id]);

  const deleteNode = async () => {
    if (!id || !row) return;
    const ok = await appDialog.confirm(`Delete WBS node "${row.name}"?`);
    if (!ok) return;
    try {
      await projectsApi.wbsDelete(id);
      navigate(`/project/wbs?project_id=${row.project_id}`);
    } catch (err) {
      await appDialog.alert(err instanceof Error ? err.message : "Delete failed");
    }
  };

  if (loading || !row) {
    return (
      <PageLayout title={loading ? "Loading..." : "WBS"} breadcrumbs={["Home", "Project Management", "WBS"]}>
        {loading ? <div className="h-64 animate-pulse rounded-2xl bg-muted" /> : null}
      </PageLayout>
    );
  }

  return (
    <PageLayout
      title={row.name}
      description={`${row.code} · ${row.node_type.replace(/_/g, " ")} · Level ${row.level}`}
      breadcrumbs={["Home", "Project Management", "WBS", row.code]}
      actions={
        <div className="flex flex-wrap gap-2">
          {canUpdate ? (
            <Button variant="secondary" onClick={() => navigate(`/project/wbs/${row.id}/edit`)}>
              Edit
            </Button>
          ) : null}
          {canCreate ? (
            <Button variant="outline" onClick={() => navigate(`/project/wbs/new?project_id=${row.project_id}&parent_id=${row.id}`)}>
              Add child
            </Button>
          ) : null}
          {canDelete ? (
            <Button variant="destructive" onClick={() => void deleteNode()}>
              Delete
            </Button>
          ) : null}
          <Button variant="secondary" onClick={() => navigate(`/project/wbs?project_id=${row.project_id}`)}>
            Back to tree
          </Button>
        </div>
      }
    >
      <ContentSection title="Overview">
        <div className="grid gap-3 sm:grid-cols-2 text-sm">
          <p><span className="text-muted-foreground">Project</span> · {row.project_code}</p>
          <p><span className="text-muted-foreground">Parent</span> · {row.parent_name || "Root"}</p>
          <p><span className="text-muted-foreground">Status</span> · {statusBadge(row.status)}</p>
          <p><span className="text-muted-foreground">Progress</span> · {row.progress_percent}%</p>
          <p><span className="text-muted-foreground">Planned</span> · {row.planned_start || "—"} → {row.planned_end || "—"}</p>
          <p><span className="text-muted-foreground">Estimated hours</span> · {row.estimated_hours}</p>
          <p><span className="text-muted-foreground">Estimated cost</span> · {formatCurrency(row.estimated_cost)}</p>
        </div>
      </ContentSection>
      {row.description ? (
        <ContentSection title="Description">
          <p className="text-sm text-muted-foreground">{row.description}</p>
        </ContentSection>
      ) : null}
    </PageLayout>
  );
}
