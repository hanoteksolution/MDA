import { useEffect, useState } from "react";
import { Upload } from "lucide-react";
import { CloudConnectionForm } from "@/components/desktop/CloudConnectionForm";
import { FormField, FormSection } from "@/components/forms/FormField";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { cloudLogin, clearCloudSession, hasCloudSession } from "@/services/api/cloudHttp";
import { syncApi } from "@/services/api/sync";
import { requestCloudSync } from "@/components/desktop/syncEvents";
import { isTauri } from "@/utils/platform";

export function ConnectionSettings() {
  const [syncing, setSyncing] = useState(false);
  const [syncStatus, setSyncStatus] = useState("");
  const [cloudUser, setCloudUser] = useState("");
  const [cloudPass, setCloudPass] = useState("");
  const [cloudLoggedIn, setCloudLoggedIn] = useState(hasCloudSession());

  useEffect(() => {
    syncApi
      .config()
      .then((syncRes) => {
        const fromDb = syncRes?.data;
        if (fromDb?.last_message) {
          setSyncStatus(
            `${fromDb.last_status || "unknown"} — ${fromDb.last_message} (${fromDb.last_sync_at || "never"})`
          );
        }
      })
      .catch(() => {});
  }, []);

  const runSync = async () => {
    setSyncing(true);
    try {
      const res = await syncApi.run();
      const msg = res.data.message || res.message;
      setSyncStatus(`success — ${msg}`);
    } catch (err) {
      setSyncStatus(err instanceof Error ? err.message : "Sync failed");
    } finally {
      setSyncing(false);
    }
  };

  const signInCloud = async () => {
    try {
      await cloudLogin(cloudUser, cloudPass);
      setCloudLoggedIn(true);
      setCloudPass("");
    } catch (err) {
      alert(err instanceof Error ? err.message : "Cloud login failed");
    }
  };

  if (!isTauri()) {
    return (
      <FormSection title="Connection" description="Use the desktop app for offline + cloud sync.">
        <p className="text-sm text-muted-foreground">Install MDA ERP desktop for shop offline mode.</p>
      </FormSection>
    );
  }

  return (
    <div>
      <CloudConnectionForm
        onSaved={(config) => {
          syncApi.saveConfig(config).catch(() => {});
          requestCloudSync();
        }}
      />

      <div className="mt-6">
        <FormSection
          title="Sync status"
          description="Automatic sync runs when online. Use this button for a manual upload."
        >
          {syncStatus && <p className="mb-3 text-sm text-muted-foreground">Last sync: {syncStatus}</p>}
          <Button type="button" variant="secondary" loading={syncing} onClick={runSync}>
            <Upload className="h-4 w-4" />
            Sync now (optional)
          </Button>
        </FormSection>
      </div>

      <div className="mt-6">
        <FormSection
          title="Cloud admin login (platform owner)"
          description="Sign in to manage all shops, subscriptions, and alerts on the cloud. Only needed for Platform menu."
        >
          {cloudLoggedIn ? (
            <div className="flex items-center gap-3">
              <Badge variant="success">Cloud admin connected</Badge>
              <Button
                type="button"
                variant="secondary"
                size="sm"
                onClick={() => {
                  clearCloudSession();
                  setCloudLoggedIn(false);
                }}
              >
                Sign out cloud
              </Button>
            </div>
          ) : (
            <div className="grid gap-4 md:grid-cols-2">
              <FormField label="Cloud username">
                <Input value={cloudUser} onChange={(e) => setCloudUser(e.target.value)} />
              </FormField>
              <FormField label="Cloud password">
                <Input
                  type="password"
                  value={cloudPass}
                  onChange={(e) => setCloudPass(e.target.value)}
                />
              </FormField>
              <div className="md:col-span-2">
                <Button type="button" onClick={signInCloud}>
                  Sign in to cloud
                </Button>
              </div>
            </div>
          )}
        </FormSection>
      </div>
    </div>
  );
}
