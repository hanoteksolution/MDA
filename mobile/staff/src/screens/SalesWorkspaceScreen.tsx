import React, { useCallback, useEffect, useState } from "react";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";

import { fetchInvoices, fetchSalesSummary, money } from "@/api/erp";
import { Screen } from "@/components/Screen";
import { ErrorText, Kpi, Row } from "@/components/ErpUi";
import type { RootStackParamList } from "@/navigation/types";

type Props = NativeStackScreenProps<RootStackParamList, "SalesWorkspace">;

export function SalesWorkspaceScreen({ navigation }: Props) {
  const [summary, setSummary] = useState<Record<string, unknown> | null>(null);
  const [rows, setRows] = useState<Record<string, unknown>[]>([]);
  const [error, setError] = useState("");

  const reload = useCallback(async () => {
    setError("");
    try {
      const [s, list] = await Promise.all([fetchSalesSummary(), fetchInvoices()]);
      setSummary(s);
      setRows(list.results ?? []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load sales");
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  return (
    <Screen title="Sales" onRefresh={() => void reload()} onBack={() => navigation.navigate("WorkspaceSwitcher")}>
      <ErrorText message={error} />
      <Kpi label="Today sales" value={money(summary?.today_sales)} />
      <Kpi label="Month sales" value={money(summary?.month_sales)} />
      <Kpi label="Open invoices" value={String(summary?.open_invoices ?? "—")} />
      <Kpi label="Quotations" value={String(summary?.quotations_count ?? "—")} />
      {rows.map((inv) => (
        <Row
          key={String(inv.id)}
          title={String(inv.number || inv.invoice_number || "Invoice")}
          subtitle={`${inv.customer_name || ""} · ${inv.status || ""}`}
          meta={money(inv.total_amount)}
        />
      ))}
    </Screen>
  );
}
