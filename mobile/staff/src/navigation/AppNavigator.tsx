import { createNativeStackNavigator } from "@react-navigation/native-stack";
import React from "react";

import { GymWorkspaceScreen } from "@/screens/GymWorkspaceScreen";
import { HotelWorkspaceScreen } from "@/screens/HotelWorkspaceScreen";
import { HousingWorkspaceScreen } from "@/screens/HousingWorkspaceScreen";
import { OfficeWorkspaceScreen } from "@/screens/OfficeWorkspaceScreen";
import { PharmacyWorkspaceScreen } from "@/screens/PharmacyWorkspaceScreen";
import { PropertyWorkspaceScreen } from "@/screens/PropertyWorkspaceScreen";
import { RestaurantWorkspaceScreen } from "@/screens/RestaurantWorkspaceScreen";
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
      <Stack.Screen name="GymWorkspace" component={GymWorkspaceScreen} />
      <Stack.Screen name="PharmacyWorkspace" component={PharmacyWorkspaceScreen} />
      <Stack.Screen name="HotelWorkspace" component={HotelWorkspaceScreen} />
      <Stack.Screen name="RestaurantWorkspace" component={RestaurantWorkspaceScreen} />
      <Stack.Screen name="PropertyWorkspace" component={PropertyWorkspaceScreen} />
      <Stack.Screen name="HousingWorkspace" component={HousingWorkspaceScreen} />
      <Stack.Screen name="OfficeWorkspace" component={OfficeWorkspaceScreen} />
    </Stack.Navigator>
  );
}
