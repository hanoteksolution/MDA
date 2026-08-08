import React, { useEffect, useState } from "react";
import { FlatList, StyleSheet, Text } from "react-native";

import { fetchClasses } from "@/api/gym";
import { Card, Loading, Screen } from "@/components/Screen";
import { colors } from "@/theme/colors";

export function ClassesScreen() {
  const [rows, setRows] = useState<
    Array<{ id: string; class_name: string; starts_at: string | null; status: string }>
  >([]);
  const [error, setError] = useState("");

  const load = async () => {
    setError("");
    try {
      const data = await fetchClasses();
      setRows(data.results);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load classes");
    }
  };

  useEffect(() => {
    void load();
  }, []);

  if (!rows.length && !error) return <Loading />;

  return (
    <Screen title="Classes" onRefresh={() => void load()}>
      {error ? <Text style={styles.error}>{error}</Text> : null}
      <FlatList
        data={rows}
        keyExtractor={(item) => item.id}
        renderItem={({ item }) => (
          <Card>
            <Text style={styles.title}>{item.class_name}</Text>
            <Text style={styles.meta}>
              {item.starts_at ?? "TBD"} · {item.status}
            </Text>
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
