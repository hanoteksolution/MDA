import { useAuthStore } from "@/store/authStore";

export function FooterStatusBar() {
  const branch = useAuthStore((s) => s.user?.branch);

  return (
    <footer className="flex h-8 shrink-0 items-center justify-between border-t border-border bg-card px-6 text-[11px] text-muted-foreground">
      <span>MDA Retail ERP v0.1.0 · Enterprise Edition</span>
      <div className="flex items-center gap-4">
        <span className="flex items-center gap-1.5">
          <span className="h-1.5 w-1.5 rounded-full bg-success animate-pulse" />
          System Online
        </span>
        {branch && <span>{branch.name} ({branch.code})</span>}
      </div>
    </footer>
  );
}
