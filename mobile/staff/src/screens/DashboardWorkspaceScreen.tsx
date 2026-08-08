import React, { useCallback, useEffect, useState } from "react";
import { Text } from "react-native";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";

import {
  fetchDashboardKpis,
  fetchDashboardWidgets,
  fetchLowStockDashboard,
  fetchRecentSales,
  money,
} from "@/api/erp";
import { Card, Screen } from "@/components/Screen";
import { ErrorText, Kpi, Row } from "@/components/ErpUi";
import type { RootStackParamList } from "@/navigation/types";
import { colors } from "@/theme/colors";

type Props = NativeStackScreenProps<RootStackParamList, "DashboardWorkspace">;

export function DashboardWorkspaceScreen({ navigation }: Props) {
  const [kpis, setKpis] = useState<Record<string, unknown> | null>(null);
  const [sales, setSales] = useState<Record<string, unknown>[]>([]);
  const [low, setLow] = useState<Record<string, unknown>[]>([]);
  const [widgets, setWidgets] = useState<Record<string, unknown>[]>([]);
  const [error, setError] = useState("");

  const reload = useCallback(async () => {
    setError("");
    try {
      const [k, s, l, w] = await Promise.all([
        fetchDashboardKpis("today"),
        fetchRecentSales(),
        fetchLowStockDashboard(),
        fetchDashboardWidgets(),
      ]);
      setKpis(k);
      setSales(s.results ?? []);
      setLow(l.results ?? []);
      setWidgets(w.results ?? []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load dashboard");
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  return (
    <Screen title="Dashboard" onRefresh={() => void reload()} onBack={() => navigation.navigate("WorkspaceSwitcher")}>
      <ErrorText message={error} />
      <Kpi label="Today sales" value={money(kpis?.total_sales ?? kpis?.revenue)} />
      <Kpi label="Cash collected" value={money(kpis?.cash_collected)} />
      <Kpi label="Profit" value={money(kpis?.profit)} />
      <Kpi label="Low / out of stock" value={`${kpis?.low_stock_count ?? "—"} / ${kpis?.out_of_stock_count ?? "—"}`} />

      {widgets.length ? (
        <Card>
          <Text style={{ color: colors.muted, marginBottom: 6 }}>Module widgets</Text>
          {widgets.slice(0, 8).map((w) => (
            <Text key={String(w.id)} style={{ color: colors.text, marginBottom: 4 }}>
              {String(w.title || w.module || w.id)}
            </Text>
          ))}
        </Card>
      ) : null}

      <Text style={{ color: colors.muted, marginTop: 8, fontWeight: "700" }}>Recent sales</Text>
      {sales.slice(0, 8).map((row, i) => (
        <Row
          key={String(row.id ?? i)}
          title={String(row.customer || row.id || "Sale")}
          subtitle={String(row.date || row.status || "")}
          meta={money(row.amount)}
        />
      ))}

      <Text style={{ color: colors.muted, marginTop: 8, fontWeight: "700" }}>Low stock</Text>
      {low.slice(0, 8).map((row, i) => (
        <Row
          key={String(row.id ?? i)}
          title={String(row.product || row.name || "Item")}
          subtitle={`${row.sku || ""} · ${row.warehouse || ""}`}
          meta={`${row.current ?? "—"} / ${row.minimum ?? "—"}`}
        />
      ))}
    </Screen>
  );
}
