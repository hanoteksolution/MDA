import React, { useCallback, useEffect, useState } from "react";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";

import { fetchInventoryList, fetchInventorySummary, fetchLowStock, money } from "@/api/erp";
import { Screen } from "@/components/Screen";
import { ErrorText, Kpi, Row } from "@/components/ErpUi";
import type { RootStackParamList } from "@/navigation/types";

type Props = NativeStackScreenProps<RootStackParamList, "InventoryWorkspace">;

export function InventoryWorkspaceScreen({ navigation }: Props) {
  const [summary, setSummary] = useState<Record<string, unknown> | null>(null);
  const [rows, setRows] = useState<Record<string, unknown>[]>([]);
  const [low, setLow] = useState<Record<string, unknown>[]>([]);
  const [error, setError] = useState("");

  const reload = useCallback(async () => {
    setError("");
    try {
      const [s, list, l] = await Promise.all([
        fetchInventorySummary(),
        fetchInventoryList(),
        fetchLowStock(),
      ]);
      setSummary(s);
      setRows(list.results ?? []);
      setLow(l.results ?? []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load inventory");
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  return (
    <Screen title="Inventory" onRefresh={() => void reload()} onBack={() => navigation.navigate("WorkspaceSwitcher")}>
      <ErrorText message={error} />
      <Kpi label="Items" value={String(summary?.total_items ?? "—")} />
      <Kpi label="On hand qty" value={String(summary?.total_quantity ?? "—")} />
      <Kpi label="Stock value" value={money(summary?.inventory_value)} />
      <Kpi label="Low / out" value={`${summary?.low_stock_count ?? "—"} / ${summary?.out_of_stock_count ?? "—"}`} />
      {low.slice(0, 8).map((row) => (
        <Row
          key={`low-${row.id}`}
          title={`LOW · ${row.product_name || row.product || ""}`}
          subtitle={`${row.product_sku || row.sku || ""} · ${row.warehouse_name || ""}`}
          meta={String(row.quantity ?? row.available_quantity ?? "")}
        />
      ))}
      {rows.map((row) => (
        <Row
          key={String(row.id)}
          title={String(row.product_name || "Item")}
          subtitle={`${row.product_sku || ""} · ${row.warehouse_name || ""}`}
          meta={String(row.available_quantity ?? row.quantity ?? "")}
        />
      ))}
    </Screen>
  );
}
