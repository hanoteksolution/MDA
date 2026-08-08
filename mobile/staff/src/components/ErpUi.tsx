import React from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { colors } from "@/theme/colors";

export function Kpi({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.kpi}>
      <Text style={styles.kpiLabel}>{label}</Text>
      <Text style={styles.kpiValue}>{value}</Text>
    </View>
  );
}

export function Row({
  title,
  subtitle,
  meta,
  onPress,
}: {
  title: string;
  subtitle?: string;
  meta?: string;
  onPress?: () => void;
}) {
  const inner = (
    <>
      <View style={styles.rowMain}>
        <Text style={styles.rowTitle}>{title}</Text>
        {subtitle ? <Text style={styles.rowSub}>{subtitle}</Text> : null}
      </View>
      {meta ? <Text style={styles.rowMeta}>{meta}</Text> : null}
    </>
  );
  if (onPress) {
    return (
      <Pressable style={styles.row} onPress={onPress}>
        {inner}
      </Pressable>
    );
  }
  return <View style={styles.row}>{inner}</View>;
}

export function ErrorText({ message }: { message?: string }) {
  if (!message) return null;
  return <Text style={styles.error}>{message}</Text>;
}

const styles = StyleSheet.create({
  kpi: {
    backgroundColor: colors.card,
    borderColor: colors.border,
    borderWidth: 1,
    borderRadius: 12,
    padding: 14,
    gap: 4,
  },
  kpiLabel: { color: colors.muted, fontSize: 13 },
  kpiValue: { color: colors.text, fontSize: 24, fontWeight: "700" },
  row: {
    backgroundColor: colors.card,
    borderColor: colors.border,
    borderWidth: 1,
    borderRadius: 12,
    padding: 14,
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
  },
  rowMain: { flex: 1, gap: 2 },
  rowTitle: { color: colors.text, fontSize: 16, fontWeight: "600" },
  rowSub: { color: colors.muted, fontSize: 13 },
  rowMeta: { color: colors.accent, fontWeight: "700" },
  error: { color: colors.danger },
});
