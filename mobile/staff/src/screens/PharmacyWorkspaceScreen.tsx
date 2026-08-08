import React, { useCallback, useEffect, useState } from "react";
import { StyleSheet, Text } from "react-native";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";

import { fetchPharmacySummary } from "@/api/bootstrap";
import { Card, Screen } from "@/components/Screen";
import type { RootStackParamList } from "@/navigation/types";
import { colors } from "@/theme/colors";

type Props = NativeStackScreenProps<RootStackParamList, "PharmacyWorkspace">;

function num(summary: Record<string, unknown> | null, key: string): string {
  const v = summary?.[key];
  return typeof v === "number" ? String(v) : "—";
}

export function PharmacyWorkspaceScreen({ navigation }: Props) {
  const [summary, setSummary] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState("");

  const reload = useCallback(async () => {
    setError("");
    try {
      setSummary(await fetchPharmacySummary());
    } catch (err) {
      setSummary(null);
      setError(err instanceof Error ? err.message : "Failed to load pharmacy summary");
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  return (
    <Screen
      title="Pharmacy"
      onRefresh={() => void reload()}
      onBack={() => navigation.navigate("WorkspaceSwitcher")}
    >
      {error ? <Text style={styles.error}>{error}</Text> : null}
      <Card>
        <Text style={styles.kpiLabel}>Active batches</Text>
        <Text style={styles.kpiValue}>{num(summary, "batch_count")}</Text>
      </Card>
      <Card>
        <Text style={styles.kpiLabel}>Expiring / expired</Text>
        <Text style={styles.kpiValue}>
          {num(summary, "expiring_count")} / {num(summary, "expired_count")}
        </Text>
      </Card>
      <Card>
        <Text style={styles.kpiLabel}>Active Rx</Text>
        <Text style={styles.kpiValue}>{num(summary, "prescriptions_active")}</Text>
      </Card>
      <Card>
        <Text style={styles.kpiLabel}>Dispensed Rx</Text>
        <Text style={styles.kpiValue}>{num(summary, "prescriptions_dispensed")}</Text>
      </Card>
    </Screen>
  );
}

const styles = StyleSheet.create({
  kpiLabel: { color: colors.muted, fontSize: 13 },
  kpiValue: { color: colors.text, fontSize: 28, fontWeight: "700" },
  error: { color: colors.danger },
});
