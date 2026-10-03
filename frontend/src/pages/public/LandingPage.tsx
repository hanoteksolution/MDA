import { Hero } from "./landing/Hero";
import { LandingHeader } from "./landing/LandingHeader";
import { Capabilities, Connected, FinalCta, IndustryStrip, LandingFooter, Modules, MultiBranch } from "./landing/Sections";

export function LandingPage() {
  return (
    <div className="min-h-dvh bg-brand-surface text-brand-ink">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[60] focus:rounded-lg focus:bg-brand-primary focus:px-4 focus:py-2 focus:text-brand-primary-foreground"
      >
        Skip to content
      </a>
      <LandingHeader />
      <main id="main">
        <Hero />
        <IndustryStrip />
        <Capabilities />
        <Connected />
        <MultiBranch />
        <Modules />
        <FinalCta />
      </main>
      <LandingFooter />
    </div>
  );
}
