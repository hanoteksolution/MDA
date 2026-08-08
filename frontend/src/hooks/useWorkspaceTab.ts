import { useCallback, useMemo } from "react";
import { useLocation, useNavigate } from "react-router-dom";

/**
 * Syncs industry mega-page tabs to workspace URLs.
 * `/gym/classes` → tab "classes"; clicking Attendance → `/gym/attendance`.
 */
export function useWorkspaceTab<T extends string>(
  workspaceRoot: string,
  suffixToTab: Record<string, T>,
  defaultTab: T
): [T, (tab: T) => void] {
  const location = useLocation();
  const navigate = useNavigate();
  const root = workspaceRoot.replace(/\/+$/, "") || "/";

  const tab = useMemo(() => {
    const path = location.pathname.replace(/\/+$/, "") || "/";
    if (path === root || path === `${root}/dashboard`) return defaultTab;
    if (!path.startsWith(`${root}/`)) return defaultTab;
    const suffix = path.slice(root.length + 1);
    return suffixToTab[suffix] ?? defaultTab;
  }, [location.pathname, root, suffixToTab, defaultTab]);

  const setTab = useCallback(
    (next: T) => {
      const suffix = Object.entries(suffixToTab).find(([, value]) => value === next)?.[0] ?? "";
      const to = suffix ? `${root}/${suffix}` : root;
      const current = location.pathname.replace(/\/+$/, "") || "/";
      if (current !== to) navigate(to);
    },
    [suffixToTab, root, navigate, location.pathname]
  );

  return [tab, setTab];
}
