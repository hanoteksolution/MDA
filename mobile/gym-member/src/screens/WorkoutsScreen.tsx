import React, { useEffect, useState } from "react";
import { FlatList, StyleSheet, Text } from "react-native";

import { fetchWorkouts } from "@/api/gym";
import { Card, Loading, Screen } from "@/components/Screen";
import { colors } from "@/theme/colors";

export function WorkoutsScreen() {
  const [rows, setRows] = useState<Array<{ id: string; plan_name: string; status: string }>>(
    []
  );
  const [error, setError] = useState("");

  const load = async () => {
    setError("");
    try {
      const data = await fetchWorkouts();
      setRows(data.results);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load workouts");
    }
  };

  useEffect(() => {
    void load();
  }, []);

  if (!rows.length && !error) return <Loading />;

  return (
    <Screen title="Workouts" onRefresh={() => void load()}>
      {error ? <Text style={styles.error}>{error}</Text> : null}
      <FlatList
        data={rows}
        keyExtractor={(item) => item.id}
        renderItem={({ item }) => (
          <Card>
            <Text style={styles.title}>{item.plan_name}</Text>
            <Text style={styles.meta}>{item.status}</Text>
          </Card>
        )}
        ItemSeparatorComponent={() => <Text> </Text>}
      />
    </Screen>
  );
}

const styles = StyleSheet.create({
  title: { color: colors.text, fontWeight: "600" },
  meta: { color: colors.muted, fontSize: 13 },
  error: { color: colors.danger },
});
