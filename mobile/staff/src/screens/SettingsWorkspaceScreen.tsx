import React, { useCallback, useEffect, useState } from "react";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";

import { fetchBranches, fetchCompany } from "@/api/erp";
import { Screen } from "@/components/Screen";
import { ErrorText, Kpi, Row } from "@/components/ErpUi";
import type { RootStackParamList } from "@/navigation/types";

type Props = NativeStackScreenProps<RootStackParamList, "SettingsWorkspace">;

export function SettingsWorkspaceScreen({ navigation }: Props) {
  const [company, setCompany] = useState<Record<string, unknown> | null>(null);
  const [branches, setBranches] = useState<Record<string, unknown>[]>([]);
  const [error, setError] = useState("");

  const reload = useCallback(async () => {
    setError("");
    try {
      const [c, b] = await Promise.all([fetchCompany(), fetchBranches()]);
      setCompany(c);
      setBranches(Array.isArray(b) ? b : []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load settings");
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  return (
    <Screen title="Settings" onRefresh={() => void reload()} onBack={() => navigation.navigate("WorkspaceSwitcher")}>
      <ErrorText message={error} />
      <Kpi label="Company" value={String(company?.name || "—")} />
      <Kpi label="Tax ID" value={String(company?.tax_id || company?.legal_name || "—")} />
      {branches.map((br) => (
        <Row
          key={String(br.id)}
          title={String(br.name || "Branch")}
          subtitle={`${br.code || ""} · ${br.address || ""}`}
          meta={br.is_default ? "default" : ""}
        />
      ))}
    </Screen>
  );
}
