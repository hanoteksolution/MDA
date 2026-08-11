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
import { projectsApi, type Project, type ProjectMilestone, type WbsNode } from "@/services/api/projects";

const STATUSES = ["pending", "achieved", "missed", "cancelled"];
const label = (value: string) => value.replace(/_/g, " ");
const statusBadge = (status: string) => <Badge variant={status === "achieved" ? "secondary" : status === "missed" || status === "cancelled" ? "destructive" : "outline"}>{label(status)}</Badge>;

export function ProjectMilestoneListPage() {
  const navigate = useNavigate();
  const branchId = useAuthStore((s) => s.user?.branch?.id);
  const { hasPermission } = usePermissions();
  const [searchParams, setSearchParams] = useSearchParams();
  const [projects, setProjects] = useState<Project[]>([]);
  const [rows, setRows] = useState<ProjectMilestone[]>([]);
  const [loading, setLoading] = useState(true);
  const projectId = searchParams.get("project_id") || "";
  const status = searchParams.get("status") || "";
  const search = searchParams.get("search") || "";

  useEffect(() => { if (branchId) projectsApi.list(1, branchId).then((res) => setProjects(res.data.results)).catch(() => undefined); }, [branchId]);
  const reload = useCallback(async () => {
    if (!branchId) return;
    setLoading(true);
    try {
      const res = await projectsApi.milestones(1, {
        project_id: projectId || undefined,
        status: status || undefined,
        search: search || undefined,
        branch_id: branchId,
      });
      setRows(status ? res.data.results.filter((row) => row.status === status) : res.data.results);
    }
    finally { setLoading(false); }
  }, [branchId, projectId, search, status]);
  useEffect(() => { void reload(); }, [reload]);
  const updateFilter = (key: string, value: string) => { const next = new URLSearchParams(searchParams); if (value) next.set(key, value); else next.delete(key); setSearchParams(next); };
  const columns: Column<ProjectMilestone>[] = [
    { key: "name", header: "Milestone", cell: (row) => <button className="text-left font-medium text-primary hover:underline" type="button" onClick={() => navigate(`/project/milestones/${row.id}`)}>{row.code} — {row.name}</button> },
    { key: "project_code", header: "Project", cell: (row) => row.project_code },
    { key: "due_date", header: "Due date", cell: (row) => row.due_date || "—" },
    { key: "is_critical", header: "Critical", cell: (row) => row.is_critical ? <Badge variant="destructive">Critical</Badge> : "—" },
    { key: "status", header: "Status", cell: (row) => statusBadge(row.status) },
  ];
  return (
    <PageLayout title="Project Milestones" description="Track the significant delivery checkpoints for every project." breadcrumbs={["Home", "Project Management", "Milestones"]}
      actions={hasPermission("project.milestones.create") ? <Button asChild size="sm"><Link to={`/project/milestones/new${projectId ? `?project_id=${projectId}` : ""}`}><Plus className="mr-2 h-4 w-4" />New milestone</Link></Button> : null}>
      <div className="mb-4 flex flex-wrap gap-3">
        <Select value={projectId || "__all__"} onValueChange={(value) => updateFilter("project_id", value === "__all__" ? "" : value)}><SelectTrigger className="w-64"><SelectValue placeholder="All projects" /></SelectTrigger><SelectContent><SelectItem value="__all__">All projects</SelectItem>{projects.map((project) => <SelectItem key={project.id} value={project.id}>{project.project_code} — {project.name}</SelectItem>)}</SelectContent></Select>
        <Select value={status || "__all__"} onValueChange={(value) => updateFilter("status", value === "__all__" ? "" : value)}><SelectTrigger className="w-48"><SelectValue placeholder="All statuses" /></SelectTrigger><SelectContent><SelectItem value="__all__">All statuses</SelectItem>{STATUSES.map((item) => <SelectItem key={item} value={item}>{label(item)}</SelectItem>)}</SelectContent></Select>
        <Input className="w-64" placeholder="Search milestones" value={search} onChange={(event) => updateFilter("search", event.target.value)} />
      </div>
      <DataTable columns={columns} data={rows} loading={loading} emptyMessage="No milestones found." />
    </PageLayout>
  );
}

