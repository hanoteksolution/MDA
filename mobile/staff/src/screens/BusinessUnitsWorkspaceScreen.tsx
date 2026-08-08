import React, { useCallback, useEffect, useState } from "react";
import { Text } from "react-native";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";

import { fetchBusinessUnits, fetchProfitLoss, money } from "@/api/erp";
import { Screen } from "@/components/Screen";
import { ErrorText, Kpi, Row } from "@/components/ErpUi";
import type { RootStackParamList } from "@/navigation/types";
import { colors } from "@/theme/colors";

type Props = NativeStackScreenProps<RootStackParamList, "BusinessUnitsWorkspace">;

export function BusinessUnitsWorkspaceScreen({ navigation }: Props) {
  const [units, setUnits] = useState<Record<string, unknown>[]>([]);
  const [selected, setSelected] = useState<Record<string, unknown> | null>(null);
  const [pnl, setPnl] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState("");

  const reload = useCallback(async () => {
    setError("");
    try {
      const list = await fetchBusinessUnits();
      const rows = list.results ?? [];
      setUnits(rows);
      setSelected((prev) => prev ?? rows[0] ?? null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load business units");
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  useEffect(() => {
    if (!selected?.id) {
      setPnl(null);
      return;
    }
    fetchProfitLoss(String(selected.id))
      .then(setPnl)
      .catch((err) => setError(err instanceof Error ? err.message : "P&L failed"));
  }, [selected?.id]);

  const totals = (pnl?.totals as Record<string, unknown> | undefined) ?? {};

  return (
    <Screen
      title="Business Units"
      onRefresh={() => void reload()}
      onBack={() => navigation.navigate("WorkspaceSwitcher")}
    >
      <ErrorText message={error} />
      <Text style={{ color: colors.muted }}>
        P&amp;L by business unit (same GL dimension as web finance).
      </Text>
      {units.map((bu) => (
        <Row
          key={String(bu.id)}
          title={`${bu.code} · ${bu.name}`}
          subtitle={String(bu.module_code || "shared")}
          meta={selected?.id === bu.id ? "selected" : ""}
          onPress={() => setSelected(bu)}
        />
      ))}
      {selected ? (
        <>
          <Kpi label={`${selected.code} revenue`} value={money(totals.revenue)} />
          <Kpi label={`${selected.code} expenses`} value={money(totals.expenses)} />
          <Kpi label={`${selected.code} net profit`} value={money(totals.net_profit)} />
        </>
      ) : null}
    </Screen>
  );
}
