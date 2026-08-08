import React, { useCallback, useEffect, useState } from "react";
import { StyleSheet, Text } from "react-native";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";

import { fetchGymSummary } from "@/api/bootstrap";
import { Card, Screen } from "@/components/Screen";
import type { RootStackParamList } from "@/navigation/types";
import { colors } from "@/theme/colors";

type Props = NativeStackScreenProps<RootStackParamList, "GymWorkspace">;

function pickCount(block: unknown, keys: string[]): string {
  if (!block || typeof block !== "object") return "—";
  const obj = block as Record<string, unknown>;
  for (const key of keys) {
    if (typeof obj[key] === "number") return String(obj[key]);
  }
  return "—";
}

export function GymWorkspaceScreen({ navigation }: Props) {
  const [summary, setSummary] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState("");

  const reload = useCallback(async () => {
    setError("");
    try {
      setSummary(await fetchGymSummary());
    } catch (err) {
      setSummary(null);
      setError(err instanceof Error ? err.message : "Failed to load gym summary");
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  const features =
    summary && typeof summary.features === "object" && summary.features
      ? (summary.features as Record<string, boolean>)
      : {};

  return (
    <Screen
      title="Gym"
      onRefresh={() => void reload()}
      onBack={() => navigation.navigate("WorkspaceSwitcher")}
    >
      {error ? <Text style={styles.error}>{error}</Text> : null}
      {features.members !== false ? (
        <>
          <Card>
            <Text style={styles.kpiLabel}>Members</Text>
            <Text style={styles.kpiValue}>
              {pickCount(summary?.members, ["total", "count", "active"])}
            </Text>
          </Card>
          <Card>
            <Text style={styles.kpiLabel}>Active subscriptions</Text>
            <Text style={styles.kpiValue}>
              {pickCount(summary?.subscriptions, ["active", "total", "count"])}
            </Text>
          </Card>
        </>
      ) : null}
      {features.attendance !== false ? (
        <Card>
          <Text style={styles.kpiLabel}>Today attendance</Text>
          <Text style={styles.kpiValue}>
            {pickCount(summary?.attendance, ["today_checkins", "today", "total"])}
          </Text>
        </Card>
      ) : null}
      <Card>
        <Text style={styles.kpiLabel}>Classes / workouts</Text>
        <Text style={styles.kpiValue}>
          {features.classes !== false
            ? pickCount(summary?.classes, ["upcoming_sessions", "upcoming", "total", "count"])
            : "—"}{" "}
          / {pickCount(summary?.workouts, ["active", "total", "count"])}
        </Text>
      </Card>
    </Screen>
  );
}

const styles = StyleSheet.create({
  kpiLabel: { color: colors.muted, fontSize: 13 },
  kpiValue: { color: colors.text, fontSize: 28, fontWeight: "700" },
  error: { color: colors.danger },
});
