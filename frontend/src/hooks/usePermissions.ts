import { useAuthStore } from "@/store/authStore";

export function usePermissions() {
  const user = useAuthStore((s) => s.user);
  const permissions = user?.permissions ?? [];
  const isSuperAdmin = user?.role?.slug === "super_admin";

  const hasPermission = (codename: string) => {
    if (isSuperAdmin) return true;
    return permissions.includes(codename);
  };

  const hasAnyPermission = (...codenames: string[]) => {
    if (isSuperAdmin) return true;
    return codenames.some((c) => permissions.includes(c));
  };

  const hasAllPermissions = (...codenames: string[]) => {
    if (isSuperAdmin) return true;
    return codenames.every((c) => permissions.includes(c));
  };

  return { permissions, isSuperAdmin, hasPermission, hasAnyPermission, hasAllPermissions };
}
