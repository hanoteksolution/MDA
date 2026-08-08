import React from "react";
import {
  ActivityIndicator,
  Pressable,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";

import { colors } from "@/theme/colors";

export function Screen({
  title,
  children,
  onRefresh,
  onBack,
  scroll = true,
}: {
  title: string;
  children: React.ReactNode;
  onRefresh?: () => void;
  onBack?: () => void;
  scroll?: boolean;
}) {
  return (
    <SafeAreaView style={styles.safe}>
      <View style={styles.header}>
        <View style={styles.headerLeft}>
          {onBack ? (
            <Pressable onPress={onBack} style={styles.backBtn}>
              <Text style={styles.backText}>Back</Text>
            </Pressable>
          ) : null}
          <Text style={styles.title}>{title}</Text>
        </View>
        {onRefresh ? (
          <Pressable onPress={onRefresh} style={styles.refreshBtn}>
            <Text style={styles.refreshText}>Refresh</Text>
          </Pressable>
        ) : null}
      </View>
      {scroll ? (
        <ScrollView
          style={styles.scroll}
          contentContainerStyle={styles.body}
          keyboardShouldPersistTaps="handled"
        >
          {children}
        </ScrollView>
      ) : (
        <View style={styles.body}>{children}</View>
      )}
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
  headerLeft: { flexDirection: "row", alignItems: "center", gap: 10, flex: 1 },
  title: { color: colors.text, fontSize: 22, fontWeight: "700" },
  backBtn: { paddingVertical: 4, paddingRight: 4 },
  backText: { color: colors.accent, fontWeight: "600" },
  refreshBtn: { paddingHorizontal: 12, paddingVertical: 8 },
  refreshText: { color: colors.accent, fontWeight: "600" },
  scroll: { flex: 1 },
  body: { padding: 20, gap: 12, paddingBottom: 40 },
  center: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: colors.bg,
  },
  card: {
    backgroundColor: colors.card,
    borderRadius: 12,
    padding: 16,
    borderWidth: 1,
    borderColor: colors.border,
    gap: 6,
  },
});
