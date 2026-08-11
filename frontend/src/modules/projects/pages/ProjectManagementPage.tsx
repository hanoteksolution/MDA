import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Briefcase, CalendarDays, ShieldAlert, Wallet, Users } from "lucide-react";
import { PageLayout } from "@/components/layout/PageLayout";
import { KpiCard, KpiGrid } from "@/components/data/KpiCard";
import { ContentSection } from "@/components/layout/ContentSection";
import { Button } from "@/components/ui/button";
import { useAuthStore } from "@/store/authStore";
import { projectsApi, type ProjectSummary } from "@/services/api/projects";
import { formatCurrency } from "@/utils/cn";

export function ProjectManagementPage() {
  const branchId = useAuthStore((s) => s.user?.branch?.id);
  const [summary, setSummary] = useState<ProjectSummary | null>(null);

  useEffect(() => {
    if (!branchId) return;
    projectsApi.summary(branchId).then((res) => setSummary(res.data)).catch(() => undefined);
  }, [branchId]);

  return (
    <PageLayout
      title="Project Management"
      description="Manage projects, budgets, workforce, and delivery lifecycle with shared ERP engines."
      breadcrumbs={["Home", "Project Management"]}
      actions={
        <div className="flex gap-2">
          <Button asChild variant="outline" size="sm">
            <Link to="/project/wbs">WBS</Link>
          </Button>
          <Button asChild variant="outline" size="sm">
            <Link to="/project/budgets">Budgets</Link>
          </Button>
          <Button asChild variant="outline" size="sm">
            <Link to="/project/construction">Construction</Link>
          </Button>
          <Button asChild variant="outline" size="sm">
            <Link to="/project/boq">BOQ</Link>
          </Button>
          <Button asChild variant="outline" size="sm">
            <Link to="/project/tasks">Tasks</Link>
          </Button>
          <Button asChild variant="outline" size="sm">
            <Link to="/project/milestones">Milestones</Link>
          </Button>
          <Button asChild variant="outline" size="sm">
            <Link to="/project/workforce">Workforce</Link>
          </Button>
          <Button asChild variant="outline" size="sm">
            <Link to="/project/projects">Projects</Link>
          </Button>
          <Button asChild variant="outline" size="sm">
            <Link to="/project/procurement">Procurement</Link>
          </Button>
          <Button asChild variant="outline" size="sm">
            <Link to="/project/expenses">Expenses</Link>
          </Button>
          <Button asChild variant="outline" size="sm">
            <Link to="/project/site-reports">Site reports</Link>
          </Button>
          <Button asChild variant="outline" size="sm">
            <Link to="/project/quality">Quality</Link>
          </Button>
          <Button asChild variant="outline" size="sm">
            <Link to="/project/safety">Safety</Link>
          </Button>
          <Button asChild variant="outline" size="sm">
            <Link to="/project/inventory">Inventory</Link>
          </Button>
          <Button asChild variant="outline" size="sm">
            <Link to="/project/field">Field</Link>
          </Button>
        </div>
      }
    >
      <KpiGrid columns={3}>
        <KpiCard
          index={0}
          accent="primary"
          title="Projects"
          value={String(summary?.total_projects ?? 0)}
          icon={<Briefcase className="h-5 w-5" />}
        />
        <KpiCard
          index={1}
          accent="warning"
          title="Active / At Risk"
          value={String((summary?.active_projects ?? 0) + (summary?.at_risk_projects ?? 0))}
          icon={<CalendarDays className="h-5 w-5" />}
        />
        <KpiCard
          index={2}
          accent="info"
          title="Total Budget"
          value={formatCurrency(summary?.total_budget ?? 0)}
          icon={<Wallet className="h-5 w-5" />}
        />
        <KpiCard
          index={3}
          accent="success"
          title="Completed"
          value={String(summary?.completed_projects ?? 0)}
          icon={<Users className="h-5 w-5" />}
        />
        <KpiCard
          index={4}
          accent="warning"
          title="Open Risks"
          value={String(summary?.open_risks_count ?? 0)}
          icon={<ShieldAlert className="h-5 w-5" />}
        />
        <KpiCard
          index={5}
          accent="warning"
          title="Open Issues"
          value={String(summary?.open_issues_count ?? 0)}
          icon={<ShieldAlert className="h-5 w-5" />}
        />
      </KpiGrid>
      <ContentSection
        title="Workspace Scope"
        description="Projects, delivery planning, field operations, controls, and project billing are available in this workspace."
      >
        <p className="text-sm text-muted-foreground">
          Use the Projects link above to manage the portfolio, and the project navigation for
          procurement, equipment, change orders, risks, issues, and billing.
        </p>
      </ContentSection>
    </PageLayout>
  );
}
