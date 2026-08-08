import React from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";

import { Card, Screen } from "@/components/Screen";
import { useAuth } from "@/context/AuthContext";
import type { RootStackParamList } from "@/navigation/types";
import { colors } from "@/theme/colors";

type Props = NativeStackScreenProps<RootStackParamList, "WorkspaceSwitcher">;

const ROUTE_BY_WORKSPACE: Record<string, keyof RootStackParamList> = {
  gym_staff: "GymWorkspace",
  pharmacy_staff: "PharmacyWorkspace",
  hotel_staff: "HotelWorkspace",
  restaurant_staff: "RestaurantWorkspace",
  property_staff: "PropertyWorkspace",
  housing_staff: "HousingWorkspace",
  office_staff: "OfficeWorkspace",
};

export function WorkspaceSwitcherScreen({ navigation }: Props) {
  const { moduleWorkspaces, refreshBootstrap, signOut } = useAuth();

  return (
    <Screen title="Workspaces" onRefresh={() => void refreshBootstrap()}>
      <Card>
        <Text style={styles.lead}>
          Modules from your shop entitlement. Open a workspace to view live KPIs.
        </Text>
      </Card>

      {!moduleWorkspaces.length ? (
        <Card>
          <Text style={styles.empty}>
            No staff mobile workspaces available. Enable Gym, Pharmacy, Hotel, Restaurant, Property,
            Housing, or Office and ensure your role has view permissions.
          </Text>
        </Card>
      ) : (
        <View style={styles.grid}>
          {moduleWorkspaces.map((ws) => {
            const route = ROUTE_BY_WORKSPACE[ws.id];
            return (
              <Pressable
                key={ws.id}
                style={styles.tile}
                disabled={!route}
                onPress={() => route && navigation.navigate(route)}
              >
                <Text style={styles.tileLabel}>{ws.label}</Text>
                <Text style={styles.tileMeta}>{ws.module || "core"}</Text>
              </Pressable>
            );
          })}
        </View>
      )}

      <Pressable onPress={() => void signOut()} style={styles.signOut}>
        <Text style={styles.signOutText}>Sign out</Text>
      </Pressable>
    </Screen>
  );
}

const styles = StyleSheet.create({
  lead: { color: colors.muted, fontSize: 14, lineHeight: 20 },
  empty: { color: colors.muted, fontSize: 14 },
  grid: { gap: 10 },
  tile: {
    backgroundColor: colors.card,
    borderColor: colors.border,
    borderWidth: 1,
    borderRadius: 12,
    paddingVertical: 18,
    paddingHorizontal: 16,
  },
  tileLabel: { color: colors.text, fontSize: 18, fontWeight: "700" },
  tileMeta: { color: colors.muted, marginTop: 4, fontSize: 13 },
  signOut: { marginTop: 8, alignItems: "center", padding: 12 },
  signOutText: { color: colors.danger, fontWeight: "600" },
});
