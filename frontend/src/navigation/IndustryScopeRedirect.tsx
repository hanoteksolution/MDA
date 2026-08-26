import { useEffect } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useUIStore } from "@/store/uiStore";
import { isIndustryPath } from "@/navigation/businessWorkspaces";
import { scopePath } from "@/hooks/useScopedPath";
import { workspaceFromPath } from "@/theme/workspaceBrand";

/**
 * When an industry workspace is selected, rewrite unscoped shared-engine URLs
 * (e.g. /products/new) to /{workspace}/products/new so the module stays pinned.
 */
export function IndustryScopeRedirect() {
  const location = useLocation();
  const navigate = useNavigate();
  const activeWorkspace = useUIStore((s) => s.activeWorkspace);

  useEffect(() => {
    if (!isIndustryPath(activeWorkspace)) return;
    // Already on an industry (or other workspace) path — leave alone.
    if (workspaceFromPath(location.pathname)) return;

    const scopedPath = scopePath(location.pathname, activeWorkspace);
    if (scopedPath !== location.pathname) {
      navigate(`${scopedPath}${location.search}${location.hash}`, { replace: true });
    }
  }, [activeWorkspace, location.pathname, location.search, location.hash, navigate]);

  return null;
}
