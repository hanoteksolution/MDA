import { useEffect, useState } from "react";
import { branchOpsApi, type BranchReport, type BranchReportName, type Query } from "@/services/api/branchOps";

/** Load several branch reports for one scope. Errors surface per page, never as zeros. */
export function useBranchReports(names: BranchReportName[], params: Query, enabled = true) {
  const [reports, setReports] = useState<Partial<Record<BranchReportName, BranchReport>>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [reload, setReload] = useState(0);
  const key = JSON.stringify([names, params]);
  useEffect(() => {
    if (!enabled) return;
    let active = true;
    setLoading(true);
    setError("");
    Promise.all(names.map((n) => branchOpsApi.report(n, params).then((r) => [n, r.data] as const)))
      .then((pairs) => active && setReports(Object.fromEntries(pairs)))
      .catch((e: unknown) => {
        if (!active) return;
        setReports({});
        setError(e instanceof Error ? e.message : "Could not load branch reports.");
      })
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, reload, enabled]);
  return { reports, loading, error, retry: () => setReload((v) => v + 1) };
}
