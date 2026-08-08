import { useEffect, type ReactNode } from "react";
import { useUIStore } from "@/store/uiStore";

/** Pins brand + switcher focus to a business workspace while rendering a shared engine page. */
export function WorkspaceGate({ workspace, children }: { workspace: string; children: ReactNode }) {
  const setActiveWorkspace = useUIStore((s) => s.setActiveWorkspace);

  useEffect(() => {
    setActiveWorkspace(workspace);
  }, [workspace, setActiveWorkspace]);

  return <>{children}</>;
}
