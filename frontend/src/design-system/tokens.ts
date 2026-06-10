/**
 * MDA ERP Design System Tokens
 * Single source of truth for spacing, typography, and semantic values.
 * Use Tailwind classes mapped to CSS variables — never hardcode colors in pages.
 */

export const spacing = {
  page: "p-6",
  section: "space-y-6",
  card: "p-6",
  gap: "gap-6",
  gapSm: "gap-4",
} as const;

export const layout = {
  sidebarWidth: "280px",
  sidebarCollapsed: "72px",
  headerHeight: "72px",
  footerHeight: "32px",
  contentMaxWidth: "1600px",
} as const;

export const typography = {
  pageTitle: "text-2xl font-semibold tracking-tight text-foreground",
  sectionTitle: "text-base font-semibold text-foreground",
  cardTitle: "text-sm font-medium text-muted-foreground",
  body: "text-sm text-foreground",
  caption: "text-xs text-muted-foreground",
  kpiValue: "text-2xl font-bold tracking-tight text-foreground",
} as const;

export const animation = {
  pageEnter: {
    initial: { opacity: 0, y: 8 },
    animate: { opacity: 1, y: 0 },
    transition: { duration: 0.35, ease: "easeOut" as const },
  },
  stagger: {
    container: {
      hidden: { opacity: 0 },
      show: { opacity: 1, transition: { staggerChildren: 0.06 } },
    },
    item: {
      hidden: { opacity: 0, y: 12 },
      show: { opacity: 1, y: 0, transition: { duration: 0.3 } },
    },
  },
} as const;

export const chartColors = {
  primary: "hsl(160 84% 39%)",
  primaryLight: "hsl(160 84% 39% / 0.2)",
  secondary: "hsl(222 47% 11%)",
  revenue: "hsl(160 84% 39%)",
  profit: "hsl(199 89% 48%)",
  sales: "hsl(262 83% 58%)",
  grid: "hsl(214 32% 91%)",
} as const;
