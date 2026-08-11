import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Plus } from "lucide-react";
import { PageLayout } from "@/components/layout/PageLayout";
import { ContentSection } from "@/components/layout/ContentSection";
import { DataTable, type Column } from "@/components/data/DataTable";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { appDialog } from "@/components/feedback/AppDialog";
import { useAuthStore } from "@/store/authStore";
import { usePermissions } from "@/hooks/usePermissions";
import { projectsApi, type DailyWage, type Project, type ProjectWorker, type WorkerAttendance, type WorkerRate } from "@/services/api/projects";
import { formatCurrency } from "@/utils/cn";

export function ProjectWorkforcePage() {
  const branchId = useAuthStore((s) => s.user?.branch?.id);
  const { hasPermission } = usePermissions();
  const [projects, setProjects] = useState<Project[]>([]);
  const [workers, setWorkers] = useState<ProjectWorker[]>([]);
  const [attendance, setAttendance] = useState<WorkerAttendance[]>([]);
  const [wages, setWages] = useState<DailyWage[]>([]);
  const [tab, setTab] = useState<"workers" | "attendance" | "wages">("workers");
  const [form, setForm] = useState<Record<string, string>>({ project_id: "", code: "", full_name: "", worker_type: "daily_wage", daily_rate: "0" });
  const [saving, setSaving] = useState(false);
  const reload = useCallback(async () => {
    if (!branchId) return;
    const [workerRes, attendanceRes, wageRes] = await Promise.all([projectsApi.workers(1, undefined, branchId), projectsApi.attendance(1, undefined, branchId), projectsApi.wages(1, undefined, branchId)]);
    setWorkers(workerRes.data.results); setAttendance(attendanceRes.data.results); setWages(wageRes.data.results);
  }, [branchId]);
  useEffect(() => { if (branchId) { projectsApi.list(1, branchId).then((r) => setProjects(r.data.results)).catch(() => undefined); void reload(); } }, [branchId, reload]);
  const createWorker = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!form.project_id || !form.code?.trim() || !form.full_name?.trim()) return;
    setSaving(true);
    try { await projectsApi.createWorker({ ...form, daily_rate: Number(form.daily_rate) || 0 }); setForm((s) => ({ ...s, code: "", full_name: "", daily_rate: "0" })); await reload(); }
    catch (e) { await appDialog.alert(e instanceof Error ? e.message : "Unable to create worker."); } finally { setSaving(false); }
  };
  const workerColumns: Column<ProjectWorker>[] = [
    { key: "full_name", header: "Worker", cell: (row) => <Link className="font-medium text-primary hover:underline" to={`/project/workforce/${row.id}`}>{row.code} — {row.full_name}</Link> },
    { key: "trade", header: "Trade", cell: (row) => row.trade || "—" },
    { key: "worker_type", header: "Type", cell: (row) => row.worker_type },
    { key: "daily_rate", header: "Daily rate", cell: (row) => formatCurrency(row.daily_rate) },
  ];
  const attendanceColumns: Column<WorkerAttendance>[] = [{ key: "work_date", header: "Date", cell: (r) => r.work_date }, { key: "worker_id", header: "Worker", cell: (r) => workers.find((w) => w.id === r.worker_id)?.full_name || r.worker_id }, { key: "hours_worked", header: "Hours", cell: (r) => r.hours_worked }, { key: "status", header: "Status", cell: (r) => r.status }];
  const wageColumns: Column<DailyWage>[] = [{ key: "work_date", header: "Date", cell: (r) => r.work_date }, { key: "worker_id", header: "Worker", cell: (r) => workers.find((w) => w.id === r.worker_id)?.full_name || r.worker_id }, { key: "amount", header: "Amount", cell: (r) => formatCurrency(r.amount) }, { key: "status", header: "Status", cell: (r) => r.status }];
  const table = tab === "workers"
    ? <DataTable columns={workerColumns} data={workers} emptyMessage="No workers yet." />
    : tab === "attendance"
      ? <DataTable columns={attendanceColumns} data={attendance} emptyMessage="No attendance yet." />
      : <DataTable columns={wageColumns} data={wages} emptyMessage="No wages yet." />;
  return <PageLayout title="Workforce" description="Workers, daily attendance, and wage entries." breadcrumbs={["Home", "Project Management", "Workforce"]}><div className="mb-5 flex gap-2">{(["workers", "attendance", "wages"] as const).map((value) => <Button key={value} size="sm" variant={tab === value ? "default" : "outline"} onClick={() => setTab(value)}>{value}</Button>)}</div>{tab === "workers" && hasPermission("project.workers.create") ? <ContentSection title="Add worker"><form className="grid gap-3 md:grid-cols-3" onSubmit={createWorker}><Select value={form.project_id} onValueChange={(project_id) => setForm((s) => ({ ...s, project_id }))}><SelectTrigger><SelectValue placeholder="Project" /></SelectTrigger><SelectContent>{projects.map((p) => <SelectItem key={p.id} value={p.id}>{p.project_code} — {p.name}</SelectItem>)}</SelectContent></Select><Input placeholder="Worker code" value={form.code || ""} onChange={(e) => setForm((s) => ({ ...s, code: e.target.value }))} /><Input placeholder="Full name" value={form.full_name || ""} onChange={(e) => setForm((s) => ({ ...s, full_name: e.target.value }))} /><Input placeholder="Trade" value={form.trade || ""} onChange={(e) => setForm((s) => ({ ...s, trade: e.target.value }))} /><Select value={form.worker_type || "daily_wage"} onValueChange={(worker_type) => setForm((s) => ({ ...s, worker_type }))}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent>{["employee", "daily_wage", "contractor", "subcontractor", "consultant"].map((v) => <SelectItem key={v} value={v}>{v}</SelectItem>)}</SelectContent></Select><Input type="number" placeholder="Daily rate" value={form.daily_rate || ""} onChange={(e) => setForm((s) => ({ ...s, daily_rate: e.target.value }))} /><Button type="submit" loading={saving}><Plus className="mr-2 h-4 w-4" />Add worker</Button></form></ContentSection> : null}<ContentSection title={tab === "workers" ? "Workers" : tab === "attendance" ? "Attendance" : "Wages"}>{table}</ContentSection></PageLayout>;
}

