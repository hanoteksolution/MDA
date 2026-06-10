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
      initial={{ opacity: 0, y: 14, scale: 0.97 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.35, delay: Math.min(index * 0.025, 0.25), ease: [0.22, 1, 0.36, 1] }}
      whileHover={{ y: -6, transition: { duration: 0.22 } }}
      onClick={() => !outOfStock && onAdd()}
      className={cn(
        "group relative flex cursor-pointer flex-col overflow-hidden rounded-2xl border border-border/60 bg-card/90",
        "shadow-sm ring-1 ring-transparent transition-all duration-300",
        "hover:border-primary/40 hover:shadow-elevated hover:ring-primary/15",
        outOfStock && "cursor-not-allowed opacity-50 grayscale-[0.25]"
      )}
    >
      <div className="pointer-events-none absolute inset-x-0 top-0 z-10 h-px bg-gradient-to-r from-transparent via-primary/40 to-transparent" />

      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation();
          onToggleFavorite();
        }}
        className={cn(
          "absolute right-2 top-2 z-30 flex h-8 w-8 items-center justify-center rounded-full",
          "border border-white/20 bg-black/20 shadow-lg backdrop-blur-md transition-all duration-200",
          "hover:scale-110",
          isFavorite ? "text-rose-400" : "text-white/90 hover:text-rose-400"
        )}
        aria-label={isFavorite ? "Remove from favorites" : "Add to favorites"}
      >
        <Heart className={cn("h-4 w-4 drop-shadow", isFavorite && "fill-current")} />
      </button>

      <div className="relative aspect-square overflow-hidden bg-gradient-to-br from-muted/50 via-muted/20 to-primary/5">
        <ProductImage product={product} className="transition-transform duration-500 group-hover:scale-105" />
        <div className="absolute inset-0 bg-gradient-to-t from-black/50 via-black/5 to-transparent" />

        <div className="absolute left-2 top-2 z-20">
          <Badge
            variant={status.variant}
            className="border-0 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide shadow-lg backdrop-blur-sm"
          >
            {status.label}
          </Badge>
        </div>

        <div className="absolute bottom-2 right-2 z-20">
          <span
            className={cn(
              "inline-flex items-center gap-1 rounded-lg px-2 py-1 text-[11px] font-bold tabular-nums shadow-lg backdrop-blur-md",
              outOfStock ? "bg-destructive/90 text-white" : "bg-black/50 text-white"
            )}
          >
            <Package className="h-3 w-3" />
            {stock}
          </span>
        </div>

        {!outOfStock && (
          <div className="absolute inset-x-0 bottom-0 z-20 flex translate-y-full justify-center p-3 transition-transform duration-300 group-hover:translate-y-0">
            <Button
              type="button"
              size="sm"
              className="h-9 w-full gap-1.5 border-0 bg-white/95 text-xs font-bold text-primary shadow-xl hover:bg-white"
              onClick={(e) => {
                e.stopPropagation();
                onAdd();
              }}
            >
              <Plus className="h-4 w-4" />
              Add to cart
            </Button>
          </div>
        )}
      </div>

      <div className="flex flex-1 flex-col p-3.5">
        {product.category_name && (
          <p className="mb-1 text-[10px] font-semibold uppercase tracking-widest text-primary/80">
            {product.category_name}
          </p>
        )}
        <p className="line-clamp-2 min-h-[2.4rem] text-sm font-bold leading-snug text-foreground">
          {product.name}
        </p>
        <p className="mt-0.5 truncate font-mono text-[10px] text-muted-foreground">{product.sku}</p>

        <div className="mt-auto flex items-center justify-between gap-2 pt-3">
          <div>
            <span className="text-xl font-extrabold tabular-nums tracking-tight text-primary">
              {formatCurrency(product.selling_price)}
            </span>
          </div>
          <Button
            type="button"
            size="sm"
            className={cn(
              "h-9 gap-1 rounded-xl px-3 text-xs font-bold shadow-md",
              outOfStock && "opacity-60"
            )}
            disabled={outOfStock}
            onClick={(e) => {
              e.stopPropagation();
              onAdd();
            }}
          >
            {outOfStock ? (
              <ShoppingBag className="h-3.5 w-3.5" />
            ) : (
              <Plus className="h-3.5 w-3.5" />
            )}
            {outOfStock ? "Sold out" : "Add"}
          </Button>
        </div>
      </div>
    </motion.article>
  );
}
