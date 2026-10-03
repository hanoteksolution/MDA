/**
 * Provisioning stages recorded by the backend (`TenantProvisioningService.STAGES`)
 * and returned as `stages` on the registration payload. The UI only marks a stage
 * complete when the server reported it — it never simulates progress.
 */
export const PROVISIONING_STAGES = [
  { id: "company", label: "Creating company" },
  { id: "workspace", label: "Reserving workspace URL" },
  { id: "owner", label: "Creating owner account" },
  { id: "modules", label: "Enabling modules" },
  { id: "subscription", label: "Activating plan" },
  { id: "accounting", label: "Preparing accounting" },
  { id: "final_checks", label: "Finalizing workspace" },
] as const;

export interface ProvisioningStageEvent {
  stage: string;
  status: string;
  message?: string;
}

export interface ProvisioningStageSummary {
  id: string;
  label: string;
  status: string;
}

/** Collapse the job log to one row per stage (latest status wins), in server order. */
export function summarizeProvisioningStages(
  events: ProvisioningStageEvent[] | null | undefined
): ProvisioningStageSummary[] {
  const latest = new Map<string, string>();
  for (const event of events || []) {
    if (!event?.stage) continue;
    latest.set(event.stage, event.status);
  }
  return Array.from(latest.entries()).map(([id, status]) => ({
    id,
    status,
    label:
      PROVISIONING_STAGES.find((stage) => stage.id === id)?.label ||
      id.replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase()),
  }));
}
