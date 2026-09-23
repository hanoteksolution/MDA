import { useCallback, useEffect, useMemo, useState } from "react";
import { posApi, type CashierSession } from "@/services/api/pos";
import { organizationApi } from "@/services/api/organization";
import { getCheckoutBlockReason } from "../utils/checkoutGuard";

interface TerminalRow {
  id: string;
  branch_id: string;
  code: string;
  name: string;
  status: string;
}

/** The cashier's shift + the branch's terminals, and the resulting checkout guard (FE-5). */
export function usePosShift(branchId: string | null | undefined) {
  const [session, setSession] = useState<CashierSession | null>(null);
  const [terminals, setTerminals] = useState<TerminalRow[]>([]);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!branchId || branchId === "all") {
      setSession(null);
      setTerminals([]);
      return;
    }
    try {
      const [current, terminalRes] = await Promise.all([
        posApi.currentSession({ branch_id: branchId }),
        organizationApi.posTerminals(),
      ]);
      setSession(current.data ?? null);
      setTerminals(
        (terminalRes.data as TerminalRow[]).filter(
          (t) => t.branch_id === branchId && t.status === "ACTIVE"
        )
      );
    } catch {
      // Unknown state must not silently allow selling: keep the previous guard inputs.
    }
  }, [branchId]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const terminalRequired = terminals.length > 0;
  const blockReason = useMemo(
    () => getCheckoutBlockReason({ branchId, terminalRequired, session }),
    [branchId, terminalRequired, session]
  );

  const openShift = useCallback(
    async (openingFloat: number, terminalId?: string) => {
      setError(null);
      try {
        await posApi.openSession({
          branch_id: branchId ?? undefined,
          terminal_id: terminalId,
          opening_float: openingFloat,
        });
        await refresh();
        return true;
      } catch (e) {
        setError(e instanceof Error ? e.message : "Could not open the shift.");
        return false;
      }
    },
    [branchId, refresh]
  );

  return { session, terminals, terminalRequired, blockReason, openShift, error, refresh };
}
