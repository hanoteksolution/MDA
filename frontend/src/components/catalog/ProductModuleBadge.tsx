import { Badge } from "@/components/ui/badge";
import { cn } from "@/utils/cn";
import {
  productModuleLabel,
  productModuleToneClass,
  normalizeProductModule,
} from "@/utils/productModuleScope";

interface ProductModuleBadgeProps {
  moduleCode?: string | null;
  className?: string;
  /** Compact for POS cards */
  size?: "sm" | "md";
}

/** Colored label showing which catalog module a product belongs to (Gym, Restaurant, …). */
export function ProductModuleBadge({
  moduleCode,
  className,
  size = "md",
}: ProductModuleBadgeProps) {
  const code = normalizeProductModule(moduleCode);
  if (!code) return null;
  const label = productModuleLabel(code);
  return (
    <Badge
      variant="secondary"
      className={cn(
        "border-0 font-semibold uppercase tracking-[0.1em] shadow-sm",
        size === "sm" ? "px-1.5 py-0 text-[8px]" : "px-2 py-0.5 text-[10px]",
        productModuleToneClass(code),
        className
      )}
      title={`Module: ${label}`}
    >
      {label}
    </Badge>
  );
}
