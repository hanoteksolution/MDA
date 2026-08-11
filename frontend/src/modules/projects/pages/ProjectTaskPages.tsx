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
import { projectsApi, type Project, type ProjectTask, type WbsNode } from "@/services/api/projects";

const STATUSES = ["todo", "in_progress", "blocked", "review", "done", "cancelled"];
const PRIORITIES = ["low", "medium", "high", "critical"];

function label(value: string) {
  return value.replace(/_/g, " ");
}

function statusBadge(status: string) {
  const variant =
    status === "done" ? "secondary" : status === "blocked" || status === "cancelled" ? "destructive" : "outline";
  return <Badge variant={variant}>{label(status)}</Badge>;
}

export function ProjectTaskListPage() {
  const navigate = useNavigate();
  const branchId = useAuthStore((s) => s.user?.branch?.id);
  const { hasPermission } = usePermissions();
  const [searchParams, setSearchParams] = useSearchParams();
  const [projects, setProjects] = useState<Project[]>([]);
  const [rows, setRows] = useState<ProjectTask[]>([]);
  const [loading, setLoading] = useState(true);
  const projectId = searchParams.get("project_id") || "";
  const status = searchParams.get("status") || "";
  const search = searchParams.get("search") || "";
  const canCreate = hasPermission("project.tasks.create");

  useEffect(() => {
    if (!branchId) return;
    projectsApi.list(1, branchId).then((res) => setProjects(res.data.results)).catch(() => undefined);
  }, [branchId]);

  const reload = useCallback(async () => {
    if (!branchId) return;
    setLoading(true);
    try {
      const res = await projectsApi.tasks(1, {
        project_id: projectId || undefined,
        status: status || undefined,
        search: search || undefined,
        branch_id: branchId,
      });
      setRows(status ? res.data.results.filter((row) => row.status === status) : res.data.results);
    } finally {
      setLoading(false);
    }
  }, [branchId, projectId, search, status]);

  useEffect(() => {
    void reload();
  }, [reload]);

  const updateFilter = (key: string, value: string) => {
    const next = new URLSearchParams(searchParams);
    if (value) next.set(key, value);
    else next.delete(key);
    setSearchParams(next);
  };

  const columns: Column<ProjectTask>[] = [
    {
      key: "title",
      header: "Task",
      cell: (row) => (
        <button className="text-left font-medium text-primary hover:underline" type="button" onClick={() => navigate(`/project/tasks/${row.id}`)}>
          {row.task_code} — {row.title}
        </button>
      ),
    },
    { key: "project_code", header: "Project", cell: (row) => row.project_code },
    { key: "priority", header: "Priority", cell: (row) => <Badge variant="outline">{row.priority}</Badge> },
    { key: "status", header: "Status", cell: (row) => statusBadge(row.status) },
    { key: "planned_end", header: "Due", cell: (row) => row.planned_end || "—" },
    { key: "estimated_hours", header: "Hours", cell: (row) => row.estimated_hours },
  ];

  return (
    <PageLayout
      title="Project Tasks"
      description="Plan, assign, and track delivery work across projects."
      breadcrumbs={["Home", "Project Management", "Tasks"]}
      actions={canCreate ? <Button asChild size="sm"><Link to={`/project/tasks/new${projectId ? `?project_id=${projectId}` : ""}`}><Plus className="mr-2 h-4 w-4" />New task</Link></Button> : null}
    >
      <div className="mb-4 flex flex-wrap gap-3">
        <Select value={projectId || "__all__"} onValueChange={(value) => updateFilter("project_id", value === "__all__" ? "" : value)}>
          <SelectTrigger className="w-64"><SelectValue placeholder="All projects" /></SelectTrigger>
          <SelectContent><SelectItem value="__all__">All projects</SelectItem>{projects.map((project) => <SelectItem key={project.id} value={project.id}>{project.project_code} — {project.name}</SelectItem>)}</SelectContent>
        </Select>
        <Select value={status || "__all__"} onValueChange={(value) => updateFilter("status", value === "__all__" ? "" : value)}>
          <SelectTrigger className="w-48"><SelectValue placeholder="All statuses" /></SelectTrigger>
          <SelectContent><SelectItem value="__all__">All statuses</SelectItem>{STATUSES.map((item) => <SelectItem key={item} value={item}>{label(item)}</SelectItem>)}</SelectContent>
        </Select>
        <Input className="w-64" placeholder="Search tasks" value={search} onChange={(event) => updateFilter("search", event.target.value)} />
      </div>
      <DataTable columns={columns} data={rows} loading={loading} emptyMessage="No tasks found." />
    </PageLayout>
  );
}

