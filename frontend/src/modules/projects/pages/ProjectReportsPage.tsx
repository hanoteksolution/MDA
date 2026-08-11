import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { PageLayout } from "@/components/layout/PageLayout";
import { ContentSection } from "@/components/layout/ContentSection";
import { KpiCard, KpiGrid } from "@/components/data/KpiCard";
import { Button } from "@/components/ui/button";
import { useAuthStore } from "@/store/authStore";
import { projectsApi, type ProjectSummary } from "@/services/api/projects";
import { formatCurrency } from "@/utils/cn";

export function ProjectReportsPage() {
  const branchId = useAuthStore((s) => s.user?.branch?.id);
  const [summary, setSummary] = useState<ProjectSummary | null>(null);

  useEffect(() => {
    if (!branchId) return;
    projectsApi.summary(branchId).then((res) => setSummary(res.data)).catch(() => undefined);
  }, [branchId]);

  return (
    <PageLayout
      title="Project Reports"
      description="Portfolio KPIs and links into shared finance/reporting engines."
      breadcrumbs={["Home", "Project Management", "Reports"]}
      actions={
        <div className="flex gap-2">
          <Button asChild variant="outline" size="sm"><Link to="/project/finance">Finance</Link></Button>
          <Button asChild variant="outline" size="sm"><Link to="/project/billing">Billing</Link></Button>
        </div>
      }
    >
      <KpiGrid columns={4}>
        <KpiCard index={0} accent="primary" title="Projects" value={String(summary?.total_projects ?? 0)} />
        <KpiCard index={1} accent="warning" title="Active" value={String(summary?.active_projects ?? 0)} />
        <KpiCard index={2} accent="info" title="Budget" value={formatCurrency(summary?.total_budget ?? 0)} />
        <KpiCard index={3} accent="success" title="Open issues" value={String(summary?.open_issues_count ?? 0)} />
      </KpiGrid>
      <ContentSection title="Operational signals">
        <div className="grid gap-3 text-sm sm:grid-cols-2">
          <p>Tasks: {summary?.tasks_count ?? 0}</p>
          <p>Workers: {summary?.workers_count ?? 0}</p>
          <p>Open risks: {summary?.open_risks_count ?? 0}</p>
          <p>At risk projects: {summary?.at_risk_projects ?? 0}</p>
          <p>Contract value: {formatCurrency(summary?.total_contract_value ?? 0)}</p>
          <p>Cost estimate: {formatCurrency(summary?.total_cost_estimate ?? 0)}</p>
        </div>
      </ContentSection>
    </PageLayout>
  );
}
