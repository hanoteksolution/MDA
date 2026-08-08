import { createNativeStackNavigator } from "@react-navigation/native-stack";
import React from "react";

import { AttendanceScreen } from "@/screens/AttendanceScreen";
import { ClassesScreen } from "@/screens/ClassesScreen";
import { HomeScreen } from "@/screens/HomeScreen";
import { QrScreen } from "@/screens/QrScreen";
import { WorkoutsScreen } from "@/screens/WorkoutsScreen";

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
      <Stack.Screen name="Home" component={HomeScreen} />
      <Stack.Screen name="Qr" component={QrScreen} />
      <Stack.Screen name="Attendance" component={AttendanceScreen} />
      <Stack.Screen name="Workouts" component={WorkoutsScreen} />
      <Stack.Screen name="Classes" component={ClassesScreen} />
    </Stack.Navigator>
  );
}
