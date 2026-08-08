import React, { useState } from "react";
import {
  KeyboardAvoidingView,
  Platform,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";

import { DEFAULT_TENANT_SLUG } from "@/config/env";
import { useAuth } from "@/context/AuthContext";
import { colors } from "@/theme/colors";

export function LoginScreen() {
  const { signIn } = useAuth();
  const [tenantSlug, setTenantSlug] = useState(DEFAULT_TENANT_SLUG);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const onSubmit = async () => {
    setError("");
    setBusy(true);
    try {
      await signIn(tenantSlug.trim(), username.trim(), password);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <KeyboardAvoidingView
      style={styles.root}
      behavior={Platform.OS === "ios" ? "padding" : undefined}
    >
      <View style={styles.panel}>
        <Text style={styles.brand}>MDA Staff</Text>
        <Text style={styles.subtitle}>Module workspaces</Text>
        <TextInput
          style={styles.input}
          placeholder="Business slug"
          placeholderTextColor={colors.muted}
          autoCapitalize="none"
          value={tenantSlug}
          onChangeText={setTenantSlug}
        />
        <TextInput
          style={styles.input}
          placeholder="Username"
          placeholderTextColor={colors.muted}
          autoCapitalize="none"
          value={username}
          onChangeText={setUsername}
        />
        <TextInput
          style={styles.input}
          placeholder="Password"
          placeholderTextColor={colors.muted}
          secureTextEntry
          value={password}
          onChangeText={setPassword}
        />
        {error ? <Text style={styles.error}>{error}</Text> : null}
        <Pressable style={styles.button} onPress={() => void onSubmit()} disabled={busy}>
          <Text style={styles.buttonText}>{busy ? "Signing in…" : "Sign in"}</Text>
        </Pressable>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.bg, justifyContent: "center", padding: 24 },
  panel: { gap: 12 },
  brand: { color: colors.text, fontSize: 32, fontWeight: "800" },
  subtitle: { color: colors.muted, marginBottom: 12 },
  input: {
    backgroundColor: colors.card,
    borderColor: colors.border,
    borderWidth: 1,
    borderRadius: 10,
    color: colors.text,
    paddingHorizontal: 14,
    paddingVertical: 12,
    fontSize: 16,
  },
  button: {
    backgroundColor: colors.accent,
    borderRadius: 10,
    paddingVertical: 14,
    alignItems: "center",
    marginTop: 8,
  },
  buttonText: { color: colors.bg, fontWeight: "700", fontSize: 16 },
  error: { color: colors.danger },
});
