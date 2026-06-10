import { useEffect, useState } from "react";
import { Plus, Trash2, Save, Star } from "lucide-react";
import { FormField, FormSection, FormGrid } from "@/components/forms/FormField";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { posApi, type PosMerchant, type PosProfile } from "@/services/api/pos";

const emptyMerchant = (): PosMerchant => ({
  id: crypto.randomUUID(),
  label: "",
  company_name: "",
  merchant_number: "",
  provider: "mobile",
  is_default: false,
});

export function PosProfileSettings() {
  const [profile, setProfile] = useState<PosProfile>({
    merchants: [],
    default_payment_method: "cash",
    receipt_footer: "Thank you for your purchase!",
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    posApi
      .profile()
      .then((res) => setProfile(res.data))
      .finally(() => setLoading(false));
  }, []);

  const addMerchant = () => {
    setProfile((p) => ({
      ...p,
      merchants: [...p.merchants, { ...emptyMerchant(), is_default: p.merchants.length === 0 }],
    }));
  };

  const updateMerchant = (id: string, patch: Partial<PosMerchant>) => {
    setProfile((p) => ({
      ...p,
      merchants: p.merchants.map((m) => (m.id === id ? { ...m, ...patch } : m)),
    }));
  };

  const removeMerchant = (id: string) => {
    setProfile((p) => {
      const next = p.merchants.filter((m) => m.id !== id);
      if (next.length && !next.some((m) => m.is_default)) next[0].is_default = true;
      return { ...p, merchants: next };
    });
  };

  const setDefault = (id: string) => {
    setProfile((p) => ({
      ...p,
      merchants: p.merchants.map((m) => ({ ...m, is_default: m.id === id })),
    }));
  };

  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      const res = await posApi.saveProfile(profile);
      setProfile(res.data);
    } catch (err) {
      alert(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return <div className="h-48 animate-pulse rounded-2xl bg-muted" />;
  }

  return (
    <form onSubmit={save}>
      <FormSection
        title="POS Profile"
        description="Add merchant numbers and company names shown on checkout and printed receipts."
      >
        <FormGrid>
          <FormField label="Default Payment Method">
            <Select
              value={profile.default_payment_method}
              onValueChange={(v) =>
                setProfile({ ...profile, default_payment_method: v as PosProfile["default_payment_method"] })
              }
            >
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="cash">Cash</SelectItem>
                <SelectItem value="card">Card</SelectItem>
                <SelectItem value="mobile">Mobile Money</SelectItem>
                <SelectItem value="bank">Bank Transfer</SelectItem>
                <SelectItem value="split">Split</SelectItem>
              </SelectContent>
            </Select>
          </FormField>
          <FormField label="Receipt Footer" className="md:col-span-2">
            <Input
              value={profile.receipt_footer}
              onChange={(e) => setProfile({ ...profile, receipt_footer: e.target.value })}
              placeholder="Thank you for your purchase!"
            />
          </FormField>
        </FormGrid>

        <div className="mt-8 flex items-center justify-between">
          <div>
            <p className="text-sm font-semibold">Merchant Accounts</p>
            <p className="text-xs text-muted-foreground">Company names and merchant numbers for card/mobile payments</p>
          </div>
          <Button type="button" variant="secondary" size="sm" onClick={addMerchant}>
            <Plus className="h-4 w-4" /> Add Merchant
          </Button>
        </div>

        <div className="mt-4 space-y-4">
          {profile.merchants.length === 0 ? (
            <p className="text-sm text-muted-foreground rounded-xl border border-dashed border-border p-6 text-center">
              No merchant accounts yet. Add your EVC Plus, bank, or card merchant numbers.
            </p>
          ) : (
            profile.merchants.map((m) => (
              <div key={m.id} className="rounded-xl border border-border bg-card p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    {m.is_default && <Badge variant="secondary">Default</Badge>}
                    <span className="text-sm font-medium">{m.label || "New Merchant"}</span>
                  </div>
                  <div className="flex gap-1">
                    {!m.is_default && (
                      <Button type="button" variant="ghost" size="sm" onClick={() => setDefault(m.id)} title="Set as default">
                        <Star className="h-4 w-4" />
                      </Button>
                    )}
                    <Button type="button" variant="ghost" size="sm" className="text-destructive" onClick={() => removeMerchant(m.id)}>
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
                <FormGrid>
                  <FormField label="Label" hint="e.g. Main EVC Plus">
                    <Input value={m.label} onChange={(e) => updateMerchant(m.id, { label: e.target.value })} />
                  </FormField>
                  <FormField label="Company Name">
                    <Input value={m.company_name} onChange={(e) => updateMerchant(m.id, { company_name: e.target.value })} />
                  </FormField>
                  <FormField label="Merchant Number">
                    <Input
                      value={m.merchant_number}
                      onChange={(e) => updateMerchant(m.id, { merchant_number: e.target.value })}
                      className="font-mono"
                    />
                  </FormField>
                  <FormField label="Provider">
                    <Select value={m.provider} onValueChange={(v) => updateMerchant(m.id, { provider: v as PosMerchant["provider"] })}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="mobile">Mobile Money</SelectItem>
                        <SelectItem value="card">Card</SelectItem>
                        <SelectItem value="bank">Bank</SelectItem>
                        <SelectItem value="cash">Cash</SelectItem>
                      </SelectContent>
                    </Select>
                  </FormField>
                </FormGrid>
              </div>
            ))
          )}
        </div>

        <div className="mt-6 flex justify-end">
          <Button type="submit" loading={saving}>
            <Save className="h-4 w-4" />
            Save POS Profile
          </Button>
        </div>
      </FormSection>
    </form>
  );
}
