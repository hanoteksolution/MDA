import { Link } from "react-router-dom";
import { CloudConnectionForm } from "@/components/desktop/CloudConnectionForm";
import { syncApi } from "@/services/api/sync";

export function ConnectionPage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-background px-6 py-10">
      <div className="w-full max-w-2xl">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-foreground">Shop connection</h1>
          <p className="mt-2 text-sm text-muted-foreground">
            Link this PC to your shop on the live server, then sign in with the shop user created on the
            platform. Daily work still runs locally — internet is only needed for the first sign-in and
            to sync.
          </p>
        </div>
        <div className="rounded-2xl border border-border bg-card p-6 shadow-sm">
          <CloudConnectionForm
            showBackLink
            onSaved={(config) => {
              syncApi.saveConfig(config).catch(() => {});
            }}
          />
        </div>
        <p className="mt-6 text-center text-xs text-muted-foreground">
          Need a device with no cloud shop?{" "}
          <Link to="/setup?offline=1" className="text-primary hover:underline">
            Offline-only setup
          </Link>{" "}
          (local shop only — not managed from the cloud)
        </p>
      </div>
    </div>
  );
}
