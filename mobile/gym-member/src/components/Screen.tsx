import React from "react";
import {
  ActivityIndicator,
  Pressable,
  SafeAreaView,
  StyleSheet,
  Text,
  View,
} from "react-native";

import { colors } from "@/theme/colors";

export function Screen({
  title,
  children,
  onRefresh,
}: {
  title: string;
  children: React.ReactNode;
  onRefresh?: () => void;
}) {
  return (
    <SafeAreaView style={styles.safe}>
      <View style={styles.header}>
        <Text style={styles.title}>{title}</Text>
        {onRefresh ? (
          <Pressable onPress={onRefresh} style={styles.refreshBtn}>
            <Text style={styles.refreshText}>Refresh</Text>
          </Pressable>
        ) : null}
      </View>
      <View style={styles.body}>{children}</View>
    </SafeAreaView>
  );
}

export function Loading() {
  return (
    <View style={styles.center}>
      <ActivityIndicator color={colors.accent} size="large" />
    </View>
  );
}

export function Card({ children }: { children: React.ReactNode }) {
  return <View style={styles.card}>{children}</View>;
}

export function Muted({ children }: { children: React.ReactNode }) {
  return <Text style={styles.muted}>{children}</Text>;
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.bg },
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: 20,
    paddingVertical: 16,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  title: { color: colors.text, fontSize: 22, fontWeight: "700" },
  refreshBtn: { paddingHorizontal: 12, paddingVertical: 8 },
  refreshText: { color: colors.accent, fontWeight: "600" },
  body: { flex: 1, padding: 20, gap: 12 },
  center: { flex: 1, alignItems: "center", justifyContent: "center", backgroundColor: colors.bg },
  card: {
    backgroundColor: colors.card,
    borderRadius: 12,
    padding: 16,
    borderWidth: 1,
    borderColor: colors.border,
    gap: 6,
  },
  muted: { color: colors.muted, fontSize: 14 },
});
