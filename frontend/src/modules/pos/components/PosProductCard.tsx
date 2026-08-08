import { motion } from "framer-motion";
import { Heart, Plus, ShoppingBag, Package } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn, formatCurrency } from "@/utils/cn";
import type { Product } from "@/types/models/catalog";
import { ProductImage, getStockStatus } from "@/components/catalog/ProductImage";

interface PosProductCardProps {
  product: Product;
  isFavorite: boolean;
  onAdd: () => void;
  onToggleFavorite: () => void;
  index?: number;
}

export function PosProductCard({
  product,
  isFavorite,
  onAdd,
  onToggleFavorite,
  index = 0,
}: PosProductCardProps) {
  const stock = product.total_stock ?? 0;
  const status = getStockStatus(stock, product.minimum_stock);
  const outOfStock = stock <= 0;

  return (
    <motion.article
      layout
      initial={{ opacity: 0, y: 10, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.28, delay: Math.min(index * 0.015, 0.15), ease: [0.22, 1, 0.36, 1] }}
      whileHover={{ y: -3, transition: { duration: 0.18 } }}
      onClick={() => !outOfStock && onAdd()}
      className={cn(
        "pos-product-card group relative flex cursor-pointer flex-col overflow-hidden",
        "ring-1 ring-transparent transition-all duration-300",
        "hover:border-primary/25 hover:shadow-[0_10px_28px_hsl(var(--primary)/0.12)] hover:ring-primary/10",
        outOfStock && "cursor-not-allowed opacity-45 grayscale"
      )}
    >
      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation();
          onToggleFavorite();
        }}
        className={cn(
          "absolute right-2 top-2 z-30 flex h-10 w-10 items-center justify-center rounded-full xl:h-9 xl:w-9",
          "border border-white/25 bg-black/25 shadow-lg backdrop-blur-md transition-all duration-200",
          "hover:scale-105 active:scale-95",
          isFavorite ? "text-rose-400" : "text-white/90 hover:text-rose-300"
        )}
        aria-label={isFavorite ? "Remove from favorites" : "Add to favorites"}
      >
        <Heart className={cn("h-3.5 w-3.5", isFavorite && "fill-current")} />
      </button>

      <div className="relative aspect-[4/3] overflow-hidden bg-gradient-to-br from-muted/40 via-background to-primary/5 xl:aspect-square">
        <ProductImage product={product} className="transition-transform duration-500 group-hover:scale-[1.03]" />
        <div className="absolute inset-0 bg-gradient-to-t from-black/45 via-transparent to-transparent" />

        <div className="absolute left-2 top-2 z-20">
          <Badge
            variant={status.variant}
            className="border-0 px-1.5 py-0.5 text-[8px] font-semibold uppercase tracking-[0.12em] shadow-md backdrop-blur-sm xl:px-2 xl:text-[9px]"
          >
            {status.label}
          </Badge>
        </div>

        <div className="absolute bottom-2 right-2 z-20">
          <span
            className={cn(
              "inline-flex items-center gap-1 rounded-lg px-1.5 py-0.5 text-[10px] font-semibold tabular-nums shadow-md backdrop-blur-md xl:px-2 xl:py-1",
              outOfStock ? "bg-destructive/90 text-white" : "bg-black/45 text-white"
            )}
          >
            <Package className="h-3 w-3" />
            {stock}
          </span>
        </div>
      </div>

      <div className="flex flex-1 flex-col px-2.5 pb-2.5 pt-2 xl:px-3 xl:pb-3 xl:pt-2.5">
        {product.category_name && (
          <p className="mb-0.5 truncate text-[9px] font-medium uppercase tracking-[0.14em] text-muted-foreground xl:text-[10px]">
            {product.category_name}
          </p>
        )}
        <p className="line-clamp-2 text-xs font-semibold leading-snug tracking-tight text-foreground xl:text-[13px]">
          {product.name}
        </p>
        {product.requires_prescription ? (
          <Badge variant="warning" className="mt-1 w-fit text-[9px] uppercase tracking-wide">
            Rx
          </Badge>
        ) : null}

        <div className="mt-auto flex items-center justify-between gap-1.5 pt-2">
          <span className="truncate text-sm font-bold tabular-nums tracking-tight text-primary xl:text-base">
            {formatCurrency(product.selling_price)}
          </span>
          <Button
            type="button"
            size="sm"
            className={cn(
              "h-10 min-w-10 shrink-0 gap-0.5 rounded-xl px-2.5 text-[11px] font-semibold shadow-sm active:scale-95 xl:h-9 xl:rounded-xl xl:px-2.5",
              outOfStock && "opacity-60"
            )}
            disabled={outOfStock}
            onClick={(e) => {
              e.stopPropagation();
              onAdd();
            }}
          >
            {outOfStock ? (
              <ShoppingBag className="h-3 w-3" />
            ) : (
              <Plus className="h-3 w-3 xl:h-3.5 xl:w-3.5" />
            )}
            <span className="hidden sm:inline">{outOfStock ? "Out" : "Add"}</span>
          </Button>
        </div>
      </div>
    </motion.article>
  );
}
