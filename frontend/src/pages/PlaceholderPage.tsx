import { ModulePage } from "@/components/layout/ModulePage";

interface PlaceholderPageProps {
  title: string;
  description: string;
  phase: string;
}

export function PlaceholderPage({ title, description, phase }: PlaceholderPageProps) {
  return (
    <ModulePage
      title={title}
      description={description}
      phase={phase}
    />
  );
}