export function ProjectMilestoneFormPage({ editId }: { editId?: string }) {
  const navigate = useNavigate();
  const branchId = useAuthStore((s) => s.user?.branch?.id);
  const [searchParams] = useSearchParams();
  const [projects, setProjects] = useState<Project[]>([]);
  const [wbsNodes, setWbsNodes] = useState<WbsNode[]>([]);
  const [loading, setLoading] = useState(Boolean(editId));
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({ project_id: searchParams.get("project_id") || "", wbs_node_id: "", code: "", name: "", description: "", due_date: "", is_critical: false, sort_order: "0", notes: "" });
  useEffect(() => { if (branchId) projectsApi.list(1, branchId).then((res) => setProjects(res.data.results)).catch(() => undefined); }, [branchId]);
  useEffect(() => {
    if (!form.project_id || !branchId) { setWbsNodes([]); return; }
    projectsApi.wbsList(1, form.project_id, branchId).then((res) => setWbsNodes(res.data.results)).catch(() => undefined);
  }, [branchId, form.project_id]);
  useEffect(() => {
    if (!editId) return;
    projectsApi.milestone(editId).then((res) => {
      const row = res.data;
      setForm({ project_id: row.project_id, wbs_node_id: row.wbs_node_id || "", code: row.code, name: row.name, description: row.description || "", due_date: row.due_date || "", is_critical: row.is_critical, sort_order: String(row.sort_order || 0), notes: row.notes || "" });
    }).catch((err) => appDialog.alert(err instanceof Error ? err.message : "Milestone not found.")).finally(() => setLoading(false));
  }, [editId]);
  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!form.project_id || !form.name.trim()) return;
    setSaving(true);
    const payload = { project_id: form.project_id, wbs_node_id: form.wbs_node_id || null, code: form.code.trim() || undefined, name: form.name.trim(), description: form.description || undefined, due_date: form.due_date || undefined, is_critical: form.is_critical, sort_order: Number(form.sort_order) || 0, notes: form.notes || undefined };
    try { const res = editId ? await projectsApi.updateMilestone(editId, payload) : await projectsApi.createMilestone(payload); navigate(`/project/milestones/${res.data.id}`); }
    catch (err) { await appDialog.alert(err instanceof Error ? err.message : "Save failed."); }
    finally { setSaving(false); }
  };
  if (loading) return <PageLayout title="Loading..." breadcrumbs={["Home", "Project Management", "Milestones"]}><div className="h-64 animate-pulse rounded-2xl bg-muted" /></PageLayout>;
  return (
    <PageLayout title={editId ? "Edit milestone" : "New milestone"} breadcrumbs={["Home", "Project Management", "Milestones", editId ? "Edit" : "New"]}>
      <form onSubmit={submit}><FormPageLayout
        main={<FormSection title="Milestone details"><FormGrid>
          <FormField label="Project" required><Select value={form.project_id} disabled={Boolean(editId)} onValueChange={(value) => setForm((current) => ({ ...current, project_id: value, wbs_node_id: "" }))}><SelectTrigger><SelectValue placeholder="Select project" /></SelectTrigger><SelectContent>{projects.map((project) => <SelectItem key={project.id} value={project.id}>{project.project_code} — {project.name}</SelectItem>)}</SelectContent></Select></FormField>
          <FormField label="WBS node"><Select value={form.wbs_node_id || "__none__"} onValueChange={(value) => setForm((current) => ({ ...current, wbs_node_id: value === "__none__" ? "" : value }))}><SelectTrigger><SelectValue placeholder="No WBS node" /></SelectTrigger><SelectContent><SelectItem value="__none__">No WBS node</SelectItem>{wbsNodes.map((node) => <SelectItem key={node.id} value={node.id}>{node.code} — {node.name}</SelectItem>)}</SelectContent></Select></FormField>
          <FormField label="Name" required><Input required value={form.name} onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))} /></FormField>
          <FormField label="Code" hint="Auto-generated if empty"><Input value={form.code} onChange={(event) => setForm((current) => ({ ...current, code: event.target.value }))} /></FormField>
          <FormField label="Due date"><Input type="date" value={form.due_date} onChange={(event) => setForm((current) => ({ ...current, due_date: event.target.value }))} /></FormField>
          <FormField label="Sort order"><Input type="number" min="0" value={form.sort_order} onChange={(event) => setForm((current) => ({ ...current, sort_order: event.target.value }))} /></FormField>
          <FormField label="Critical milestone"><label className="flex h-10 items-center gap-2"><input type="checkbox" checked={form.is_critical} onChange={(event) => setForm((current) => ({ ...current, is_critical: event.target.checked }))} />Requires focused delivery attention</label></FormField>
          <FormField label="Description" className="md:col-span-2 xl:col-span-3"><Input value={form.description} onChange={(event) => setForm((current) => ({ ...current, description: event.target.value }))} /></FormField>
          <FormField label="Notes" className="md:col-span-2 xl:col-span-3"><Input value={form.notes} onChange={(event) => setForm((current) => ({ ...current, notes: event.target.value }))} /></FormField>
        </FormGrid></FormSection>}
        actions={<FormActions><div className="flex gap-3"><Button type="submit" loading={saving}>{editId ? "Save changes" : "Create milestone"}</Button><Button type="button" variant="secondary" onClick={() => navigate("/project/milestones")}>Cancel</Button></div></FormActions>}
      /></form>
    </PageLayout>
  );
}

