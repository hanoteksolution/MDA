import { Navigate } from "react-router-dom";
import { useAuthStore } from "@/store/authStore";
import { useModules } from "@/hooks/useModules";
import { usePermissions } from "@/hooks/usePermissions";

interface PermissionGuardProps {
  children: React.ReactNode;
  /** Single permission or any-of list */
  permission: string | string[];
  /** TenantModule code(s); also requires dependencies (usable set from /me). */
  module?: string | string[];
  fallback?: string;
}

export function PermissionGuard({
  children,
  permission,
  module,
  fallback = "/dashboard",
}: PermissionGuardProps) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const isLoading = useAuthStore((s) => s.isLoading);
  const user = useAuthStore((s) => s.user);
  const { hasPermission, hasAnyPermission } = usePermissions();
  const { hasModule, hasAnyModule } = useModules();

  // Refresh / cold start: token exists but /me has not returned yet — do not redirect.
  if (isAuthenticated && (isLoading || !user)) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    );
  }

  const allowed = Array.isArray(permission)
    ? hasAnyPermission(...permission)
    : hasPermission(permission);

  if (!allowed) {
    return <Navigate to={fallback} replace />;
  }
  if (module) {
    const moduleOk = Array.isArray(module) ? hasAnyModule(...module) : hasModule(module);
    if (!moduleOk) {
      return <Navigate to={fallback} replace />;
    }
  }

  return <>{children}</>;
}
