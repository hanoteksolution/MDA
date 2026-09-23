import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { inventoryApi } from "@/services/api/catalog";
import type { ProductAvailability } from "@/types/models/catalog";

/**
 * Branch Phase 3: read-only cross-branch stock visibility (BRANCH_INVENTORY.md §7).
 * Fetches on demand — this is a look-up, not something worth pre-loading for every
 * row in a paginated list. Never a mutation: clicking this never reserves, transfers,
 * or otherwise touches another branch's stock (that is Phase 4's workflow).
 */
export function CrossBranchAvailability({ productId }: { productId: string }) {
  const [data, setData] = useState<ProductAvailability | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState(false);

  async function load() {
    if (data || loading) {
      setOpen((v) => !v);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const response = await inventoryApi.productAvailability(productId);
      setData(response.data);
      setOpen(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not check other branches.");
      setOpen(true);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="inline-flex flex-col items-start gap-1">
      <Button size="sm" variant="ghost" onClick={load} disabled={loading}>
        {loading ? "Checking…" : "Check other branches"}
      </Button>
      {open && error && <span className="text-xs text-destructive">{error}</span>}
      {open && data && (
        <div className="flex flex-wrap gap-1">
          {data.other_branches.length === 0 ? (
            <span className="text-xs text-muted-foreground">
              No visibility into other branches for your role.
            </span>
          ) : (
            data.other_branches.map((branch) => (
              <Badge key={branch.branch_id} variant={branch.available > 0 ? "success" : "secondary"}>
                {branch.branch_name}: {branch.available}
              </Badge>
            ))
          )}
        </div>
      )}
    </div>
  );
}
