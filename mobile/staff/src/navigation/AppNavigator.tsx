import { createNativeStackNavigator } from "@react-navigation/native-stack";
import React from "react";

import { BusinessUnitsWorkspaceScreen } from "@/screens/BusinessUnitsWorkspaceScreen";
import { CustomersWorkspaceScreen } from "@/screens/CustomersWorkspaceScreen";
import { DashboardWorkspaceScreen } from "@/screens/DashboardWorkspaceScreen";
import { FinanceWorkspaceScreen } from "@/screens/FinanceWorkspaceScreen";
import { FutsalWorkspaceScreen } from "@/screens/FutsalWorkspaceScreen";
import { FieldOpsScreen } from "@/screens/FieldOpsScreen";
import { GymWorkspaceScreen } from "@/screens/GymWorkspaceScreen";
import { HotelWorkspaceScreen } from "@/screens/HotelWorkspaceScreen";
import { HousingWorkspaceScreen } from "@/screens/HousingWorkspaceScreen";
import { InventoryWorkspaceScreen } from "@/screens/InventoryWorkspaceScreen";
import { OfficeWorkspaceScreen } from "@/screens/OfficeWorkspaceScreen";
import { PharmacyWorkspaceScreen } from "@/screens/PharmacyWorkspaceScreen";
import { PosWorkspaceScreen } from "@/screens/PosWorkspaceScreen";
import { PropertyWorkspaceScreen } from "@/screens/PropertyWorkspaceScreen";
import { PurchasesWorkspaceScreen } from "@/screens/PurchasesWorkspaceScreen";
import { ReportsWorkspaceScreen } from "@/screens/ReportsWorkspaceScreen";
import { RestaurantWorkspaceScreen } from "@/screens/RestaurantWorkspaceScreen";
import { SalesWorkspaceScreen } from "@/screens/SalesWorkspaceScreen";
import { SettingsWorkspaceScreen } from "@/screens/SettingsWorkspaceScreen";
import { SuppliersWorkspaceScreen } from "@/screens/SuppliersWorkspaceScreen";
import { WorkspaceSwitcherScreen } from "@/screens/WorkspaceSwitcherScreen";

import type { RootStackParamList } from "./types";

const Stack = createNativeStackNavigator<RootStackParamList>();

export function AppNavigator() {
  return (
    <Stack.Navigator
      screenOptions={{
        headerShown: false,
        contentStyle: { backgroundColor: "#0f172a" },
      }}
    >
      <Stack.Screen name="WorkspaceSwitcher" component={WorkspaceSwitcherScreen} />
      <Stack.Screen name="DashboardWorkspace" component={DashboardWorkspaceScreen} />
      <Stack.Screen name="PosWorkspace" component={PosWorkspaceScreen} />
      <Stack.Screen name="SalesWorkspace" component={SalesWorkspaceScreen} />
      <Stack.Screen name="InventoryWorkspace" component={InventoryWorkspaceScreen} />
      <Stack.Screen name="PurchasesWorkspace" component={PurchasesWorkspaceScreen} />
      <Stack.Screen name="CustomersWorkspace" component={CustomersWorkspaceScreen} />
      <Stack.Screen name="SuppliersWorkspace" component={SuppliersWorkspaceScreen} />
      <Stack.Screen name="FinanceWorkspace" component={FinanceWorkspaceScreen} />
      <Stack.Screen name="BusinessUnitsWorkspace" component={BusinessUnitsWorkspaceScreen} />
      <Stack.Screen name="ReportsWorkspace" component={ReportsWorkspaceScreen} />
      <Stack.Screen name="SettingsWorkspace" component={SettingsWorkspaceScreen} />
      <Stack.Screen name="GymWorkspace" component={GymWorkspaceScreen} />
      <Stack.Screen name="PharmacyWorkspace" component={PharmacyWorkspaceScreen} />
      <Stack.Screen name="HotelWorkspace" component={HotelWorkspaceScreen} />
      <Stack.Screen name="RestaurantWorkspace" component={RestaurantWorkspaceScreen} />
      <Stack.Screen name="PropertyWorkspace" component={PropertyWorkspaceScreen} />
      <Stack.Screen name="HousingWorkspace" component={HousingWorkspaceScreen} />
      <Stack.Screen name="OfficeWorkspace" component={OfficeWorkspaceScreen} />
      <Stack.Screen name="FutsalWorkspace" component={FutsalWorkspaceScreen} />
      <Stack.Screen name="FieldOps" component={FieldOpsScreen} />
    </Stack.Navigator>
  );
}
