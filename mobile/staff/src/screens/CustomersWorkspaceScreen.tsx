import React, { useCallback, useEffect, useState } from "react";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";

import { fetchCustomerSummary, fetchCustomers, money } from "@/api/erp";
import { Screen } from "@/components/Screen";
import { ErrorText, Kpi, Row } from "@/components/ErpUi";
import type { RootStackParamList } from "@/navigation/types";

type Props = NativeStackScreenProps<RootStackParamList, "CustomersWorkspace">;

export function CustomersWorkspaceScreen({ navigation }: Props) {
  const [summary, setSummary] = useState<Record<string, unknown> | null>(null);
  const [rows, setRows] = useState<Record<string, unknown>[]>([]);
  const [error, setError] = useState("");

  const reload = useCallback(async () => {
    setError("");
    try {
      const [s, list] = await Promise.all([fetchCustomerSummary(), fetchCustomers()]);
      setSummary(s);
      setRows(list.results ?? []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load customers");
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  return (
    <Screen title="Customers" onRefresh={() => void reload()} onBack={() => navigation.navigate("WorkspaceSwitcher")}>
      <ErrorText message={error} />
      <Kpi label="Total" value={String(summary?.total ?? summary?.count ?? rows.length)} />
      <Kpi label="Active" value={String(summary?.active ?? "—")} />
      {rows.map((c) => (
        <Row
          key={String(c.id)}
          title={String(c.full_name || "Customer")}
          subtitle={`${c.customer_code || ""} · ${c.phone || c.email || ""}`}
          meta={money(c.outstanding_balance)}
        />
      ))}
    </Screen>
  );
}
