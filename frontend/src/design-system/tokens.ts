/**
 * MDA ERP Design System Tokens
 * Single source of truth for spacing, typography, density, and semantic values.
 * Use Tailwind classes mapped to CSS variables — never hardcode colors in pages.
 */

export const spacing = {
  page: "p-6",
  pageDense: "p-4 xl:p-5",
  section: "space-y-6",
  sectionDense: "space-y-4",
  card: "p-6",
  cardDense: "p-4",
  gap: "gap-6",
  gapSm: "gap-4",
  gapXs: "gap-2",
} as const;

export const density = {
  /** Default data-dense UI for list/admin screens */
  tableHead: "h-9 px-3 text-[11px]",
  tableCell: "px-3 py-2 text-sm",
  tableRow: "h-10",
  navItem: "min-h-10 px-3 py-2",
  tab: "min-h-9 px-3 py-1.5 text-sm",
} as const;

export const touch = {
  /** WCAG-ish comfortable touch target */
  min: "min-h-11 min-w-11",
  target: "h-11 w-11",
  button: "min-h-10 px-4",
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
  emptyTitle: "text-base font-semibold text-foreground",
  emptyDescription: "text-sm text-muted-foreground",
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
