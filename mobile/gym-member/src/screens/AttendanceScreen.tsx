import React, { useEffect, useState } from "react";
import { FlatList, StyleSheet, Text } from "react-native";

import { fetchAttendance, type GymAttendance } from "@/api/gym";
import { Card, Loading, Screen } from "@/components/Screen";
import { colors } from "@/theme/colors";

export function AttendanceScreen() {
  const [rows, setRows] = useState<GymAttendance[]>([]);
  const [error, setError] = useState("");

  const load = async () => {
    setError("");
    try {
      const data = await fetchAttendance();
      setRows(data.results);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load attendance");
    }
  };

  useEffect(() => {
    void load();
  }, []);

  if (!rows.length && !error) return <Loading />;

  return (
    <Screen title="Attendance" onRefresh={() => void load()}>
      {error ? <Text style={styles.error}>{error}</Text> : null}
      <FlatList
        data={rows}
        keyExtractor={(item) => item.id}
        renderItem={({ item }) => (
          <Card>
            <Text style={styles.when}>{item.check_in_at ?? "—"}</Text>
            <Text style={styles.meta}>
              {item.branch_name ?? "Main"} · {item.is_open ? "Open visit" : "Completed"}
            </Text>
          </Card>
        )}
        ItemSeparatorComponent={() => <Text> </Text>}
      />
    </Screen>
  );
}

const styles = StyleSheet.create({
  when: { color: colors.text, fontWeight: "600" },
  meta: { color: colors.muted, fontSize: 13 },
  error: { color: colors.danger },
});
