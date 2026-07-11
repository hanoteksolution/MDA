import { useEffect, useState } from "react";
import { ImageIcon, Package } from "lucide-react";
import { resolveProductImageUrl } from "@/config/api";
import { cn } from "@/utils/cn";
import type { Product } from "@/types/models/catalog";

const GRADIENTS = [
  "from-emerald-500/20 to-teal-600/30",
  "from-blue-500/20 to-indigo-600/30",
  "from-violet-500/20 to-purple-600/30",
  "from-amber-500/20 to-orange-600/30",
  "from-rose-500/20 to-pink-600/30",
  "from-cyan-500/20 to-sky-600/30",
];

export function productGradient(name: string) {
  let hash = 0;
  for (let i = 0; i < name.length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash);
  return GRADIENTS[Math.abs(hash) % GRADIENTS.length];
}

export function getStockStatus(stock: number, minimum: number) {
  if (stock <= 0) return { label: "Out of Stock", variant: "destructive" as const };
  if (stock <= minimum) return { label: "Low Stock", variant: "warning" as const };
  return { label: "In Stock", variant: "success" as const };
}

interface ProductImageProps {
  product: Pick<Product, "name" | "image" | "category_name" | "sku">;
  className?: string;
  iconClassName?: string;
  /** When true, empty state is a quiet “no photo” instead of category gradient. */
  emptyQuiet?: boolean;
}

export function ProductImage({ product, className, iconClassName, emptyQuiet }: ProductImageProps) {
  const resolved = resolveProductImageUrl(product.image);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    setFailed(false);
  }, [resolved]);

  if (resolved && !failed) {
    return (
      <img
        key={resolved}
        src={resolved}
        alt={product.name}
        loading="lazy"
        onError={() => setFailed(true)}
        className={cn("h-full w-full object-cover", className)}
      />
    );
  }

  if (emptyQuiet) {
    return (
      <div
        className={cn(
          "flex h-full w-full flex-col items-center justify-center gap-2 bg-muted/40 text-muted-foreground",
          className
        )}
      >
        <ImageIcon className={cn("h-8 w-8 opacity-50", iconClassName)} strokeWidth={1.25} />
        <span className="text-[11px] font-medium opacity-70">No photo</span>
      </div>
    );
  }

  return (
    <div
      className={cn(
        "flex h-full w-full items-center justify-center bg-gradient-to-br",
        productGradient(product.category_name || product.name),
        className
      )}
    >
      <Package className={cn("h-8 w-8 text-primary/70", iconClassName)} strokeWidth={1.5} />
    </div>
  );
}

interface ProductThumbnailProps {
  product: Pick<Product, "name" | "image" | "category_name" | "sku">;
  size?: "sm" | "md" | "lg";
  className?: string;
}

const THUMB_SIZE = {
  sm: "h-9 w-9 rounded-lg",
  md: "h-11 w-11 rounded-lg",
  lg: "h-16 w-16 rounded-xl",
};

export function ProductThumbnail({ product, size = "md", className }: ProductThumbnailProps) {
  return (
    <div
      className={cn(
        "shrink-0 overflow-hidden border border-border bg-muted/30",
        THUMB_SIZE[size],
        className
      )}
    >
      <ProductImage product={product} iconClassName={size === "sm" ? "h-4 w-4" : "h-5 w-5"} />
    </div>
  );
}

interface ProductImagePreviewProps {
  image?: string;
  name?: string;
  sku?: string;
  categoryName?: string;
  className?: string;
  emptyQuiet?: boolean;
}

export function ProductImagePreview({
  image,
  name = "",
  sku,
  categoryName,
  className,
  emptyQuiet = true,
}: ProductImagePreviewProps) {
  return (
    <div
      className={cn(
        "aspect-[4/3] overflow-hidden rounded-2xl border border-border/50 bg-muted/20 shadow-[inset_0_1px_0_hsl(var(--background))]",
        className
      )}
    >
      <ProductImage
        product={{ name, image: image || "", sku: sku || name, category_name: categoryName || name }}
        emptyQuiet={emptyQuiet}
      />
    </div>
  );
}
