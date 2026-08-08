import React, { useCallback, useEffect, useState } from "react";
import { StyleSheet, Text } from "react-native";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";

import { fetchHotelSummary } from "@/api/bootstrap";
import { Card, Screen } from "@/components/Screen";
import type { RootStackParamList } from "@/navigation/types";
import { colors } from "@/theme/colors";

type Props = NativeStackScreenProps<RootStackParamList, "HotelWorkspace">;

function num(summary: Record<string, unknown> | null, key: string): string {
  const v = summary?.[key];
  return typeof v === "number" ? String(v) : "—";
}

export function HotelWorkspaceScreen({ navigation }: Props) {
  const [summary, setSummary] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState("");

  const reload = useCallback(async () => {
    setError("");
    try {
      setSummary(await fetchHotelSummary());
    } catch (err) {
      setSummary(null);
      setError(err instanceof Error ? err.message : "Failed to load hotel summary");
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  return (
    <Screen
      title="Hotel"
      onRefresh={() => void reload()}
      onBack={() => navigation.navigate("WorkspaceSwitcher")}
    >
      {error ? <Text style={styles.error}>{error}</Text> : null}
      <Card>
        <Text style={styles.kpiLabel}>Rooms vacant / occupied</Text>
        <Text style={styles.kpiValue}>
          {num(summary, "rooms_vacant")} / {num(summary, "rooms_occupied")}
        </Text>
      </Card>
      <Card>
        <Text style={styles.kpiLabel}>In house</Text>
        <Text style={styles.kpiValue}>{num(summary, "in_house")}</Text>
      </Card>
      <Card>
        <Text style={styles.kpiLabel}>Arrivals / departures today</Text>
        <Text style={styles.kpiValue}>
          {num(summary, "arrivals_today")} / {num(summary, "departures_today")}
        </Text>
      </Card>
      <Card>
        <Text style={styles.kpiLabel}>Booked reservations</Text>
        <Text style={styles.kpiValue}>{num(summary, "reservations_booked")}</Text>
      </Card>
    </Screen>
  );
}

const styles = StyleSheet.create({
  kpiLabel: { color: colors.muted, fontSize: 13 },
  kpiValue: { color: colors.text, fontSize: 28, fontWeight: "700" },
  error: { color: colors.danger },
});
