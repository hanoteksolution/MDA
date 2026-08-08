import React, { useCallback, useEffect, useState } from "react";
import { StyleSheet, Text } from "react-native";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";

import { fetchFutsalSummary } from "@/api/bootstrap";
import { Card, Screen } from "@/components/Screen";
import type { RootStackParamList } from "@/navigation/types";
import { colors } from "@/theme/colors";

type Props = NativeStackScreenProps<RootStackParamList, "FutsalWorkspace">;

function num(summary: Record<string, unknown> | null, key: string): string {
  const v = summary?.[key];
  return typeof v === "number" ? String(v) : "—";
}

export function FutsalWorkspaceScreen({ navigation }: Props) {
  const [summary, setSummary] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState("");

  const reload = useCallback(async () => {
    setError("");
    try {
      setSummary(await fetchFutsalSummary());
    } catch (err) {
      setSummary(null);
      setError(err instanceof Error ? err.message : "Failed to load futsal summary");
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  return (
    <Screen
      title="Futsal"
      onRefresh={() => void reload()}
      onBack={() => navigation.navigate("WorkspaceSwitcher")}
    >
      {error ? <Text style={styles.error}>{error}</Text> : null}
      <Card>
        <Text style={styles.kpiLabel}>Courts / teams / players</Text>
        <Text style={styles.kpiValue}>
          {num(summary, "courts")} / {num(summary, "teams")} / {num(summary, "players")}
        </Text>
      </Card>
      <Card>
        <Text style={styles.kpiLabel}>Bookings today</Text>
        <Text style={styles.kpiValue}>{num(summary, "bookings_today")}</Text>
      </Card>
      <Card>
        <Text style={styles.kpiLabel}>Hours today</Text>
        <Text style={styles.kpiValue}>{num(summary, "hours_today")}</Text>
      </Card>
      <Card>
        <Text style={styles.kpiLabel}>Month profit</Text>
        <Text style={styles.kpiValue}>{num(summary, "profit_month")}</Text>
      </Card>
    </Screen>
  );
}

const styles = StyleSheet.create({
  kpiLabel: { color: colors.muted, fontSize: 13 },
  kpiValue: { color: colors.text, fontSize: 28, fontWeight: "700" },
  error: { color: colors.danger },
});
