import { SAFARI_BRAND } from "@/design-system/brand";
import { cn } from "@/utils/cn";

const SIZES = {
  sm: "h-9",
  md: "h-12",
  lg: "h-16",
} as const;

/**
 * The official Safari Technology Solutions logo, never stretched: height is set
 * and width follows the intrinsic aspect ratio. The artwork has black lettering
 * on transparency, so dark surfaces get a white plate instead of an altered logo.
 */
export function SafariLogo({
  size = "md",
  className,
  decorative = false,
}: {
  size?: keyof typeof SIZES;
  className?: string;
  /** Set when an adjacent heading already names Safari. */
  decorative?: boolean;
}) {
  const { logo } = SAFARI_BRAND;
  return (
    <span
      className={cn(
        "inline-flex shrink-0 items-center dark:rounded-xl dark:bg-white dark:px-3 dark:py-1.5",
        className
      )}
    >
      <img
        src={logo.src}
        alt={decorative ? "" : logo.alt}
        width={logo.width}
        height={logo.height}
        className={cn(SIZES[size], "w-auto max-w-full object-contain")}
        draggable={false}
      />
    </span>
  );
}
