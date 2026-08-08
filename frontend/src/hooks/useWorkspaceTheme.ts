import { useEffect } from "react";
import { useLocation } from "react-router-dom";
import { useUIStore } from "@/store/uiStore";
import { applyWorkspaceBrand, workspaceFromPath } from "@/theme/workspaceBrand";

/** Keep the active workspace + brand color in sync with the current route. */
export function useWorkspaceTheme() {
  const location = useLocation();
  const darkMode = useUIStore((s) => s.darkMode);
  const activeWorkspace = useUIStore((s) => s.activeWorkspace);
  const setActiveWorkspace = useUIStore((s) => s.setActiveWorkspace);

  useEffect(() => {
    const inferred = workspaceFromPath(location.pathname);
    if (inferred && inferred !== activeWorkspace) {
      setActiveWorkspace(inferred);
      return;
    }
    applyWorkspaceBrand(activeWorkspace, darkMode);
  }, [location.pathname, darkMode, activeWorkspace, setActiveWorkspace]);
}
