import type { ReactNode } from "react";
import { Construction } from "lucide-react";
import { PageLayout } from "@/components/layout/PageLayout";
import { ContentSection } from "@/components/layout/ContentSection";
import { Badge } from "@/components/ui/badge";

interface ModulePageProps {
  title: string;
  description: string;
  phase: string;
  breadcrumbs?: string[];
  actions?: ReactNode;
  children?: ReactNode;
}

export function ModulePage({
  title,
  description,
  phase,
  breadcrumbs,
  actions,
  children,
}: ModulePageProps) {
  return (
    <PageLayout
      title={title}
      description={description}
      breadcrumbs={breadcrumbs ?? ["Home", title]}
      actions={actions}
    >
      {children ?? (
        <ContentSection>
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-muted mb-6">
              <Construction className="h-8 w-8 text-muted-foreground" />
            </div>
            <Badge variant="secondary" className="mb-4">
              {phase}
            </Badge>
            <h3 className="text-lg font-semibold text-foreground">Coming Soon</h3>
            <p className="mt-2 max-w-md text-sm text-muted-foreground">
              The {title} module is scheduled for {phase}. All modules share the same
              enterprise design system for a consistent experience.
            </p>
          </div>
        </ContentSection>
      )}
    </PageLayout>
  );
}
