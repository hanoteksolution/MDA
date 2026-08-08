import React, { useCallback, useEffect, useState } from "react";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";

import { fetchPurchaseOrders, fetchPurchaseSummary, money } from "@/api/erp";
import { Screen } from "@/components/Screen";
import { ErrorText, Kpi, Row } from "@/components/ErpUi";
import type { RootStackParamList } from "@/navigation/types";

type Props = NativeStackScreenProps<RootStackParamList, "PurchasesWorkspace">;

export function PurchasesWorkspaceScreen({ navigation }: Props) {
  const [summary, setSummary] = useState<Record<string, unknown> | null>(null);
  const [rows, setRows] = useState<Record<string, unknown>[]>([]);
  const [error, setError] = useState("");

  const reload = useCallback(async () => {
    setError("");
    try {
      const [s, list] = await Promise.all([fetchPurchaseSummary(), fetchPurchaseOrders()]);
      setSummary(s);
      setRows(list.results ?? []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load purchases");
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  return (
    <Screen title="Purchases" onRefresh={() => void reload()} onBack={() => navigation.navigate("WorkspaceSwitcher")}>
      <ErrorText message={error} />
      <Kpi label="Open orders" value={String(summary?.open_orders ?? "—")} />
      <Kpi label="Pending receipt" value={String(summary?.pending_receipt ?? "—")} />
      <Kpi label="Total orders" value={String(summary?.total_orders ?? "—")} />
      <Kpi label="Received (value)" value={money(summary?.month_total)} />
      {rows.map((po) => (
        <Row
          key={String(po.id)}
          title={String(po.order_number || "PO")}
          subtitle={`${po.supplier_name || ""} · ${po.status || ""}`}
          meta={money(po.total_amount)}
        />
      ))}
    </Screen>
  );
}
