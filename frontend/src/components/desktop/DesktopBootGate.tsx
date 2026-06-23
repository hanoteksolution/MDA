import { useEffect, useState } from "react";
import { Loader2, AlertTriangle } from "lucide-react";
import { LOCAL_API_BASE } from "@/config/connection";
import { isTauri } from "@/utils/platform";
import { Button } from "@/components/ui/button";

export function DesktopBootGate({ children }: { children: React.ReactNode }) {
  const [ready, setReady] = useState(!isTauri());
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isTauri()) return;

    let cancelled = false;
    let attempts = 0;
    const maxAttempts = 240;

    const poll = async () => {
      if (cancelled) return;
      attempts += 1;

      try {
        const { invoke } = await import("@tauri-apps/api/core");
        const status = await invoke<{ ready: boolean; error?: string | null }>("get_backend_status");
        if (cancelled) return;
        if (status.error) {
          setError(status.error);
          return;
        }
        if (status.ready) {
          setReady(true);
          return;
        }
      } catch {
        try {
          const res = await fetch(`${LOCAL_API_BASE}/health/`);
          if (res.ok) {
            setReady(true);
            return;
          }
        } catch {
          // still starting
        }
      }

      if (attempts >= maxAttempts) {
        setError("Local shop database did not start. Close apps using port 8000 and restart MDA ERP.");
        return;
      }
      window.setTimeout(poll, 500);
    };

    poll();
    return () => {
      cancelled = true;
    };
  }, []);

  if (!isTauri()) return <>{children}</>;

  if (error) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-background px-6 text-center">
        <AlertTriangle className="h-10 w-10 text-destructive" />
        <div className="max-w-md space-y-2">
          <h1 className="text-lg font-semibold">Could not start MDA ERP</h1>
          <p className="text-sm text-muted-foreground">{error}</p>
        </div>
        <Button variant="secondary" onClick={() => window.location.reload()}>
          Retry
        </Button>
      </div>
    );
  }

  if (!ready) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-3 bg-background">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <p className="text-sm text-muted-foreground">Starting local shop database…</p>
      </div>
    );
  }

  return <>{children}</>;
}
