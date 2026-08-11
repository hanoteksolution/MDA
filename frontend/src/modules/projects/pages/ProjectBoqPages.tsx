import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { Plus, Trash2 } from "lucide-react";
import { PageLayout } from "@/components/layout/PageLayout";
import { ContentSection } from "@/components/layout/ContentSection";
import { DataTable, type Column } from "@/components/data/DataTable";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { appDialog } from "@/components/feedback/AppDialog";
import { useAuthStore } from "@/store/authStore";
import { usePermissions } from "@/hooks/usePermissions";
import { projectsApi, type Boq, type BoqLine, type Project } from "@/services/api/projects";
import { formatCurrency } from "@/utils/cn";

const blankLine = (): BoqLine => ({ item_code: "", description: "", unit_of_measure: "unit", quantity: 0, unit_rate: 0, category: "other" });

export function ProjectBoqListPage() {
  const navigate = useNavigate();
  const branchId = useAuthStore((s) => s.user?.branch?.id);
  const { hasPermission } = usePermissions();
  const [rows, setRows] = useState<Boq[]>([]);
  const [loading, setLoading] = useState(true);
  useEffect(() => { if (branchId) projectsApi.boqList(1, undefined, branchId).then((r) => setRows(r.data.results)).finally(() => setLoading(false)); }, [branchId]);
  const columns: Column<Boq>[] = [
    { key: "name", header: "BOQ", cell: (row) => <button className="font-medium text-primary hover:underline" onClick={() => navigate(`/project/boq/${row.id}`)}>{row.name}</button> },
    { key: "version", header: "Version", cell: (row) => `v${row.version}` },
    { key: "status", header: "Status", cell: (row) => row.status },
    { key: "total_amount", header: "Total", cell: (row) => formatCurrency(row.total_amount) },
  ];
  return <PageLayout title="Bill of Quantities" description="Priced quantities and cost lines by project." breadcrumbs={["Home", "Project Management", "BOQ"]} actions={hasPermission("project.boq.create") ? <Button asChild size="sm"><Link to="/project/boq/new"><Plus className="mr-2 h-4 w-4" />New BOQ</Link></Button> : null}><DataTable columns={columns} data={rows} loading={loading} emptyMessage="No BOQs yet." /></PageLayout>;
}

export function ProjectBoqFormPage({ editId }: { editId?: string }) {
  const navigate = useNavigate();
  const branchId = useAuthStore((s) => s.user?.branch?.id);
  const [projects, setProjects] = useState<Project[]>([]);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({ project_id: "", name: "", currency: "USD", notes: "", lines: [blankLine()] });
  useEffect(() => { if (branchId) projectsApi.list(1, branchId).then((r) => setProjects(r.data.results)).catch(() => undefined); }, [branchId]);
  useEffect(() => { if (editId) projectsApi.boq(editId).then((r) => { const b = r.data; setForm({ project_id: b.project_id, name: b.name, currency: b.currency, notes: b.notes || "", lines: b.lines.length ? b.lines : [blankLine()] }); }).catch((e) => appDialog.alert(e instanceof Error ? e.message : "BOQ not found.")); }, [editId]);
  const updateLine = (index: number, patch: Partial<BoqLine>) => setForm((s) => ({ ...s, lines: s.lines.map((line, i) => i === index ? { ...line, ...patch } : line) }));
  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!form.project_id || !form.name.trim()) return;
    setSaving(true);
    try {
      const payload = { ...form, lines: form.lines.filter((line) => line.description.trim()).map((line, sort_order) => ({ ...line, quantity: Number(line.quantity) || 0, unit_rate: Number(line.unit_rate) || 0, sort_order })) };
      const result = editId ? await projectsApi.updateBoq(editId, payload) : await projectsApi.createBoq(payload);
      navigate(`/project/boq/${result.data.id}`);
    } catch (e) { await appDialog.alert(e instanceof Error ? e.message : "Unable to save BOQ."); } finally { setSaving(false); }
  };
  return <PageLayout title={editId ? "Edit BOQ" : "New BOQ"} breadcrumbs={["Home", "Project Management", "BOQ", editId ? "Edit" : "New"]}><form className="space-y-6" onSubmit={submit}><ContentSection title="Header"><div className="grid gap-3 md:grid-cols-2"><Select value={form.project_id} onValueChange={(project_id) => setForm((s) => ({ ...s, project_id }))} disabled={Boolean(editId)}><SelectTrigger><SelectValue placeholder="Project" /></SelectTrigger><SelectContent>{projects.map((p) => <SelectItem key={p.id} value={p.id}>{p.project_code} — {p.name}</SelectItem>)}</SelectContent></Select><Input placeholder="BOQ name" value={form.name} onChange={(e) => setForm((s) => ({ ...s, name: e.target.value }))} /><Input placeholder="Currency" value={form.currency} onChange={(e) => setForm((s) => ({ ...s, currency: e.target.value }))} /><Input placeholder="Notes" value={form.notes} onChange={(e) => setForm((s) => ({ ...s, notes: e.target.value }))} /></div></ContentSection><ContentSection title="Line items"><div className="space-y-3">{form.lines.map((line, index) => <div className="grid gap-2 rounded-xl border p-3 md:grid-cols-12" key={index}><Input className="md:col-span-2" placeholder="Item code" value={line.item_code} onChange={(e) => updateLine(index, { item_code: e.target.value })} /><Input className="md:col-span-3" placeholder="Description" value={line.description} onChange={(e) => updateLine(index, { description: e.target.value })} /><Input placeholder="UOM" value={line.unit_of_measure} onChange={(e) => updateLine(index, { unit_of_measure: e.target.value })} /><Input type="number" placeholder="Qty" value={line.quantity || ""} onChange={(e) => updateLine(index, { quantity: Number(e.target.value) || 0 })} /><Input type="number" placeholder="Rate" value={line.unit_rate || ""} onChange={(e) => updateLine(index, { unit_rate: Number(e.target.value) || 0 })} /><Select value={line.category} onValueChange={(category) => updateLine(index, { category })}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent>{["labor", "materials", "equipment", "subcontract", "other"].map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}</SelectContent></Select><Button type="button" variant="ghost" size="icon" onClick={() => setForm((s) => ({ ...s, lines: s.lines.filter((_, i) => i !== index) }))}><Trash2 className="h-4 w-4" /></Button></div>)}</div><Button className="mt-3" type="button" variant="outline" onClick={() => setForm((s) => ({ ...s, lines: [...s.lines, blankLine()] }))}>Add line</Button></ContentSection><Button type="submit" loading={saving}>{editId ? "Save changes" : "Create BOQ"}</Button></form></PageLayout>;
}