export function ProjectWorkerDetailPage() {
  const { id } = useParams();
  const { hasPermission } = usePermissions();
  const [worker, setWorker] = useState<ProjectWorker | null>(null);
  const [rates, setRates] = useState<WorkerRate[]>([]);
  const [attendance, setAttendance] = useState<WorkerAttendance[]>([]);
  const [wages, setWages] = useState<DailyWage[]>([]);
  const [saving, setSaving] = useState(false);
  const reload = useCallback(async () => { if (!id) return; const [workerRes, rateRes, attendanceRes, wageRes] = await Promise.all([projectsApi.worker(id), projectsApi.workerRates(id), projectsApi.attendance(), projectsApi.wages()]); setWorker(workerRes.data); setRates(rateRes.data); setAttendance(attendanceRes.data.results.filter((r) => r.worker_id === id)); setWages(wageRes.data.results.filter((r) => r.worker_id === id)); }, [id]);
  useEffect(() => { void reload(); }, [reload]);
  const addAttendance = async () => { if (!worker) return; setSaving(true); try { await projectsApi.createAttendance({ project_id: worker.project_id, worker_id: worker.id, work_date: new Date().toISOString().slice(0, 10), hours_worked: 8, status: "present" }); await reload(); } catch (e) { await appDialog.alert(e instanceof Error ? e.message : "Unable to add attendance."); } finally { setSaving(false); } };
  const addWage = async (entry: WorkerAttendance) => { if (!worker) return; setSaving(true); try { await projectsApi.createWage({ attendance_id: entry.id }); await reload(); } catch (e) { await appDialog.alert(e instanceof Error ? e.message : "Unable to create wage."); } finally { setSaving(false); } };
  if (!worker) return <PageLayout title="Loading worker" breadcrumbs={["Home", "Project Management", "Workforce"]}><div className="h-40 animate-pulse rounded-xl bg-muted" /></PageLayout>;
  return <PageLayout title={worker.full_name} description={`${worker.code} · ${worker.trade || worker.worker_type}`} breadcrumbs={["Home", "Project Management", "Workforce", worker.full_name]}><ContentSection title="Profile"><div className="grid gap-3 text-sm sm:grid-cols-2"><p>Type · {worker.worker_type}</p><p>Daily rate · {formatCurrency(worker.daily_rate)}</p><p>Phone · {worker.phone || "—"}</p><p>Status · {worker.is_active ? "Active" : "Inactive"}</p></div></ContentSection><ContentSection title="Rate history"><DataTable columns={[{ key: "effective_from", header: "Effective from", cell: (r) => r.effective_from }, { key: "effective_to", header: "Effective to", cell: (r) => r.effective_to || "Current" }, { key: "rate", header: "Rate", cell: (r) => formatCurrency(r.rate) }]} data={rates} emptyMessage="No rate history." /></ContentSection><ContentSection title="Attendance" action={hasPermission("project.workers.create") ? <Button size="sm" loading={saving} onClick={() => void addAttendance()}>Record today</Button> : null}><DataTable columns={[{ key: "work_date", header: "Date", cell: (r) => r.work_date }, { key: "hours_worked", header: "Hours", cell: (r) => r.hours_worked }, { key: "status", header: "Status", cell: (r) => r.status }, { key: "action", header: "", cell: (r) => hasPermission("project.wages.create") ? <Button size="sm" variant="outline" loading={saving} onClick={() => void addWage(r)}>Create wage</Button> : null }]} data={attendance} emptyMessage="No attendance." /></ContentSection><ContentSection title="Wages"><DataTable columns={[{ key: "work_date", header: "Date", cell: (r) => r.work_date }, { key: "amount", header: "Amount", cell: (r) => formatCurrency(r.amount) }, { key: "status", header: "Status", cell: (r) => r.status }]} data={wages} emptyMessage="No wages." /></ContentSection></PageLayout>;
}
