/** Map industry workspace path codes to Product.module_code values. */
const WORKSPACE_TO_MODULE: Record<string, string> = {
  cafeteria: "restaurant",
  restaurant: "restaurant",
  gym: "gym",
  pharmacy: "pharmacy",
  hotel: "hotel",
  futsal: "futsal",
  property: "property_management",
  project: "project_management",
  travel: "travel_agency",
  retail: "retail",
};

const MODULE_LABELS: Record<string, string> = {
  gym: "Gym",
  restaurant: "Restaurant",
  pharmacy: "Pharmacy",
  hotel: "Hotel",
  futsal: "Futsal",
  retail: "Retail",
  shared: "Shared",
  property_management: "Property",
  project_management: "Projects",
  travel_agency: "Travel",
};

/** Soft tone classes for module badges (light + dark friendly). */
const MODULE_TONES: Record<string, string> = {
  gym: "bg-violet-600/90 text-white",
  restaurant: "bg-orange-600/90 text-white",
  pharmacy: "bg-teal-600/90 text-white",
  hotel: "bg-sky-600/90 text-white",
  futsal: "bg-lime-700/90 text-white",
  retail: "bg-amber-600/90 text-white",
  shared: "bg-slate-600/90 text-white",
  property_management: "bg-cyan-700/90 text-white",
  project_management: "bg-blue-700/90 text-white",
  travel_agency: "bg-indigo-600/90 text-white",
};

/**
 * Resolve the catalog module_code for the active industry workspace.
 * Returns undefined when not inside an industry scope (full tenant catalog).
 * Retail keeps "retail" so the API can merge shop-floor catalogs (gym/restaurant/…).
 */
export function productModuleCode(
  workspace: string | null | undefined,
  opts?: { pharmacyProfile?: boolean }
): string | undefined {
  if (opts?.pharmacyProfile) return "pharmacy";
  if (!workspace) return undefined;
  return WORKSPACE_TO_MODULE[workspace] || workspace;
}

export function normalizeProductModule(moduleCode?: string | null): string {
  return (moduleCode || "").trim().toLowerCase();
}

export function productModuleLabel(moduleCode?: string | null): string {
  const code = normalizeProductModule(moduleCode);
  if (!code) return "Shared";
  return (
    MODULE_LABELS[code] ||
    code.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())
  );
}

export function productModuleToneClass(moduleCode?: string | null): string {
  const code = normalizeProductModule(moduleCode);
  return MODULE_TONES[code] || "bg-muted text-foreground";
}
