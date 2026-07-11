import { useEffect, useRef, useState } from "react";
import { X, User, UtensilsCrossed, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/utils/cn";

export type PosQuickCreateMode = "customer" | "waiter";

interface PosCartQuickCreateDialogProps {
  mode: PosQuickCreateMode | null;
  onClose: () => void;
  onCreateCustomer?: (data: { full_name: string; phone?: string }) => Promise<void>;
  onCreateWaiter?: (name: string) => Promise<void>;
}

export function PosCartQuickCreateDialog({
  mode,
  onClose,
  onCreateCustomer,
  onCreateWaiter,
}: PosCartQuickCreateDialogProps) {
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const nameRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!mode) return;
    setName("");
    setPhone("");
    setError(null);
    const t = setTimeout(() => nameRef.current?.focus(), 50);
    return () => clearTimeout(t);
  }, [mode]);

  if (!mode) return null;

  const isCustomer = mode === "customer";
  const title = isCustomer ? "New customer" : "New waiter";
  const subtitle = isCustomer
    ? "Add a customer and attach them to this sale."
    : "Add a waiter for this order and future sales.";

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = name.trim();
    if (!trimmed) {
      setError("Name is required.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      if (isCustomer) {
        await onCreateCustomer?.({ full_name: trimmed, phone: phone.trim() || undefined });
      } else {
        await onCreateWaiter?.(trimmed);
      }
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save. Try again.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-[60] flex items-end justify-center bg-black/40 p-4 sm:items-center"
      onClick={onClose}
      role="presentation"
    >
      <div
        className={cn(
          "w-full max-w-sm overflow-hidden rounded-2xl border border-border/60 bg-card shadow-2xl",
          "animate-in fade-in slide-in-from-bottom-4 duration-200"
        )}
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="pos-quick-create-title"
      >
        <div className="relative border-b border-border/50 bg-gradient-to-br from-primary/[0.06] to-transparent px-5 py-4">
          <button
            type="button"
            onClick={onClose}
            className="absolute right-3 top-3 flex h-8 w-8 items-center justify-center rounded-lg text-muted-foreground hover:bg-muted/60"
            aria-label="Close"
          >
            <X className="h-4 w-4" />
          </button>
          <div className="flex items-center gap-3 pr-8">
            <div
              className={cn(
                "flex h-10 w-10 items-center justify-center rounded-xl",
                isCustomer ? "bg-primary/10 text-primary" : "bg-amber-500/10 text-amber-600"
              )}
            >
              {isCustomer ? <User className="h-5 w-5" /> : <UtensilsCrossed className="h-5 w-5" />}
            </div>
            <div>
              <h2 id="pos-quick-create-title" className="text-base font-semibold tracking-tight">
                {title}
              </h2>
              <p className="text-xs text-muted-foreground">{subtitle}</p>
            </div>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4 p-5">
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted-foreground">Name</label>
            <Input
              ref={nameRef}
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder={isCustomer ? "Customer full name" : "Waiter name"}
              className="h-11 rounded-xl"
              disabled={saving}
              required
            />
          </div>

          {isCustomer && (
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground">Phone (optional)</label>
              <Input
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                placeholder="061 234 5678"
                className="h-11 rounded-xl"
                disabled={saving}
              />
            </div>
          )}

          {error && (
            <p className="rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive">{error}</p>
          )}

          <div className="flex gap-2 pt-1">
            <Button type="button" variant="secondary" className="h-11 flex-1 rounded-xl" onClick={onClose} disabled={saving}>
              Cancel
            </Button>
            <Button type="submit" className="h-11 flex-1 rounded-xl font-semibold" disabled={saving}>
              {saving ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Saving…
                </>
              ) : (
                "Add & select"
              )}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
