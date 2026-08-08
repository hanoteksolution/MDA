import React, { useCallback, useEffect, useState } from "react";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";

import { fetchAccountingEquation, fetchFinanceSummary, money } from "@/api/erp";
import { Screen } from "@/components/Screen";
import { ErrorText, Kpi, Row } from "@/components/ErpUi";
import type { RootStackParamList } from "@/navigation/types";

type Props = NativeStackScreenProps<RootStackParamList, "FinanceWorkspace">;

export function FinanceWorkspaceScreen({ navigation }: Props) {
  const [summary, setSummary] = useState<Record<string, unknown> | null>(null);
  const [equation, setEquation] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState("");

  const reload = useCallback(async () => {
    setError("");
    try {
      const [s, eq] = await Promise.all([fetchFinanceSummary("month"), fetchAccountingEquation()]);
      setSummary(s);
      setEquation(eq);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load finance");
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  const kpis = (summary?.kpis as Record<string, unknown> | undefined) ?? summary ?? {};
  const activity = (summary?.activity as Record<string, unknown>[] | undefined) ?? [];

  return (
    <Screen title="Finance" onRefresh={() => void reload()} onBack={() => navigation.navigate("WorkspaceSwitcher")}>
      <ErrorText message={error} />
      <Kpi label="Revenue" value={money(kpis.revenue)} />
      <Kpi label="Expenses" value={money(kpis.expenses)} />
      <Kpi label="Net profit" value={money(kpis.net_profit)} />
      <Kpi label="Cash balance" value={money(kpis.cash_balance ?? kpis.cash_collected)} />
      <Kpi label="Assets" value={money(equation?.assets ?? equation?.total_assets)} />
      <Kpi
        label="Liabilities + equity"
        value={money(
          equation?.liabilities_plus_equity ??
            (Number(equation?.liabilities ?? 0) + Number(equation?.equity ?? 0) || equation?.liabilities)
        )}
      />
      {activity.map((row, i) => (
        <Row
          key={String(row.id ?? i)}
          title={String(row.label || "Entry")}
          subtitle={String(row.date || row.type || "")}
          meta={money(row.amount)}
        />
      ))}
    </Screen>
  );
}
