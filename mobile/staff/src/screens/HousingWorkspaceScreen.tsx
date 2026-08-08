import React, { useCallback, useEffect, useState } from "react";
import { StyleSheet, Text } from "react-native";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";

import { fetchHousingSummary } from "@/api/bootstrap";
import { Card, Screen } from "@/components/Screen";
import type { RootStackParamList } from "@/navigation/types";
import { colors } from "@/theme/colors";

type Props = NativeStackScreenProps<RootStackParamList, "HousingWorkspace">;

function num(summary: Record<string, unknown> | null, key: string): string {
  const v = summary?.[key];
  return typeof v === "number" ? String(v) : "—";
}

export function HousingWorkspaceScreen({ navigation }: Props) {
  const [summary, setSummary] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState("");

  const reload = useCallback(async () => {
    setError("");
    try {
      setSummary(await fetchHousingSummary());
    } catch (err) {
      setSummary(null);
      setError(err instanceof Error ? err.message : "Failed to load housing summary");
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  return (
    <Screen
      title="Housing"
      onRefresh={() => void reload()}
      onBack={() => navigation.navigate("WorkspaceSwitcher")}
    >
      {error ? <Text style={styles.error}>{error}</Text> : null}
      <Card>
        <Text style={styles.kpiLabel}>Active leases</Text>
        <Text style={styles.kpiValue}>{num(summary, "leases_active")}</Text>
      </Card>
      <Card>
        <Text style={styles.kpiLabel}>Residential vacant / occupied</Text>
        <Text style={styles.kpiValue}>
          {num(summary, "units_vacant")} / {num(summary, "units_occupied")}
        </Text>
      </Card>
      <Card>
        <Text style={styles.kpiLabel}>Charges pending / overdue</Text>
        <Text style={styles.kpiValue}>
          {num(summary, "charges_pending")} / {num(summary, "charges_overdue")}
        </Text>
      </Card>
      <Card>
        <Text style={styles.kpiLabel}>Tenants</Text>
        <Text style={styles.kpiValue}>{num(summary, "tenants")}</Text>
      </Card>
    </Screen>
  );
}

const styles = StyleSheet.create({
  kpiLabel: { color: colors.muted, fontSize: 13 },
  kpiValue: { color: colors.text, fontSize: 28, fontWeight: "700" },
  error: { color: colors.danger },
});
