import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, Cloud, HardDrive, RefreshCw } from "lucide-react";
import { FormField, FormGrid, FormSection } from "@/components/forms/FormField";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  LOCAL_API_BASE,
  type HybridConnectionConfig,
  loadDesktopConnection,
  persistDesktopConnection,
} from "@/config/connection";
import { DEFAULT_CLOUD_API_BASE } from "@/config/publicCloudUrl";
import { isTauri } from "@/utils/platform";

const EMPTY: HybridConnectionConfig = {
  cloud_api_base: "",
  tenant_slug: "",
  sync_secret: "",
};

interface CloudConnectionFormProps {
  onSaved?: (config: HybridConnectionConfig) => void;
  showBackLink?: boolean;
}

export function CloudConnectionForm({ onSaved, showBackLink = false }: CloudConnectionFormProps) {
  const [form, setForm] = useState<HybridConnectionConfig>(EMPTY);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    loadDesktopConnection()
      .then((cfg) => {
        if (cfg?.cloud_api_base) {
          setForm(cfg);
        } else {
          setForm({ ...EMPTY, cloud_api_base: DEFAULT_CLOUD_API_BASE });
        }
      })
      .finally(() => setLoading(false));
  }, []);

  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setSaved(false);
    try {
      const normalized = {
        cloud_api_base: form.cloud_api_base.trim().replace(/\/$/, ""),
        tenant_slug: form.tenant_slug.trim(),
        sync_secret: form.sync_secret.trim(),
      };
      await persistDesktopConnection(normalized);
      setForm(normalized);
      setSaved(true);
      onSaved?.(normalized);
    } catch (err) {
      alert(err instanceof Error ? err.message : "Could not save settings.");
    } finally {
      setSaving(false);
    }
  };

  if (!isTauri()) {
    return (
      <p className="text-sm text-muted-foreground">
        Install the MDA ERP desktop app to configure shop cloud sync.
      </p>
    );
  }

  return (
    <form onSubmit={save}>
      <Badge className="mb-4">
        <HardDrive className="mr-1 h-3 w-3" />
        Local shop API: {LOCAL_API_BASE}
      </Badge>

      <FormSection
        title="Cloud connection"
        description="Required before the shop manager's first sign-in. Get slug and sync secret from Platform → All Shops → Edit shop."
      >
        <div className="mb-4 flex flex-wrap gap-2">
          <Badge variant="outline">
            <Cloud className="mr-1 h-3 w-3" />
            Live server sync
          </Badge>
        </div>
        <FormGrid>
          <FormField label="Cloud server URL" hint={`Example: ${DEFAULT_CLOUD_API_BASE}`}>
            <Input
              value={form.cloud_api_base}
              disabled={loading}
              onChange={(e) => setForm({ ...form, cloud_api_base: e.target.value })}
              placeholder={DEFAULT_CLOUD_API_BASE}
            />
          </FormField>
          <FormField label="Shop slug" hint="From Platform → All Shops">
            <Input
              value={form.tenant_slug}
              disabled={loading}
              onChange={(e) => setForm({ ...form, tenant_slug: e.target.value })}
            />
          </FormField>
          <FormField label="Sync secret" hint="Copy from Edit Shop on the platform" className="md:col-span-2">
            <Input
              value={form.sync_secret}
              disabled={loading}
              onChange={(e) => setForm({ ...form, sync_secret: e.target.value })}
              type="password"
            />
          </FormField>
        </FormGrid>
      </FormSection>

      <div className="mt-6 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          {showBackLink && (
            <Button type="button" variant="secondary" asChild>
              <Link to="/login">
                <ArrowLeft className="h-4 w-4" />
                Back to login
              </Link>
            </Button>
          )}
          {saved && <span className="text-sm text-emerald-600">Saved. You can sign in now.</span>}
        </div>
        <Button type="submit" loading={saving} disabled={loading}>
          <RefreshCw className="h-4 w-4" />
          Save connection
        </Button>
      </div>
    </form>
  );
}
