import { NavigationContainer } from "@react-navigation/native";
import { StatusBar } from "expo-status-bar";
import React from "react";

import { Loading } from "@/components/Screen";
import { AuthProvider, useAuth } from "@/context/AuthContext";
import { AppNavigator } from "@/navigation/AppNavigator";
import { LoginScreen } from "@/screens/LoginScreen";

function Root() {
  const { loading, signedIn } = useAuth();
  if (loading) return <Loading />;
  if (!signedIn) return <LoginScreen />;
  return (
    <NavigationContainer>
      <AppNavigator />
    </NavigationContainer>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <StatusBar style="light" />
      <Root />
    </AuthProvider>
  );
}
