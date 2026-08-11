import { useEffect, useState } from "react";
import { PageLayout } from "@/components/layout/PageLayout";
import { ContentSection } from "@/components/layout/ContentSection";
import { Button } from "@/components/ui/button";
import { DataTable } from "@/components/data/DataTable";
import { appDialog } from "@/components/feedback/AppDialog";
import { projectsApi, type ProjectInventoryAllocation } from "@/services/api/projects";

export function ProjectInventoryPage() {
  const [rows, setRows] = useState<ProjectInventoryAllocation[]>([]);
  const [form, setForm] = useState({ project_id: "", product_id: "", quantity: "", unit_cost: "", notes: "" });
  const load = () => projectsApi.inventoryAllocations().then((res) => setRows(res.data.results)).catch(() => undefined);
  useEffect(() => { void load(); }, []);
  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    try {
      await projectsApi.createInventoryAllocation({ ...form, source_type: "manual" });
      setForm({ project_id: "", product_id: "", quantity: "", unit_cost: "", notes: "" });
      load();
    } catch (error) { await appDialog.alert(error instanceof Error ? error.message : "Could not allocate inventory."); }
  };
  return <PageLayout title="Project Inventory" description="Allocate purchased inventory to project work and track its receipt source." breadcrumbs={["Home", "Project Management", "Inventory"]}>
    <ContentSection title="New allocation">
      <form className="grid gap-3 sm:grid-cols-2" onSubmit={submit}>
        {([
          ["project_id", "Project ID"], ["product_id", "Product ID"], ["quantity", "Quantity"], ["unit_cost", "Unit cost"], ["notes", "Notes"],
        ] as const).map(([key, label]) => <label key={key} className="grid gap-1 text-sm">{label}<input required={key !== "notes"} className="rounded-md border bg-background px-3 py-2" value={form[key]} onChange={(e) => setForm({ ...form, [key]: e.target.value })} /></label>)}
        <div className="flex items-end"><Button type="submit">Allocate inventory</Button></div>
      </form>
    </ContentSection>
    <ContentSection title="Allocations">
      <DataTable columns={[
        { key: "product_id", header: "Product", cell: (r) => r.product_id },
        { key: "quantity", header: "Quantity", cell: (r) => r.quantity },
        { key: "unit_cost", header: "Unit cost", cell: (r) => r.unit_cost },
        { key: "source_type", header: "Source", cell: (r) => r.source_type },
        { key: "allocated_at", header: "Allocated", cell: (r) => new Date(r.allocated_at).toLocaleString() },
      ]} data={rows} emptyMessage="No project inventory allocations yet." />
    </ContentSection>
  </PageLayout>;
}
