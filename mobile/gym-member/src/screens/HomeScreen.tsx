import React from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";

import { Card, Screen } from "@/components/Screen";
import { useAuth } from "@/context/AuthContext";
import { navButtonsFromScreens } from "@/modules/registry";
import type { RootStackParamList } from "@/navigation/types";
import { colors } from "@/theme/colors";

type Props = NativeStackScreenProps<RootStackParamList, "Home">;

export function HomeScreen({ navigation }: Props) {
  const { home, refreshBootstrap, signOut, gymModuleEnabled, mobileNav } = useAuth();
  const member = home?.member;
  const sub = home?.active_subscription;
  const buttons = navButtonsFromScreens(mobileNav?.screens);

  return (
    <Screen title="Home" onRefresh={() => void refreshBootstrap()}>
      {!gymModuleEnabled ? (
        <Card>
          <Text style={styles.name}>Gym module unavailable</Text>
          <Text style={styles.meta}>
            This shop does not have the gym module enabled, or your account lacks member portal
            access. Contact reception.
          </Text>
        </Card>
      ) : (
        <>
          <Card>
            <Text style={styles.name}>{member?.full_name ?? "Member"}</Text>
            <Text style={styles.meta}>{member?.membership_number}</Text>
            <Text style={styles.meta}>
              Status: {member?.status} · Today visits: {home?.today_checkins ?? 0}
            </Text>
            <Text style={[styles.meta, home?.is_checked_in ? styles.ok : undefined]}>
              {home?.is_checked_in ? "Currently checked in" : "Not checked in"}
            </Text>
          </Card>

          <Card>
            <Text style={styles.section}>Membership</Text>
            {sub ? (
              <>
                <Text style={styles.meta}>{sub.plan_name}</Text>
                <Text style={styles.meta}>
                  {sub.status} · until {sub.end_date ?? "—"}
                </Text>
              </>
            ) : (
              <Text style={styles.meta}>No active subscription</Text>
            )}
          </Card>

          <View style={styles.grid}>
            {buttons.map((btn) => (
              <NavButton
                key={btn.id}
                label={btn.label}
                onPress={() => navigation.navigate(btn.route)}
              />
            ))}
          </View>
        </>
      )}

      <Pressable onPress={() => void signOut()} style={styles.signOut}>
        <Text style={styles.signOutText}>Sign out</Text>
      </Pressable>
    </Screen>
  );
}

function NavButton({ label, onPress }: { label: string; onPress: () => void }) {
  return (
    <Pressable style={styles.navBtn} onPress={onPress}>
      <Text style={styles.navText}>{label}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  name: { color: colors.text, fontSize: 20, fontWeight: "700" },
  meta: { color: colors.muted, fontSize: 14 },
  ok: { color: colors.success },
  section: { color: colors.text, fontWeight: "600", marginBottom: 4 },
  grid: { flexDirection: "row", flexWrap: "wrap", gap: 10 },
  navBtn: {
    backgroundColor: colors.card,
    borderColor: colors.border,
    borderWidth: 1,
    borderRadius: 10,
    paddingVertical: 16,
    paddingHorizontal: 14,
    minWidth: "47%",
  },
  navText: { color: colors.text, fontWeight: "600" },
  signOut: { marginTop: 8, alignItems: "center", padding: 12 },
  signOutText: { color: colors.danger, fontWeight: "600" },
});
