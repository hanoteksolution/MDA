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
import { projectsApi, type ConstructionKind, type ConstructionRecord, type Project } from "@/services/api/projects";

const kinds: { value: ConstructionKind; label: string }[] = [
  { value: "site", label: "Sites" },
  { value: "building", label: "Buildings" },
  { value: "floor", label: "Floors" },
  { value: "unit", label: "Units" },
];

export function ProjectConstructionPage() {
  const branchId = useAuthStore((s) => s.user?.branch?.id);
  const { hasPermission } = usePermissions();
  const [kind, setKind] = useState<ConstructionKind>("site");
  const [projects, setProjects] = useState<Project[]>([]);
  const [rows, setRows] = useState<ConstructionRecord[]>([]);
  const [sites, setSites] = useState<ConstructionRecord[]>([]);
  const [buildings, setBuildings] = useState<ConstructionRecord[]>([]);
  const [floors, setFloors] = useState<ConstructionRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState<Record<string, string>>({ project_id: "", code: "", name: "", status: "active" });
  const canCreate = hasPermission("projects.update");

  useEffect(() => {
    if (!branchId) return;
    projectsApi.list(1, branchId).then((res) => setProjects(res.data.results)).catch(() => undefined);
    Promise.all([
      projectsApi.construction("site", 1, undefined, branchId),
      projectsApi.construction("building", 1, undefined, branchId),
      projectsApi.construction("floor", 1, undefined, branchId),
    ]).then(([siteRes, buildingRes, floorRes]) => {
      setSites(siteRes.data.results);
      setBuildings(buildingRes.data.results);
      setFloors(floorRes.data.results);
    }).catch(() => undefined);
  }, [branchId]);

  const reload = useCallback(async () => {
    if (!branchId) return;
    setLoading(true);
    try {
      const res = await projectsApi.construction(kind, 1, undefined, branchId);
      setRows(res.data.results);
    } finally {
      setLoading(false);
    }
  }, [branchId, kind]);

  useEffect(() => { void reload(); }, [reload]);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!form.project_id || !form.code?.trim() || !form.name?.trim()) return;
    setSaving(true);
    try {
      await projectsApi.createConstruction(kind, {
        ...form,
        floors_count: form.floors_count ? Number(form.floors_count) : undefined,
        level_number: form.level_number ? Number(form.level_number) : undefined,
        area_sqm: form.area_sqm ? Number(form.area_sqm) : undefined,
      });
      setForm({ project_id: form.project_id, code: "", name: "", status: "active" });
      await reload();
    } catch (err) {
      await appDialog.alert(err instanceof Error ? err.message : "Unable to create record.");
    } finally {
      setSaving(false);
    }
  };

  const columns: Column<ConstructionRecord>[] = [
    { key: "code", header: "Code", cell: (row) => row.code },
    { key: "name", header: "Name", cell: (row) => kind === "site" || kind === "unit" ? <Link className="font-medium text-primary hover:underline" to={`/project/construction/${kind}/${row.id}`}>{row.name}</Link> : row.name },
    { key: "status", header: "Status", cell: (row) => row.status || "—" },
    { key: "detail", header: "Details", cell: (row) => kind === "building" ? `${row.floors_count || 0} floors` : kind === "floor" ? `Level ${row.level_number || 0}` : kind === "unit" ? `${row.unit_type || "other"} · ${row.area_sqm || 0} sqm` : row.location || "—" },
  ];

  return (
    <PageLayout title="Construction" description="Maintain the site hierarchy for each project." breadcrumbs={["Home", "Project Management", "Construction"]}>
      <div className="mb-5 flex flex-wrap gap-2">
        {kinds.map((item) => <Button key={item.value} size="sm" variant={kind === item.value ? "default" : "outline"} onClick={() => setKind(item.value)}>{item.label}</Button>)}
      </div>
      {canCreate ? <ContentSection title={`Add ${kind}`}>
        <form className="grid gap-3 md:grid-cols-3" onSubmit={submit}>
          <Select value={form.project_id} onValueChange={(project_id) => setForm((s) => ({ ...s, project_id }))}><SelectTrigger><SelectValue placeholder="Project" /></SelectTrigger><SelectContent>{projects.map((p) => <SelectItem key={p.id} value={p.id}>{p.project_code} — {p.name}</SelectItem>)}</SelectContent></Select>
          <Input placeholder="Code" value={form.code || ""} onChange={(e) => setForm((s) => ({ ...s, code: e.target.value }))} />
          <Input placeholder="Name" value={form.name || ""} onChange={(e) => setForm((s) => ({ ...s, name: e.target.value }))} />
          {kind === "building" ? <Select value={form.site_id || ""} onValueChange={(site_id) => setForm((s) => ({ ...s, site_id }))}><SelectTrigger><SelectValue placeholder="Site" /></SelectTrigger><SelectContent>{sites.filter((site) => !form.project_id || site.project_id === form.project_id).map((site) => <SelectItem key={site.id} value={site.id}>{site.code} — {site.name}</SelectItem>)}</SelectContent></Select> : null}
          {kind === "building" ? <Input type="number" placeholder="Floor count" value={form.floors_count || ""} onChange={(e) => setForm((s) => ({ ...s, floors_count: e.target.value }))} /> : null}
          {kind === "floor" || kind === "unit" ? <Select value={form.building_id || ""} onValueChange={(building_id) => setForm((s) => ({ ...s, building_id }))}><SelectTrigger><SelectValue placeholder="Building" /></SelectTrigger><SelectContent>{buildings.filter((building) => !form.project_id || building.project_id === form.project_id).map((building) => <SelectItem key={building.id} value={building.id}>{building.code} — {building.name}</SelectItem>)}</SelectContent></Select> : null}
          {kind === "floor" ? <Input type="number" placeholder="Level number" value={form.level_number || ""} onChange={(e) => setForm((s) => ({ ...s, level_number: e.target.value }))} /> : null}
          {kind === "unit" ? <Select value={form.floor_id || "__none__"} onValueChange={(floor_id) => setForm((s) => ({ ...s, floor_id: floor_id === "__none__" ? "" : floor_id }))}><SelectTrigger><SelectValue placeholder="Floor (optional)" /></SelectTrigger><SelectContent><SelectItem value="__none__">No floor</SelectItem>{floors.filter((floor) => !form.project_id || floor.project_id === form.project_id).map((floor) => <SelectItem key={floor.id} value={floor.id}>{floor.code} — {floor.name}</SelectItem>)}</SelectContent></Select> : null}
          {kind === "unit" ? <><Select value={form.unit_type || "other"} onValueChange={(unit_type) => setForm((s) => ({ ...s, unit_type }))}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent>{["apartment", "shop", "office", "other"].map((value) => <SelectItem key={value} value={value}>{value}</SelectItem>)}</SelectContent></Select><Input type="number" placeholder="Area sqm" value={form.area_sqm || ""} onChange={(e) => setForm((s) => ({ ...s, area_sqm: e.target.value }))} /></> : null}
          <Button type="submit" loading={saving}><Plus className="mr-2 h-4 w-4" />Add {kind}</Button>
        </form>
      </ContentSection> : null}
      <ContentSection title={kinds.find((item) => item.value === kind)?.label || "Records"}><DataTable columns={columns} data={rows} loading={loading} emptyMessage={`No ${kind}s found.`} /></ContentSection>
    </PageLayout>
  );
}

export function ProjectConstructionDetailPage() {
  const { kind, id } = useParams<{ kind: ConstructionKind; id: string }>();
  const [row, setRow] = useState<ConstructionRecord | null>(null);
  useEffect(() => { if (kind && id) projectsApi.constructionGet(kind, id).then((res) => setRow(res.data)).catch(() => undefined); }, [kind, id]);
  return <PageLayout title={row?.name || "Construction record"} breadcrumbs={["Home", "Project Management", "Construction"]}><ContentSection title="Details"><div className="grid gap-3 text-sm sm:grid-cols-2">{row ? Object.entries(row).filter(([key]) => key !== "id").map(([key, value]) => <p key={key}><span className="capitalize text-muted-foreground">{key.replace(/_/g, " ")}</span> · {String(value ?? "—")}</p>) : <div className="h-32 animate-pulse rounded-xl bg-muted" />}</div></ContentSection></PageLayout>;
}
