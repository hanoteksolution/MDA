import { Link } from "react-router-dom";
import { useEffect, useState } from "react";
import { Cloud, AlertTriangle } from "lucide-react";
import { ensureConnectionLoaded, getCloudApiBase } from "@/config/connection";
import { hasCloudSession } from "@/services/api/cloudHttp";
import { PUBLIC_APP_URL } from "@/config/publicCloudUrl";
import { isTauri } from "@/utils/platform";

type CloudStatus = "loading" | "ok" | "no-url" | "no-session" | "local-fallback";

export function PlatformCloudNotice() {
  const [status, setStatus] = useState<CloudStatus>("loading");

  useEffect(() => {
    void ensureConnectionLoaded().then(() => {
      const base = getCloudApiBase();
      if (!base) {
        setStatus(isTauri() ? "local-fallback" : "no-url");
        return;
      }
      if (!hasCloudSession()) {
        setStatus("no-session");
        return;
      }
      setStatus("ok");
    });
  }, []);

  if (status === "loading" || status === "ok") return null;

  if (status === "local-fallback") {
    return (
      <div className="mb-4 flex gap-3 rounded-lg border border-amber-500/40 bg-amber-500/10 p-4 text-sm">
        <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />
        <div>
          <p className="font-medium">Cloud server not configured</p>
          <p className="mt-1 text-muted-foreground">
            Shops will be saved to <strong>this PC only</strong> until you set the cloud URL in{" "}
            <Link to="/settings" className="text-primary underline">
              Settings → Connection
            </Link>
            . For shops visible on phone and all devices, use{" "}
            <code className="text-xs">{PUBLIC_APP_URL}</code> and sign in to cloud.
          </p>
        </div>
      </div>
    );
  }

  if (status === "no-session") {
    return (
      <div className="mb-4 flex gap-3 rounded-lg border border-amber-500/40 bg-amber-500/10 p-4 text-sm">
        <Cloud className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />
        <div>
          <p className="font-medium">Cloud admin sign-in required</p>
          <p className="mt-1 text-muted-foreground">
            Open{" "}
            <Link to="/settings" className="text-primary underline">
              Settings → Connection
            </Link>{" "}
            and use <strong>Sign in to cloud</strong> with your platform account (e.g. maxbuub), then try again.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="mb-4 rounded-lg border border-destructive/40 bg-destructive/10 p-4 text-sm">
      Cloud server URL is not configured. Set it in Settings → Connection.
    </div>
  );
}
