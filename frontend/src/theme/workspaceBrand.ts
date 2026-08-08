import { MODULE_WORKSPACES, type WorkspaceTone } from "@/navigation/moduleWorkspaces";
import { INDUSTRY_PATH_SET } from "@/navigation/businessWorkspaces";

export interface BrandTokens {
  primary: string;
  primaryHover: string;
  accent: string;
  accentForeground: string;
  sidebarAccent: string;
  ring: string;
  chart1: string;
}

const COMPANY: BrandTokens = {
  primary: "160 84% 39%",
  primaryHover: "160 84% 32%",
  accent: "160 84% 95%",
  accentForeground: "160 84% 25%",
  sidebarAccent: "160 84% 95%",
  ring: "160 84% 39%",
  chart1: "160 84% 39%",
};

const COMPANY_DARK: BrandTokens = {
  primary: "160 70% 48%",
  primaryHover: "160 70% 40%",
  accent: "160 50% 12%",
  accentForeground: "160 84% 70%",
  sidebarAccent: "160 50% 12%",
  ring: "160 70% 48%",
  chart1: "160 70% 48%",
};

function pair(
  light: Omit<BrandTokens, "ring" | "chart1" | "sidebarAccent"> & Partial<BrandTokens>,
  dark: Omit<BrandTokens, "ring" | "chart1" | "sidebarAccent"> & Partial<BrandTokens>
): { light: BrandTokens; dark: BrandTokens } {
  return {
    light: {
      ring: light.primary,
      chart1: light.primary,
      sidebarAccent: light.accent,
      ...light,
    } as BrandTokens,
    dark: {
      ring: dark.primary,
      chart1: dark.primary,
      sidebarAccent: dark.accent,
      ...dark,
    } as BrandTokens,
  };
}

/** HSL channel tokens per workspace tone (light / dark). */
export const TONE_BRAND: Record<WorkspaceTone, { light: BrandTokens; dark: BrandTokens }> = {
  sky: pair(
    { primary: "199 89% 48%", primaryHover: "200 90% 40%", accent: "199 95% 94%", accentForeground: "201 90% 27%" },
    { primary: "199 89% 58%", primaryHover: "199 89% 48%", accent: "201 50% 14%", accentForeground: "199 95% 78%" }
  ),
  orange: pair(
    { primary: "24 95% 53%", primaryHover: "21 90% 48%", accent: "33 100% 94%", accentForeground: "15 79% 34%" },
    { primary: "27 96% 61%", primaryHover: "24 95% 53%", accent: "22 50% 14%", accentForeground: "32 97% 80%" }
  ),
  blue: pair(
    { primary: "217 91% 60%", primaryHover: "221 83% 53%", accent: "214 95% 93%", accentForeground: "224 76% 40%" },
    { primary: "213 94% 68%", primaryHover: "217 91% 60%", accent: "217 50% 14%", accentForeground: "213 97% 82%" }
  ),
  teal: pair(
    { primary: "173 80% 40%", primaryHover: "175 77% 32%", accent: "167 85% 93%", accentForeground: "175 77% 26%" },
    { primary: "172 66% 50%", primaryHover: "173 80% 40%", accent: "175 45% 12%", accentForeground: "170 77% 78%" }
  ),
  indigo: pair(
    { primary: "239 84% 67%", primaryHover: "243 75% 59%", accent: "226 100% 94%", accentForeground: "243 75% 40%" },
    { primary: "234 89% 74%", primaryHover: "239 84% 67%", accent: "239 40% 16%", accentForeground: "230 94% 84%" }
  ),
  violet: pair(
    { primary: "258 90% 66%", primaryHover: "262 83% 58%", accent: "251 91% 95%", accentForeground: "263 70% 42%" },
    { primary: "255 92% 76%", primaryHover: "258 90% 66%", accent: "261 40% 16%", accentForeground: "252 95% 85%" }
  ),
  emerald: pair(COMPANY, COMPANY_DARK),
  green: pair(
    { primary: "142 71% 45%", primaryHover: "142 76% 36%", accent: "141 79% 93%", accentForeground: "144 80% 26%" },
    { primary: "142 69% 58%", primaryHover: "142 71% 45%", accent: "144 40% 12%", accentForeground: "141 79% 80%" }
  ),
  amber: pair(
    { primary: "38 92% 50%", primaryHover: "32 95% 44%", accent: "48 96% 89%", accentForeground: "26 90% 30%" },
    { primary: "43 96% 56%", primaryHover: "38 92% 50%", accent: "32 50% 12%", accentForeground: "48 96% 76%" }
  ),
  cyan: pair(
    { primary: "189 94% 43%", primaryHover: "192 91% 36%", accent: "186 94% 94%", accentForeground: "193 84% 28%" },
    { primary: "188 86% 53%", primaryHover: "189 94% 43%", accent: "192 45% 12%", accentForeground: "187 92% 78%" }
  ),
  stone: pair(
    { primary: "24 10% 45%", primaryHover: "24 10% 37%", accent: "60 5% 94%", accentForeground: "24 10% 23%" },
    { primary: "24 6% 64%", primaryHover: "24 10% 45%", accent: "24 10% 14%", accentForeground: "24 6% 80%" }
  ),
  lime: pair(
    { primary: "84 81% 44%", primaryHover: "85 78% 36%", accent: "80 89% 89%", accentForeground: "88 79% 22%" },
    { primary: "82 77% 55%", primaryHover: "84 81% 44%", accent: "85 40% 12%", accentForeground: "81 88% 78%" }
  ),
  slate: pair(
    { primary: "215 19% 47%", primaryHover: "215 25% 39%", accent: "210 20% 94%", accentForeground: "215 25% 27%" },
    { primary: "216 12% 65%", primaryHover: "215 19% 47%", accent: "217 20% 14%", accentForeground: "214 15% 80%" }
  ),
  fuchsia: pair(
    { primary: "292 84% 61%", primaryHover: "293 69% 49%", accent: "287 100% 95%", accentForeground: "295 72% 37%" },
    { primary: "291 93% 73%", primaryHover: "292 84% 61%", accent: "293 40% 14%", accentForeground: "291 95% 85%" }
  ),
  rose: pair(
    { primary: "347 77% 60%", primaryHover: "346 77% 50%", accent: "356 100% 95%", accentForeground: "347 77% 34%" },
    { primary: "351 95% 71%", primaryHover: "347 77% 60%", accent: "347 40% 14%", accentForeground: "353 96% 82%" }
  ),
  zinc: pair(
    { primary: "240 5% 46%", primaryHover: "240 4% 38%", accent: "240 5% 94%", accentForeground: "240 6% 26%" },
    { primary: "240 5% 64%", primaryHover: "240 5% 46%", accent: "240 4% 14%", accentForeground: "240 5% 80%" }
  ),
  neutral: pair(
    { primary: "0 0% 45%", primaryHover: "0 0% 37%", accent: "0 0% 94%", accentForeground: "0 0% 25%" },
    { primary: "0 0% 64%", primaryHover: "0 0% 45%", accent: "0 0% 14%", accentForeground: "0 0% 80%" }
  ),
  purple: pair(
    { primary: "271 81% 56%", primaryHover: "272 72% 47%", accent: "270 95% 95%", accentForeground: "274 66% 32%" },
    { primary: "270 91% 65%", primaryHover: "271 81% 56%", accent: "273 40% 14%", accentForeground: "269 100% 85%" }
  ),
  pink: pair(
    { primary: "330 81% 60%", primaryHover: "333 71% 51%", accent: "327 87% 95%", accentForeground: "336 74% 35%" },
    { primary: "329 86% 70%", primaryHover: "330 81% 60%", accent: "333 40% 14%", accentForeground: "327 87% 85%" }
  ),
};

