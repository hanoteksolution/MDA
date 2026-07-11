import { Package, TrendingUp } from "lucide-react";
import { ProductImagePreview } from "@/components/catalog/ProductImage";
import { Badge } from "@/components/ui/badge";
import { cn, formatCurrency } from "@/utils/cn";

interface ProductPreviewCardProps {
  image?: string;
  name: string;
  sku: string;
  categoryName?: string;
  isActive: boolean;
  cost: number;
  price: number;
  margin: number;
}

export function ProductPreviewCard({
  image,
  name,
  sku,
  categoryName,
  isActive,
  cost,
  price,
  margin,
}: ProductPreviewCardProps) {
  return (
    <div className="ds-card-premium overflow-hidden">
      <div className="border-b border-border/60 px-5 py-4">
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10 text-primary">
            <Package className="h-4 w-4" />
          </div>
          <div>
            <p className="text-sm font-semibold tracking-tight">Live preview</p>
            <p className="text-[11px] text-muted-foreground">Catalog & POS appearance</p>
          </div>
        </div>
      </div>

      <div className="space-y-5 p-5">
        <div className="overflow-hidden rounded-2xl border border-border/50 bg-background shadow-[inset_0_1px_0_hsl(var(--background))]">
          <ProductImagePreview
            image={image}
            name={name}
            sku={sku}
            categoryName={categoryName}
            className="aspect-square rounded-none border-0"
          />
          <div className="space-y-2 border-t border-border/50 bg-card/80 px-4 py-3.5">
            {categoryName && (
              <span className="inline-flex rounded-full bg-primary/10 px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-[0.14em] text-primary">
                {categoryName}
              </span>
            )}
            <p className="text-[15px] font-semibold leading-snug tracking-tight text-foreground">
              {name || "Product name"}
            </p>
            <p className="font-mono text-[11px] text-muted-foreground">{sku || "SKU-0000"}</p>
            <div className="flex items-center justify-between pt-1">
              <span className="text-lg font-bold tabular-nums tracking-tight text-primary">
                {formatCurrency(price)}
              </span>
              <Badge variant={isActive ? "success" : "secondary"} className="text-[10px]">
                {isActive ? "Active" : "Draft"}
              </Badge>
            </div>
          </div>
        </div>

        <div className="rounded-2xl border border-border/50 bg-muted/20 p-4">
          <div className="mb-3 flex items-center justify-between">
            <span className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
              Economics
            </span>
            <span
              className={cn(
                "flex items-center gap-1 text-xs font-semibold tabular-nums",
                margin >= 0 ? "text-emerald-600 dark:text-emerald-400" : "text-destructive"
              )}
            >
              <TrendingUp className="h-3.5 w-3.5" />
              {margin.toFixed(1)}% margin
            </span>
          </div>
          <div className="space-y-2.5">
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Cost</span>
              <span className="tabular-nums">{formatCurrency(cost)}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Retail price</span>
              <span className="font-semibold tabular-nums">{formatCurrency(price)}</span>
            </div>
          </div>
          <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-muted">
            <div
              className={cn(
                "h-full rounded-full transition-all duration-300",
                margin >= 30 ? "bg-emerald-500" : margin >= 10 ? "bg-primary" : "bg-amber-500"
              )}
              style={{ width: `${Math.min(100, Math.max(0, margin))}%` }}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
