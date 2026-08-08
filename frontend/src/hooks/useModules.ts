import { useAuthStore } from "@/store/authStore";
import { usePermissions } from "@/hooks/usePermissions";

export function useModules() {
  const user = useAuthStore((s) => s.user);
  const { isSuperAdmin } = usePermissions();
  const modules = user?.enabled_modules ?? [];
  const features = user?.module_features ?? {};

  const hasModule = (code: string) => {
    if (isSuperAdmin) return true;
    if (!code) return true;
    // Until modules are hydrated, avoid blanking the whole nav for legacy sessions.
    if (!user?.enabled_modules) return true;
    // /me returns usable modules only (enabled + required deps).
    return modules.includes(code);
  };

  const hasAnyModule = (...codes: string[]) => {
    if (isSuperAdmin) return true;
    if (!user?.enabled_modules) return true;
    return codes.some((c) => modules.includes(c));
  };

  const hasFeature = (moduleCode: string, feature: string) => {
    if (isSuperAdmin) return true;
    if (!hasModule(moduleCode)) return false;
    const map = features[moduleCode];
    if (!map) return true;
    return map[feature] !== false;
  };

  return { modules, features, hasModule, hasAnyModule, hasFeature };
}
