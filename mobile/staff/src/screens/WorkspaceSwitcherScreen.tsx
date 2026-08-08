import React, { useMemo } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";

import { Card, Screen } from "@/components/Screen";
import { useAuth } from "@/context/AuthContext";
import type { RootStackParamList } from "@/navigation/types";
import { colors } from "@/theme/colors";

type Props = NativeStackScreenProps<RootStackParamList, "WorkspaceSwitcher">;

const ROUTE_BY_WORKSPACE: Record<string, keyof RootStackParamList> = {
  dashboard_staff: "DashboardWorkspace",
  pos_staff: "PosWorkspace",
  sales_staff: "SalesWorkspace",
  inventory_staff: "InventoryWorkspace",
  purchases_staff: "PurchasesWorkspace",
  customers_staff: "CustomersWorkspace",
  suppliers_staff: "SuppliersWorkspace",
  finance_staff: "FinanceWorkspace",
  business_units_staff: "BusinessUnitsWorkspace",
  reports_staff: "ReportsWorkspace",
  settings_staff: "SettingsWorkspace",
  gym_staff: "GymWorkspace",
  pharmacy_staff: "PharmacyWorkspace",
  hotel_staff: "HotelWorkspace",
  restaurant_staff: "RestaurantWorkspace",
  property_staff: "PropertyWorkspace",
  housing_staff: "HousingWorkspace",
  office_staff: "OfficeWorkspace",
  futsal_staff: "FutsalWorkspace",
};

const GROUPS: { id: string; label: string }[] = [
  { id: "core", label: "Operations" },
  { id: "finance", label: "Finance" },
  { id: "venue", label: "Venues" },
];

export function WorkspaceSwitcherScreen({ navigation }: Props) {
  const { moduleWorkspaces, refreshBootstrap, signOut } = useAuth();

  const grouped = useMemo(() => {
    return GROUPS.map((g) => ({
      ...g,
      items: moduleWorkspaces.filter((w) => (w.group || "venue") === g.id),
    })).filter((g) => g.items.length);
  }, [moduleWorkspaces]);

  return (
    <Screen title="Workspaces" onRefresh={() => void refreshBootstrap()}>
      <Card>
        <Text style={styles.lead}>
          Same ERP modules as web — POS, sales, inventory, finance, business units, and venues —
          filtered by your shop entitlement and role.
        </Text>
      </Card>

      {!moduleWorkspaces.length ? (
        <Card>
          <Text style={styles.empty}>
            No staff mobile workspaces available. Enable modules and ensure your role has view
            permissions.
          </Text>
        </Card>
      ) : (
        grouped.map((group) => (
          <View key={group.id} style={styles.group}>
            <Text style={styles.groupLabel}>{group.label}</Text>
            {group.items.map((ws) => {
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
        ))
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
  group: { gap: 8 },
  groupLabel: { color: colors.muted, fontWeight: "700", marginTop: 8, textTransform: "uppercase" },
  tile: {
    backgroundColor: colors.card,
    borderColor: colors.border,
    borderWidth: 1,
    borderRadius: 12,
    paddingVertical: 16,
    paddingHorizontal: 16,
  },
  tileLabel: { color: colors.text, fontSize: 18, fontWeight: "700" },
  tileMeta: { color: colors.muted, marginTop: 4, fontSize: 13 },
  signOut: { marginTop: 8, alignItems: "center", padding: 12 },
  signOutText: { color: colors.danger, fontWeight: "600" },
});
