import React, { useCallback, useEffect, useState } from "react";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";

import { fetchSuppliers, money } from "@/api/erp";
import { Screen } from "@/components/Screen";
import { ErrorText, Row } from "@/components/ErpUi";
import type { RootStackParamList } from "@/navigation/types";

type Props = NativeStackScreenProps<RootStackParamList, "SuppliersWorkspace">;

export function SuppliersWorkspaceScreen({ navigation }: Props) {
  const [rows, setRows] = useState<Record<string, unknown>[]>([]);
  const [error, setError] = useState("");

  const reload = useCallback(async () => {
    setError("");
    try {
      const list = await fetchSuppliers();
      setRows(list.results ?? []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load suppliers");
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  return (
    <Screen title="Suppliers" onRefresh={() => void reload()} onBack={() => navigation.navigate("WorkspaceSwitcher")}>
      <ErrorText message={error} />
      {rows.map((s) => (
        <Row
          key={String(s.id)}
          title={String(s.company_name || "Supplier")}
          subtitle={`${s.supplier_code || ""} · ${s.contact_person || s.phone || ""}`}
          meta={money(s.outstanding_balance)}
        />
      ))}
    </Screen>
  );
}
