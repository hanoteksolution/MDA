import { useEffect, useState } from "react";
import { PageLayout } from "@/components/layout/PageLayout";
import { ContentSection } from "@/components/layout/ContentSection";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { appDialog } from "@/components/feedback/AppDialog";
import { travelApi, type TravelDestination } from "@/services/api/travel";

export function TravelDestinationPage() {
  const [rows, setRows] = useState<TravelDestination[]>([]);
  const [form, setForm] = useState({ country: "", city: "", name: "", code: "" });
  const load = () => travelApi.destinations().then((r) => setRows(r.data.results)).catch(() => setRows([]));
  useEffect(() => { void load(); }, []);
  const save = async (e: React.FormEvent) => { e.preventDefault(); try { await travelApi.createDestination(form); setForm({ country:"", city:"", name:"", code:"" }); load(); } catch (err) { await appDialog.alert(err instanceof Error ? err.message : "Unable to save destination"); } };
  return <PageLayout title="Destinations" breadcrumbs={["Travel", "Destinations"]}><ContentSection title="Add destination"><form className="grid gap-3 md:grid-cols-5" onSubmit={save}><Input required placeholder="Country" value={form.country} onChange={e=>setForm({...form,country:e.target.value})}/><Input required placeholder="City" value={form.city} onChange={e=>setForm({...form,city:e.target.value})}/><Input required placeholder="Name" value={form.name} onChange={e=>setForm({...form,name:e.target.value})}/><Input required placeholder="Code" value={form.code} onChange={e=>setForm({...form,code:e.target.value})}/><Button>Add destination</Button></form></ContentSection><ContentSection title="Saved destinations"><div className="space-y-2">{rows.map(d=><div key={d.id} className="rounded border p-3"><b>{d.name}</b> <span className="text-muted-foreground">({d.code}) · {d.city}, {d.country}</span></div>)}</div></ContentSection></PageLayout>;
}