export function ProjectTaskFormPage({ editId }: { editId?: string }) {
  const navigate = useNavigate();
  const branchId = useAuthStore((s) => s.user?.branch?.id);
  const [searchParams] = useSearchParams();
  const [projects, setProjects] = useState<Project[]>([]);
  const [wbsNodes, setWbsNodes] = useState<WbsNode[]>([]);
  const [loading, setLoading] = useState(Boolean(editId));
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({
    project_id: searchParams.get("project_id") || "", wbs_node_id: "", task_code: "", title: "", description: "",
    priority: "medium", planned_start: "", planned_end: "", estimated_hours: "", progress_percent: "0", notes: "",
  });

  useEffect(() => {
    if (!branchId) return;
    projectsApi.list(1, branchId).then((res) => setProjects(res.data.results)).catch(() => undefined);
  }, [branchId]);

  useEffect(() => {
    if (!form.project_id || !branchId) {
      setWbsNodes([]);
      return;
    }
    projectsApi.wbsList(1, form.project_id, branchId).then((res) => setWbsNodes(res.data.results)).catch(() => undefined);
  }, [branchId, form.project_id]);

  useEffect(() => {
    if (!editId) return;
    projectsApi.task(editId).then((res) => {
      const row = res.data;
      setForm({
        project_id: row.project_id, wbs_node_id: row.wbs_node_id || "", task_code: row.task_code, title: row.title,
        description: row.description || "", priority: row.priority, planned_start: row.planned_start || "",
        planned_end: row.planned_end || "", estimated_hours: String(row.estimated_hours || ""),
        progress_percent: String(row.progress_percent || 0), notes: row.notes || "",
      });
    }).catch((err) => appDialog.alert(err instanceof Error ? err.message : "Task not found.")).finally(() => setLoading(false));
  }, [editId]);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!form.project_id || !form.title.trim()) return;
    setSaving(true);
    const payload = {
      project_id: form.project_id, wbs_node_id: form.wbs_node_id || null, task_code: form.task_code.trim() || undefined,
      title: form.title.trim(), description: form.description || undefined, priority: form.priority,
      planned_start: form.planned_start || undefined, planned_end: form.planned_end || undefined,
      estimated_hours: Number(form.estimated_hours) || 0, progress_percent: Number(form.progress_percent) || 0, notes: form.notes || undefined,
    };
    try {
      const res = editId ? await projectsApi.updateTask(editId, payload) : await projectsApi.createTask(payload);
      navigate(`/project/tasks/${res.data.id}`);
    } catch (err) {
      await appDialog.alert(err instanceof Error ? err.message : "Save failed.");
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <PageLayout title="Loading..." breadcrumbs={["Home", "Project Management", "Tasks"]}><div className="h-64 animate-pulse rounded-2xl bg-muted" /></PageLayout>;

  return (
    <PageLayout title={editId ? "Edit task" : "New task"} breadcrumbs={["Home", "Project Management", "Tasks", editId ? "Edit" : "New"]}>
      <form onSubmit={submit}>
        <FormPageLayout
          main={<FormSection title="Task details"><FormGrid>
            <FormField label="Project" required><Select value={form.project_id} onValueChange={(value) => setForm((current) => ({ ...current, project_id: value, wbs_node_id: "" }))} disabled={Boolean(editId)}><SelectTrigger><SelectValue placeholder="Select project" /></SelectTrigger><SelectContent>{projects.map((project) => <SelectItem key={project.id} value={project.id}>{project.project_code} — {project.name}</SelectItem>)}</SelectContent></Select></FormField>
            <FormField label="WBS node"><Select value={form.wbs_node_id || "__none__"} onValueChange={(value) => setForm((current) => ({ ...current, wbs_node_id: value === "__none__" ? "" : value }))}><SelectTrigger><SelectValue placeholder="No WBS node" /></SelectTrigger><SelectContent><SelectItem value="__none__">No WBS node</SelectItem>{wbsNodes.map((node) => <SelectItem key={node.id} value={node.id}>{node.code} — {node.name}</SelectItem>)}</SelectContent></Select></FormField>
            <FormField label="Title" required><Input required value={form.title} onChange={(event) => setForm((current) => ({ ...current, title: event.target.value }))} /></FormField>
            <FormField label="Task code" hint="Auto-generated if empty"><Input value={form.task_code} onChange={(event) => setForm((current) => ({ ...current, task_code: event.target.value }))} /></FormField>
            <FormField label="Priority"><Select value={form.priority} onValueChange={(value) => setForm((current) => ({ ...current, priority: value }))}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent>{PRIORITIES.map((item) => <SelectItem key={item} value={item}>{label(item)}</SelectItem>)}</SelectContent></Select></FormField>
            <FormField label="Estimated hours"><Input type="number" min="0" step="0.01" value={form.estimated_hours} onChange={(event) => setForm((current) => ({ ...current, estimated_hours: event.target.value }))} /></FormField>
            <FormField label="Planned start"><Input type="date" value={form.planned_start} onChange={(event) => setForm((current) => ({ ...current, planned_start: event.target.value }))} /></FormField>
            <FormField label="Planned end"><Input type="date" value={form.planned_end} onChange={(event) => setForm((current) => ({ ...current, planned_end: event.target.value }))} /></FormField>
            <FormField label="Progress %"><Input type="number" min="0" max="100" step="0.01" value={form.progress_percent} onChange={(event) => setForm((current) => ({ ...current, progress_percent: event.target.value }))} /></FormField>
            <FormField label="Description" className="md:col-span-2 xl:col-span-3"><Input value={form.description} onChange={(event) => setForm((current) => ({ ...current, description: event.target.value }))} /></FormField>
            <FormField label="Notes" className="md:col-span-2 xl:col-span-3"><Input value={form.notes} onChange={(event) => setForm((current) => ({ ...current, notes: event.target.value }))} /></FormField>
          </FormGrid></FormSection>}
          actions={<FormActions><div className="flex gap-3"><Button type="submit" loading={saving}>{editId ? "Save changes" : "Create task"}</Button><Button type="button" variant="secondary" onClick={() => navigate("/project/tasks")}>Cancel</Button></div></FormActions>}
        />
      </form>
    </PageLayout>
  );
}