export function ProjectMilestoneNewPage() { return <ProjectMilestoneFormPage />; }
export function ProjectMilestoneEditPage() { const { id } = useParams(); return <ProjectMilestoneFormPage editId={id} />; }

export function ProjectMilestoneDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { hasPermission } = usePermissions();
  const [row, setRow] = useState<ProjectMilestone | null>(null);
  const [loading, setLoading] = useState(true);
  const canUpdate = hasPermission("project.milestones.update");
  const canDelete = hasPermission("project.milestones.delete");
  useEffect(() => { if (id) projectsApi.milestone(id).then((res) => setRow(res.data)).catch((err) => appDialog.alert(err instanceof Error ? err.message : "Milestone not found.")).finally(() => setLoading(false)); }, [id]);
  const setStatus = async (status: string) => { if (!id) return; try { const res = await projectsApi.setMilestoneStatus(id, status); setRow(res.data); } catch (err) { await appDialog.alert(err instanceof Error ? err.message : "Status update failed."); } };
  const remove = async () => { if (!id || !row || !(await appDialog.confirm(`Delete milestone "${row.name}"?`))) return; try { await projectsApi.deleteMilestone(id); navigate(`/project/milestones?project_id=${row.project_id}`); } catch (err) { await appDialog.alert(err instanceof Error ? err.message : "Delete failed."); } };
  if (loading || !row) return <PageLayout title={loading ? "Loading..." : "Milestone"} breadcrumbs={["Home", "Project Management", "Milestones"]}>{loading ? <div className="h-64 animate-pulse rounded-2xl bg-muted" /> : null}</PageLayout>;
  return (
    <PageLayout title={row.name} description={`${row.code} · ${row.project_code}`} breadcrumbs={["Home", "Project Management", "Milestones", row.code]}
      actions={<div className="flex flex-wrap gap-2">{canUpdate ? <Button variant="secondary" onClick={() => navigate(`/project/milestones/${row.id}/edit`)}>Edit</Button> : null}{canDelete ? <Button variant="destructive" onClick={() => void remove()}>Delete</Button> : null}<Button variant="secondary" onClick={() => navigate(`/project/milestones?project_id=${row.project_id}`)}>Back</Button></div>}>
      <ContentSection title="Overview"><div className="grid gap-3 text-sm sm:grid-cols-2"><p><span className="text-muted-foreground">Project</span> · {row.project_code} — {row.project_name}</p><p><span className="text-muted-foreground">Status</span> · {statusBadge(row.status)}</p><p><span className="text-muted-foreground">Due date</span> · {row.due_date || "—"}</p><p><span className="text-muted-foreground">WBS</span> · {row.wbs_code || "—"}</p><p><span className="text-muted-foreground">Critical</span> · {row.is_critical ? "Yes" : "No"}</p><p><span className="text-muted-foreground">Completed</span> · {row.completed_at || "—"}</p></div></ContentSection>
      {row.description ? <ContentSection title="Description"><p className="text-sm text-muted-foreground">{row.description}</p></ContentSection> : null}
      {canUpdate ? <ContentSection title="Status"><div className="flex flex-wrap gap-2">{STATUSES.filter((status) => status !== row.status).map((status) => <Button key={status} size="sm" variant="outline" onClick={() => void setStatus(status)}>Mark {label(status)}</Button>)}</div></ContentSection> : null}
    </PageLayout>
  );
}
