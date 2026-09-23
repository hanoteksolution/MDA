import { useEffect, useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { cn, formatCurrency } from "@/utils/cn";
import type { Product } from "@/types/models/catalog";
import { restaurantApi, type MenuCustomizePayload } from "@/services/api/restaurant";

interface PosMenuCustomizeDialogProps {
  product: Product;
  onClose: () => void;
  onConfirm: (payload: {
    name: string;
    price: number;
    variant_id?: string;
    modifier_ids: string[];
    menu_item_id: string;
  }) => void;
}

export function PosMenuCustomizeDialog({
  product,
  onClose,
  onConfirm,
}: PosMenuCustomizeDialogProps) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<MenuCustomizePayload | null>(null);
  const [variantId, setVariantId] = useState<string>("");
  const [selectedMods, setSelectedMods] = useState<Record<string, boolean>>({});

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    restaurantApi
      .itemCustomizeByProduct(product.id)
      .then((res) => {
        if (cancelled) return;
        const payload = res.data;
        setData(payload);
        const defaultVariant =
          payload.variants?.find((v) => v.is_default)?.id || payload.variants?.[0]?.id || "";
        setVariantId(defaultVariant);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "Failed to load options");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [product.id]);

  const basePrice = Number(data?.menu_item?.unit_price ?? product.selling_price ?? 0);
  const variantAdj = useMemo(() => {
    const v = data?.variants?.find((x) => x.id === variantId);
    return Number(v?.price_adjustment || 0);
  }, [data, variantId]);
  const modAdj = useMemo(() => {
    let sum = 0;
    for (const g of data?.modifier_groups || []) {
      for (const m of g.modifiers || []) {
        if (selectedMods[m.id]) sum += Number(m.price_delta || 0);
      }
    }
    return sum;
  }, [data, selectedMods]);
  const total = Math.round((basePrice + variantAdj + modAdj) * 100) / 100;

  const toggleMod = (id: string, groupId: string, maxSelect: number) => {
    setSelectedMods((prev) => {
      const next = { ...prev };
      if (next[id]) {
        delete next[id];
        return next;
      }
      if (maxSelect === 1) {
        const group = data?.modifier_groups?.find((g) => g.id === groupId);
        for (const m of group?.modifiers || []) delete next[m.id];
      } else if (maxSelect > 1) {
        const group = data?.modifier_groups?.find((g) => g.id === groupId);
        const count = (group?.modifiers || []).filter((m) => next[m.id]).length;
        if (count >= maxSelect) return prev;
      }
      next[id] = true;
      return next;
    });
  };

  const handleConfirm = () => {
    if (!data?.menu_item?.id) {
      onConfirm({
        name: product.name,
        price: Number(product.selling_price || 0),
        modifier_ids: [],
        menu_item_id: "",
      });
      return;
    }
    const variant = data.variants?.find((v) => v.id === variantId);
    const modNames: string[] = [];
    const modifier_ids: string[] = [];
    for (const g of data.modifier_groups || []) {
      for (const m of g.modifiers || []) {
        if (selectedMods[m.id]) {
          modifier_ids.push(m.id);
          modNames.push(m.name);
        }
      }
    }
    const nameParts = [product.name];
    if (variant?.name) nameParts.push(`(${variant.name})`);
    if (modNames.length) nameParts.push(`+ ${modNames.join(", ")}`);
    onConfirm({
      name: nameParts.join(" "),
      price: total,
      variant_id: variantId || undefined,
      modifier_ids,
      menu_item_id: data.menu_item.id,
    });
  };

  const hasOptions =
    (data?.variants?.length || 0) > 0 || (data?.modifier_groups?.length || 0) > 0;

  return (
    <div className="fixed inset-0 z-[60] flex items-end justify-center bg-black/45 p-4 sm:items-center">
      <div className="w-full max-w-md rounded-2xl border border-border bg-card p-5 shadow-xl">
        <div className="mb-4 flex items-start justify-between gap-3">
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
              Customize
            </p>
            <h3 className="mt-1 text-lg font-semibold text-foreground">{product.name}</h3>
            <p className="mt-1 text-sm text-muted-foreground">{formatCurrency(total)}</p>
          </div>
          <Button type="button" variant="ghost" size="sm" onClick={onClose}>
            Close
          </Button>
        </div>

        {loading ? (
          <p className="text-sm text-muted-foreground">Loading options…</p>
        ) : error ? (
          <p className="text-sm text-destructive">{error}</p>
        ) : !hasOptions ? (
          <p className="text-sm text-muted-foreground">No variants or modifiers for this item.</p>
        ) : (
          <div className="max-h-[50vh] space-y-4 overflow-y-auto pr-1">
            {(data?.variants?.length || 0) > 0 && (
              <div>
                <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Size / Variant
                </p>
                <div className="flex flex-wrap gap-2">
                  {(data?.variants || []).map((v) => (
                    <button
                      key={v.id}
                      type="button"
                      onClick={() => setVariantId(v.id)}
                      className={cn(
                        "rounded-xl border px-3 py-2 text-sm transition",
                        variantId === v.id
                          ? "border-primary bg-primary/10 text-foreground"
                          : "border-border bg-background text-muted-foreground"
                      )}
                    >
                      {v.name}
                      {Number(v.price_adjustment) ? (
                        <span className="ml-1 text-xs">
                          {Number(v.price_adjustment) > 0 ? "+" : ""}
                          {formatCurrency(Number(v.price_adjustment))}
                        </span>
                      ) : null}
                    </button>
                  ))}
                </div>
              </div>
            )}
            {(data?.modifier_groups || []).map((g) => (
              <div key={g.id}>
                <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  {g.name}
                  {g.min_select ? ` · pick ≥${g.min_select}` : ""}
                </p>
                <div className="flex flex-wrap gap-2">
                  {(g.modifiers || []).map((m) => (
                    <button
                      key={m.id}
                      type="button"
                      onClick={() => toggleMod(m.id, g.id, Number(g.max_select || 0))}
                      className={cn(
                        "rounded-xl border px-3 py-2 text-sm transition",
                        selectedMods[m.id]
                          ? "border-primary bg-primary/10 text-foreground"
                          : "border-border bg-background text-muted-foreground"
                      )}
                    >
                      {m.name}
                      {Number(m.price_delta) ? (
                        <span className="ml-1 text-xs">
                          {Number(m.price_delta) > 0 ? "+" : ""}
                          {formatCurrency(Number(m.price_delta))}
                        </span>
                      ) : null}
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}

        <div className="mt-5 flex gap-2">
          <Button type="button" variant="secondary" className="flex-1" onClick={onClose}>
            Cancel
          </Button>
          <Button type="button" className="flex-1" onClick={handleConfirm} disabled={loading}>
            Add · {formatCurrency(total)}
          </Button>
        </div>
      </div>
    </div>
  );
}
