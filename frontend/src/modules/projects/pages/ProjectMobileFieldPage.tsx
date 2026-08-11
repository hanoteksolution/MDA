import { useEffect, useState } from "react";
import { PageLayout } from "@/components/layout/PageLayout";
import { ContentSection } from "@/components/layout/ContentSection";
import { Button } from "@/components/ui/button";
import { appDialog } from "@/components/feedback/AppDialog";
import { projectsApi, type ProjectMobileSummary, type ProjectMobileTask } from "@/services/api/projects";

export function ProjectMobileFieldPage() {
  const [summary, setSummary] = useState<ProjectMobileSummary | null>(null);
  const [tasks, setTasks] = useState<ProjectMobileTask[]>([]);
  const [projectId, setProjectId] = useState("");
  const [message, setMessage] = useState("");
  useEffect(() => {
    projectsApi.mobileSummary().then((r) => setSummary(r.data)).catch(() => undefined);
    projectsApi.mobileTasks().then((r) => setTasks(r.data)).catch(() => undefined);
  }, []);
  const submit = async (kind: "site" | "safety") => {
    if (!projectId || !message) return;
    try {
      if (kind === "site") await projectsApi.mobileSiteReport({ project_id: projectId, report_date: new Date().toISOString().slice(0, 10), summary: message });
      else await projectsApi.mobileSafetyIncident({ project_id: projectId, incident_date: new Date().toISOString().slice(0, 10), severity: "medium", title: "Field incident", description: message });
      setMessage("");
      await appDialog.alert("Submitted.");
    } catch (error) { await appDialog.alert(error instanceof Error ? error.message : "Submission failed."); }
  };
  return <PageLayout title="Field" description="Mobile-first tasks, attendance, and field reporting." breadcrumbs={["Home", "Project Management", "Field"]}>
    <div className="grid gap-4 sm:grid-cols-2"><ContentSection title="Today"><p className="text-2xl font-semibold">{summary?.my_open_tasks ?? 0}</p><p className="text-sm text-muted-foreground">Open tasks · {summary?.active_projects ?? 0} active projects</p></ContentSection>
      <ContentSection title="My tasks">{tasks.length ? <ul className="space-y-2">{tasks.map((task) => <li key={task.id} className="rounded border p-3"><strong>{task.title}</strong><p className="text-sm text-muted-foreground">{task.priority} · {task.status}</p></li>)}</ul> : <p className="text-sm text-muted-foreground">No open tasks.</p>}</ContentSection></div>
    <ContentSection title="Site report or safety incident">
      <div className="grid gap-3"><input className="rounded-md border bg-background px-3 py-2" placeholder="Project ID" value={projectId} onChange={(e) => setProjectId(e.target.value)} /><textarea className="min-h-28 rounded-md border bg-background px-3 py-2" placeholder="What happened on site?" value={message} onChange={(e) => setMessage(e.target.value)} /><div className="flex gap-2"><Button onClick={() => void submit("site")}>Submit site report</Button><Button variant="destructive" onClick={() => void submit("safety")}>Report safety incident</Button></div></div>
    </ContentSection>
  </PageLayout>;
}
