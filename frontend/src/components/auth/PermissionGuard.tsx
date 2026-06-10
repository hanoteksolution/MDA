import { Navigate } from "react-router-dom";
import { usePermissions } from "@/hooks/usePermissions";

interface PermissionGuardProps {
  children: React.ReactNode;
  /** Single permission or any-of list */
  permission: string | string[];
  fallback?: string;
}

export function PermissionGuard({
  children,
  permission,
  fallback = "/dashboard",
}: PermissionGuardProps) {
  const { hasPermission, hasAnyPermission } = usePermissions();
  const allowed = Array.isArray(permission)
    ? hasAnyPermission(...permission)
    : hasPermission(permission);

  if (!allowed) {
    return <Navigate to={fallback} replace />;
  }

  return <>{children}</>;
}
