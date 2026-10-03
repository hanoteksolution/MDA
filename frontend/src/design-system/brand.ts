/**
 * Safari Technology Solutions — platform brand used by the public auth and
 * onboarding experience. Colors live as CSS variables (`--brand-*` in
 * styles/globals.css, Tailwind `brand-*`); this file holds the non-color facts.
 */
import safariLogoUrl from "@/assets/brand/safari-logo.png";

export const SAFARI_BRAND = {
  company: "Safari Technology Solutions",
  product: "Safari ERP",
  logo: {
    src: safariLogoUrl,
    alt: "Safari Technology Solutions",
    /** Intrinsic size of the official asset; used to reserve layout space. */
    width: 567,
    height: 219,
  },
} as const;
