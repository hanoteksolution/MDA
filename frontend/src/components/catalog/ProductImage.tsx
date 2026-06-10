import { useState } from "react";
import { Package } from "lucide-react";
import { resolveMediaUrl } from "@/config/api";
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

function picsumUrl(seed: string) {
  return `https://picsum.photos/seed/${encodeURIComponent(seed)}/400/400`;
}

interface ProductImageProps {
  product: Pick<Product, "name" | "image" | "category_name" | "sku">;
  className?: string;
  iconClassName?: string;
}

export function ProductImage({ product, className, iconClassName }: ProductImageProps) {
  const [stage, setStage] = useState<"primary" | "fallback" | "placeholder">(
    product.image ? "primary" : product.sku ? "fallback" : "placeholder"
  );

  const src =
    stage === "primary"
      ? resolveMediaUrl(product.image)
      : stage === "fallback" && product.sku
        ? picsumUrl(product.sku)
        : null;

  if (src) {
    return (
      <img
        src={src}
        alt={product.name}
        loading="lazy"
        onError={() => {
          if (stage === "primary" && product.sku) setStage("fallback");
          else setStage("placeholder");
        }}
        className={cn("h-full w-full object-cover", className)}
      />
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
}

export function ProductImagePreview({ image, name = "", sku, categoryName, className }: ProductImagePreviewProps) {
  return (
    <div className={cn("aspect-[4/3] overflow-hidden rounded-xl border border-border bg-muted/30", className)}>
      <ProductImage product={{ name, image: image || "", sku: sku || name, category_name: categoryName || name }} />
    </div>
  );
}