export function ProjectTaskNewPage() { return <ProjectTaskFormPage />; }
export function ProjectTaskEditPage() { const { id } = useParams(); return <ProjectTaskFormPage editId={id} />; }

export function ProjectTaskDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { hasPermission } = usePermissions();
  const [row, setRow] = useState<ProjectTask | null>(null);
  const [loading, setLoading] = useState(true);
  const canUpdate = hasPermission("project.tasks.update");
  const canDelete = hasPermission("project.tasks.delete");

  useEffect(() => {
    if (!id) return;
    projectsApi.task(id).then((res) => setRow(res.data)).catch((err) => appDialog.alert(err instanceof Error ? err.message : "Task not found.")).finally(() => setLoading(false));
  }, [id]);

  const updateStatus = async (status: string) => {
    if (!id) return;
    try { const res = await projectsApi.setTaskStatus(id, status); setRow(res.data); }
    catch (err) { await appDialog.alert(err instanceof Error ? err.message : "Status update failed."); }
  };
  const deleteTask = async () => {
    if (!id || !row || !(await appDialog.confirm(`Delete task "${row.title}"?`))) return;
    try { await projectsApi.deleteTask(id); navigate(`/project/tasks?project_id=${row.project_id}`); }
    catch (err) { await appDialog.alert(err instanceof Error ? err.message : "Delete failed."); }
  };

  if (loading || !row) return <PageLayout title={loading ? "Loading..." : "Task"} breadcrumbs={["Home", "Project Management", "Tasks"]}>{loading ? <div className="h-64 animate-pulse rounded-2xl bg-muted" /> : null}</PageLayout>;
  const transitions: Record<string, string[]> = {
    todo: ["in_progress", "blocked", "cancelled"], in_progress: ["blocked", "review", "done", "cancelled"],
    blocked: ["todo", "in_progress", "cancelled"], review: ["in_progress", "blocked", "done", "cancelled"],
    done: ["in_progress"], cancelled: ["todo"],
  };
  return (
    <PageLayout title={row.title} description={`${row.task_code} · ${row.project_code}`} breadcrumbs={["Home", "Project Management", "Tasks", row.task_code]}
      actions={<div className="flex flex-wrap gap-2">{canUpdate ? <Button variant="secondary" onClick={() => navigate(`/project/tasks/${row.id}/edit`)}>Edit</Button> : null}{canDelete ? <Button variant="destructive" onClick={() => void deleteTask()}>Delete</Button> : null}<Button variant="secondary" onClick={() => navigate(`/project/tasks?project_id=${row.project_id}`)}>Back</Button></div>}>
      <ContentSection title="Overview"><div className="grid gap-3 text-sm sm:grid-cols-2"><p><span className="text-muted-foreground">Project</span> · {row.project_code} — {row.project_name}</p><p><span className="text-muted-foreground">Status</span> · {statusBadge(row.status)}</p><p><span className="text-muted-foreground">Priority</span> · {row.priority}</p><p><span className="text-muted-foreground">WBS</span> · {row.wbs_code || "—"}</p><p><span className="text-muted-foreground">Planned</span> · {row.planned_start || "—"} → {row.planned_end || "—"}</p><p><span className="text-muted-foreground">Hours</span> · {row.actual_hours} actual / {row.estimated_hours} estimated</p><p><span className="text-muted-foreground">Progress</span> · {row.progress_percent}%</p></div></ContentSection>
      {row.description ? <ContentSection title="Description"><p className="text-sm text-muted-foreground">{row.description}</p></ContentSection> : null}
      {canUpdate ? <ContentSection title="Workflow"><div className="flex flex-wrap gap-2">{(transitions[row.status] || []).map((status) => <Button key={status} size="sm" variant="outline" onClick={() => void updateStatus(status)}>Move to {label(status)}</Button>)}</div></ContentSection> : null}
    </PageLayout>
  );
}