export function ProjectBoqNewPage() { return <ProjectBoqFormPage />; }
export function ProjectBoqEditPage() { const { id } = useParams(); return <ProjectBoqFormPage editId={id} />; }

export function ProjectBoqDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { hasAnyPermission } = usePermissions();
  const [row, setRow] = useState<Boq | null>(null);
  useEffect(() => { if (id) projectsApi.boq(id).then((r) => setRow(r.data)).catch((e) => appDialog.alert(e instanceof Error ? e.message : "BOQ not found.")); }, [id]);
  const setStatus = async (status: string) => { if (!id) return; try { const r = await projectsApi.setBoqStatus(id, status); setRow(r.data); } catch (e) { await appDialog.alert(e instanceof Error ? e.message : "Status change failed."); } };
  if (!row) return <PageLayout title="Loading BOQ" breadcrumbs={["Home", "Project Management", "BOQ"]}><div className="h-48 animate-pulse rounded-xl bg-muted" /></PageLayout>;
  const next = ({ draft: ["submitted"], submitted: ["draft", "approved"], approved: ["locked"] } as Record<string, string[]>)[row.status] || [];
  return <PageLayout title={row.name} description={`Version ${row.version} · ${row.status}`} breadcrumbs={["Home", "Project Management", "BOQ", row.name]} actions={<div className="flex gap-2">{hasAnyPermission("project.boq.update", "project.boq.approve") && row.status === "draft" ? <Button variant="outline" onClick={() => navigate(`/project/boq/${row.id}/edit`)}>Edit</Button> : null}<Button variant="outline" onClick={() => navigate("/project/boq")}>Back</Button></div>}><ContentSection title="Summary"><p className="text-sm">Total amount · {formatCurrency(row.total_amount)}</p></ContentSection><ContentSection title="Line items"><DataTable columns={[{ key: "item_code", header: "Code", cell: (line) => line.item_code }, { key: "description", header: "Description", cell: (line) => line.description }, { key: "quantity", header: "Quantity", cell: (line) => `${line.quantity} ${line.unit_of_measure}` }, { key: "unit_rate", header: "Rate", cell: (line) => formatCurrency(line.unit_rate) }, { key: "amount", header: "Amount", cell: (line) => formatCurrency(line.amount || line.quantity * line.unit_rate) }]} data={row.lines} emptyMessage="No line items." /></ContentSection>{next.length && hasAnyPermission("project.boq.update", "project.boq.approve") ? <ContentSection title="Workflow"><div className="flex gap-2">{next.map((status) => <Button key={status} size="sm" variant="outline" onClick={() => void setStatus(status)}>Move to {status}</Button>)}</div></ContentSection> : null}</PageLayout>;
}
