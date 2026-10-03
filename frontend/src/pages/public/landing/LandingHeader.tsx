import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, Menu, X } from "lucide-react";
import { SafariLogo } from "@/components/brand/SafariLogo";
import { cn } from "@/utils/cn";
import { btnPrimary, btnSecondary, container, focusRing } from "./ui";

const NAV = [
  { label: "Solutions", href: "#solutions" },
  { label: "Modules", href: "#modules" },
  { label: "Pricing", href: "#pricing" },
  { label: "Industries", href: "#industries" },
  { label: "Resources", href: "#resources" },
];

export function LandingHeader() {
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  return (
    <header
      className={cn(
        "sticky top-0 z-50 border-b transition-colors",
        scrolled || open
          ? "border-brand-primary/10 bg-brand-surface/85 backdrop-blur-md"
          : "border-transparent bg-brand-surface"
      )}
    >
      <div className={cn(container, "flex h-[72px] items-center justify-between gap-6")}>
        <Link to="/" aria-label="Safari ERP home" className={cn("rounded-lg", focusRing)}>
          <SafariLogo size="sm" />
        </Link>

        <nav aria-label="Primary" className="hidden items-center gap-9 lg:flex">
          {NAV.map((item) => (
            <a
              key={item.href}
              href={item.href}
              className={cn("rounded-md text-sm font-medium text-brand-ink/80 transition hover:text-brand-primary", focusRing)}
            >
              {item.label}
            </a>
          ))}
        </nav>

        <div className="hidden items-center gap-3 lg:flex">
          <Link to="/login" className={btnSecondary}>Sign in</Link>
          <Link to="/register" className={btnPrimary}>
            Start free <ArrowRight className="h-4 w-4" aria-hidden />
          </Link>
        </div>

        <button
          type="button"
          className={cn("grid h-10 w-10 place-items-center rounded-xl border border-brand-primary/20 text-brand-ink lg:hidden", focusRing)}
          aria-label={open ? "Close menu" : "Open menu"}
          aria-expanded={open}
          aria-controls="landing-mobile-menu"
          onClick={() => setOpen((v) => !v)}
        >
          {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>
      </div>

      {open && (
        <div id="landing-mobile-menu" className="border-t border-brand-primary/10 lg:hidden">
          <nav aria-label="Mobile" className={cn(container, "flex flex-col gap-1 py-4")}>
            {NAV.map((item) => (
              <a
                key={item.href}
                href={item.href}
                onClick={() => setOpen(false)}
                className={cn("rounded-lg px-3 py-3 text-base font-medium text-brand-ink hover:bg-brand-soft", focusRing)}
              >
                {item.label}
              </a>
            ))}
            <div className="mt-3 grid grid-cols-2 gap-3">
              <Link to="/login" className={btnSecondary}>Sign in</Link>
              <Link to="/register" className={btnPrimary}>
                Start free <ArrowRight className="h-4 w-4" aria-hidden />
              </Link>
            </div>
          </nav>
        </div>
      )}
    </header>
  );
}
