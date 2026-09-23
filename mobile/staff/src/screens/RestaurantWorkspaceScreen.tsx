import React, { useCallback, useEffect, useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";

import { apiRequest } from "@/api/client";
import { fetchRestaurantSummary } from "@/api/bootstrap";
import { Card, Screen } from "@/components/Screen";
import type { RootStackParamList } from "@/navigation/types";
import { colors } from "@/theme/colors";

type Props = NativeStackScreenProps<RootStackParamList, "RestaurantWorkspace">;

type Ticket = {
  id: string;
  order_number: string;
  queue_number?: string;
  elapsed_seconds?: number;
  board_column?: string;
  lines?: { name: string; quantity: number }[];
};

function num(summary: Record<string, unknown> | null, key: string): string {
  const v = summary?.[key];
  return typeof v === "number" ? String(v) : "—";
}

function formatElapsed(seconds?: number) {
  const s = seconds || 0;
  const m = Math.floor(s / 60);
  const r = s % 60;
  return `${String(m).padStart(2, "0")}:${String(r).padStart(2, "0")}`;
}

export function RestaurantWorkspaceScreen({ navigation }: Props) {
  const [summary, setSummary] = useState<Record<string, unknown> | null>(null);
  const [mode, setMode] = useState<"dashboard" | "barista">("dashboard");
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState<string | null>(null);

  const reload = useCallback(async () => {
    setError("");
    try {
      setSummary(await fetchRestaurantSummary());
      if (mode === "barista") {
        const data = await apiRequest<{
          columns?: { NEW?: Ticket[]; PREPARING?: Ticket[]; READY?: Ticket[] };
        }>("/restaurant/barista/queue/");
        const cols = data?.columns || {};
        setTickets([...(cols.NEW || []), ...(cols.PREPARING || []), ...(cols.READY || [])]);
      }
    } catch (err) {
      setSummary(null);
      setError(err instanceof Error ? err.message : "Failed to load cafeteria");
    }
  }, [mode]);

  useEffect(() => {
    void reload();
    const id = setInterval(() => void reload(), 15000);
    return () => clearInterval(id);
  }, [reload]);

  const act = async (id: string, action: string) => {
    setBusy(id);
    try {
      await apiRequest(`/restaurant/barista/tickets/${id}/${action}/`, {
        method: "POST",
        body: JSON.stringify({}),
      });
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Action failed");
    } finally {
      setBusy(null);
    }
  };

  return (
    <Screen
      title={mode === "barista" ? "Barista Queue" : "Cafeteria"}
      onRefresh={() => void reload()}
      onBack={() => navigation.navigate("WorkspaceSwitcher")}
    >
      {error ? <Text style={styles.error}>{error}</Text> : null}

      <View style={styles.tabs}>
        <Pressable
          style={[styles.tab, mode === "dashboard" && styles.tabActive]}
          onPress={() => setMode("dashboard")}
        >
          <Text style={styles.tabText}>Dashboard</Text>
        </Pressable>
        <Pressable
          style={[styles.tab, mode === "barista" && styles.tabActive]}
          onPress={() => setMode("barista")}
        >
          <Text style={styles.tabText}>Barista</Text>
        </Pressable>
      </View>

      {mode === "dashboard" ? (
        <>
          <Card>
            <Text style={styles.kpiLabel}>Today's sales</Text>
            <Text style={styles.kpiValue}>{num(summary, "todays_sales")}</Text>
          </Card>
          <Card>
            <Text style={styles.kpiLabel}>Open / Preparing / Ready</Text>
            <Text style={styles.kpiValue}>
              {num(summary, "orders_open")} / {num(summary, "orders_preparing")} /{" "}
              {num(summary, "orders_ready")}
            </Text>
          </Card>
          <Card>
            <Text style={styles.kpiLabel}>Orders today</Text>
            <Text style={styles.kpiValue}>{num(summary, "orders_today")}</Text>
          </Card>
          <Card>
            <Text style={styles.kpiLabel}>Menu items</Text>
            <Text style={styles.kpiValue}>{num(summary, "menu_items")}</Text>
          </Card>
        </>
      ) : (
        <>
          {tickets.length === 0 ? (
            <Card>
              <Text style={styles.muted}>No tickets in queue</Text>
            </Card>
          ) : (
            tickets.map((t) => (
              <Card key={t.id}>
                <View style={styles.ticketHeader}>
                  <Text style={styles.ticketTitle}>{t.order_number}</Text>
                  <Text style={styles.elapsed}>{formatElapsed(t.elapsed_seconds)}</Text>
                </View>
                {t.queue_number ? (
                  <Text style={styles.muted}>Queue #{t.queue_number}</Text>
                ) : null}
                <Text style={styles.muted}>{t.board_column || "NEW"}</Text>
                {(t.lines || []).map((l, idx) => (
                  <Text key={idx} style={styles.line}>
                    {l.quantity}× {l.name}
                  </Text>
                ))}
                <View style={styles.actions}>
                  {(t.board_column === "NEW" || !t.board_column) && (
                    <Pressable
                      style={styles.actionBtn}
                      disabled={busy === t.id}
                      onPress={() => void act(t.id, "accept")}
                    >
                      <Text style={styles.actionText}>Accept</Text>
                    </Pressable>
                  )}
                  {t.board_column === "PREPARING" && (
                    <Pressable
                      style={styles.actionBtn}
                      disabled={busy === t.id}
                      onPress={() => void act(t.id, "ready")}
                    >
                      <Text style={styles.actionText}>Ready</Text>
                    </Pressable>
                  )}
                  {t.board_column === "READY" && (
                    <Pressable
                      style={styles.actionBtn}
                      disabled={busy === t.id}
                      onPress={() => void act(t.id, "complete")}
                    >
                      <Text style={styles.actionText}>Complete</Text>
                    </Pressable>
                  )}
                </View>
              </Card>
            ))
          )}
        </>
      )}
    </Screen>
  );
}

const styles = StyleSheet.create({
  kpiLabel: { color: colors.muted, fontSize: 13 },
  kpiValue: { color: colors.text, fontSize: 28, fontWeight: "700" },
  error: { color: colors.danger, marginBottom: 8 },
  muted: { color: colors.muted, fontSize: 13, marginTop: 4 },
  tabs: { flexDirection: "row", gap: 8, marginBottom: 12 },
  tab: {
    flex: 1,
    paddingVertical: 10,
    borderRadius: 10,
    backgroundColor: colors.card,
    alignItems: "center",
  },
  tabActive: { backgroundColor: "#92400e" },
  tabText: { color: colors.text, fontWeight: "600" },
  ticketHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  ticketTitle: { color: colors.text, fontSize: 20, fontWeight: "700" },
  elapsed: { color: "#92400e", fontWeight: "700", fontSize: 16 },
  line: { color: colors.text, fontSize: 16, marginTop: 6 },
  actions: { flexDirection: "row", gap: 8, marginTop: 12 },
  actionBtn: {
    backgroundColor: "#92400e",
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderRadius: 10,
    minWidth: 96,
    alignItems: "center",
  },
  actionText: { color: "#fff", fontWeight: "700", fontSize: 16 },
});
