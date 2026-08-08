import React, { useCallback, useEffect, useState } from "react";
import { StyleSheet, Text } from "react-native";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";

import { fetchRestaurantSummary } from "@/api/bootstrap";
import { Card, Screen } from "@/components/Screen";
import type { RootStackParamList } from "@/navigation/types";
import { colors } from "@/theme/colors";

type Props = NativeStackScreenProps<RootStackParamList, "RestaurantWorkspace">;

function num(summary: Record<string, unknown> | null, key: string): string {
  const v = summary?.[key];
  return typeof v === "number" ? String(v) : "—";
}

export function RestaurantWorkspaceScreen({ navigation }: Props) {
  const [summary, setSummary] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState("");

  const reload = useCallback(async () => {
    setError("");
    try {
      setSummary(await fetchRestaurantSummary());
    } catch (err) {
      setSummary(null);
      setError(err instanceof Error ? err.message : "Failed to load restaurant summary");
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  return (
    <Screen
      title="Restaurant"
      onRefresh={() => void reload()}
      onBack={() => navigation.navigate("WorkspaceSwitcher")}
    >
      {error ? <Text style={styles.error}>{error}</Text> : null}
      <Card>
        <Text style={styles.kpiLabel}>Open orders</Text>
        <Text style={styles.kpiValue}>{num(summary, "orders_open")}</Text>
      </Card>
      <Card>
        <Text style={styles.kpiLabel}>Orders today</Text>
        <Text style={styles.kpiValue}>{num(summary, "orders_today")}</Text>
      </Card>
      <Card>
        <Text style={styles.kpiLabel}>Tables occupied / total</Text>
        <Text style={styles.kpiValue}>
          {num(summary, "tables_occupied")} / {num(summary, "tables")}
        </Text>
      </Card>
      <Card>
        <Text style={styles.kpiLabel}>Menu items</Text>
        <Text style={styles.kpiValue}>{num(summary, "menu_items")}</Text>
      </Card>
    </Screen>
  );
}

const styles = StyleSheet.create({
  kpiLabel: { color: colors.muted, fontSize: 13 },
  kpiValue: { color: colors.text, fontSize: 28, fontWeight: "700" },
  error: { color: colors.danger },
});
