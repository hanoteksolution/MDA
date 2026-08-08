import React, { useEffect, useState } from "react";
import { StyleSheet, Text, View } from "react-native";
import QRCode from "react-native-qrcode-svg";

import { fetchQr, type GymQr } from "@/api/gym";
import { Card, Loading, Screen } from "@/components/Screen";
import { colors } from "@/theme/colors";

export function QrScreen() {
  const [qr, setQr] = useState<GymQr | null>(null);
  const [error, setError] = useState("");

  const load = async () => {
    setError("");
    try {
      setQr(await fetchQr());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load QR");
    }
  };

  useEffect(() => {
    void load();
  }, []);

  if (!qr && !error) return <Loading />;

  return (
    <Screen title="Membership QR" onRefresh={() => void load()}>
      {error ? <Text style={styles.error}>{error}</Text> : null}
      {qr ? (
        <Card>
          <View style={styles.qrWrap}>
            <QRCode value={qr.payload} size={220} backgroundColor="#ffffff" />
          </View>
          <Text style={styles.name}>{qr.member_name}</Text>
          <Text style={styles.meta}>{qr.membership_number}</Text>
          <Text style={styles.hint}>Show this code at reception for check-in.</Text>
        </Card>
      ) : null}
    </Screen>
  );
}

const styles = StyleSheet.create({
  qrWrap: { alignItems: "center", paddingVertical: 16 },
  name: { color: colors.text, fontSize: 18, fontWeight: "700", textAlign: "center" },
  meta: { color: colors.muted, textAlign: "center" },
  hint: { color: colors.muted, textAlign: "center", marginTop: 8, fontSize: 13 },
  error: { color: colors.danger },
});