export function workspaceFromPath(pathname: string): string | null {
  if (pathname === "/modules" || pathname.startsWith("/modules/")) return "hub";
  const first = pathname.split("/").filter(Boolean)[0];
  if (first && INDUSTRY_PATH_SET.has(first)) return first;
  if (pathname.startsWith("/housing")) return "property";
  if (pathname.startsWith("/office")) return "property";
  if (pathname.startsWith("/pos")) return "pos";
  if (pathname.startsWith("/inventory") || pathname.startsWith("/products") || pathname.startsWith("/categories")) {
    return "inventory";
  }
  if (
    pathname.startsWith("/sales") ||
    pathname.startsWith("/receipts") ||
    pathname.startsWith("/customers") ||
    pathname.startsWith("/daily-ops") ||
    pathname.startsWith("/expenses") ||
    pathname.startsWith("/trash")
  ) {
    return "sales";
  }
  if (pathname.startsWith("/purchases") || pathname.startsWith("/suppliers")) return "purchases";
  if (pathname.startsWith("/reports") || pathname.startsWith("/staff-performance")) return "reports";
  if (pathname.startsWith("/finance")) return "finance";
  if (pathname.startsWith("/platform")) return "platform";
  if (pathname.startsWith("/admin")) return "admin";
  if (pathname.startsWith("/settings")) return "settings";
  if (pathname.startsWith("/dashboard")) return "overview";
  if (pathname.startsWith("/login") || pathname.startsWith("/setup") || pathname.startsWith("/onboard")) {
    return "hub";
  }
  return null;
}

export function toneForWorkspace(code: string): WorkspaceTone {
  if (code === "hub") return "emerald";
  return MODULE_WORKSPACES.find((w) => w.code === code)?.tone ?? "emerald";
}

export function brandForWorkspace(code: string, darkMode: boolean): BrandTokens {
  const tone = toneForWorkspace(code);
  return darkMode ? TONE_BRAND[tone].dark : TONE_BRAND[tone].light;
}

export function applyWorkspaceBrand(code: string, darkMode = false): void {
  if (typeof document === "undefined") return;
  const tokens = brandForWorkspace(code, darkMode);
  const root = document.documentElement;
  root.style.setProperty("--primary", tokens.primary);
  root.style.setProperty("--primary-hover", tokens.primaryHover);
  root.style.setProperty("--primary-foreground", "0 0% 100%");
  root.style.setProperty("--accent", tokens.accent);
  root.style.setProperty("--accent-foreground", tokens.accentForeground);
  root.style.setProperty("--sidebar-accent", tokens.sidebarAccent);
  root.style.setProperty("--ring", tokens.ring);
  root.style.setProperty("--chart-1", tokens.chart1);
  root.dataset.workspace = code;
  root.dataset.workspaceTone = toneForWorkspace(code);
}
