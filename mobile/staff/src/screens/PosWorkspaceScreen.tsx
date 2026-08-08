import React, { useCallback, useMemo, useState } from "react";
import { Pressable, StyleSheet, Text, TextInput, View } from "react-native";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";

import { money, posCheckout, searchProducts } from "@/api/erp";
import { Screen } from "@/components/Screen";
import { ErrorText, Row } from "@/components/ErpUi";
import type { RootStackParamList } from "@/navigation/types";
import { colors } from "@/theme/colors";

type Props = NativeStackScreenProps<RootStackParamList, "PosWorkspace">;

interface CartLine {
  id: string;
  name: string;
  sku: string;
  price: number;
  qty: number;
}

export function PosWorkspaceScreen({ navigation }: Props) {
  const [query, setQuery] = useState("");
  const [products, setProducts] = useState<Record<string, unknown>[]>([]);
  const [cart, setCart] = useState<CartLine[]>([]);
  const [error, setError] = useState("");
  const [receipt, setReceipt] = useState("");
  const [busy, setBusy] = useState(false);

  const loadProducts = useCallback(async (q: string) => {
    setError("");
    try {
      const rows = await searchProducts(q);
      setProducts(Array.isArray(rows) ? rows : []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Product search failed");
    }
  }, []);

  const add = (p: Record<string, unknown>) => {
    const id = String(p.id);
    const price = Number(p.selling_price ?? 0);
    setCart((prev) => {
      const existing = prev.find((l) => l.id === id);
      if (existing) return prev.map((l) => (l.id === id ? { ...l, qty: l.qty + 1 } : l));
      return [...prev, { id, name: String(p.name || "Item"), sku: String(p.sku || ""), price, qty: 1 }];
    });
  };

  const total = useMemo(() => cart.reduce((s, l) => s + l.price * l.qty, 0), [cart]);

  const checkout = async () => {
    if (!cart.length) return;
    setBusy(true);
    setError("");
    try {
      const res = await posCheckout({
        items: cart.map((l) => ({ product_id: l.id, quantity: l.qty, unit_price: l.price })),
        payment_method: "cash",
        amount_tendered: total,
        idempotency_key: `pos-mobile-${Date.now()}`,
      });
      const rec = (res.receipt ?? res) as Record<string, unknown>;
      setReceipt(String(rec.invoice_number || rec.invoice_id || "Sale complete"));
      setCart([]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Checkout failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Screen title="POS" onRefresh={() => void loadProducts(query)} onBack={() => navigation.navigate("WorkspaceSwitcher")}>
      <ErrorText message={error} />
      {receipt ? <Text style={styles.ok}>Receipt {receipt}</Text> : null}
      <TextInput
        style={styles.input}
        placeholder="Search products / barcode"
        placeholderTextColor={colors.muted}
        value={query}
        onChangeText={setQuery}
        onSubmitEditing={() => void loadProducts(query)}
        autoCapitalize="none"
      />
      <Pressable style={styles.btn} onPress={() => void loadProducts(query)}>
        <Text style={styles.btnText}>Search</Text>
      </Pressable>

      {products.map((p) => (
        <Row
          key={String(p.id)}
          title={String(p.name || "Product")}
          subtitle={`${p.sku || ""} · stock ${p.total_stock ?? p.available_quantity ?? "—"}`}
          meta={money(p.selling_price)}
          onPress={() => add(p)}
        />
      ))}

      <Text style={styles.section}>Cart · {money(total)}</Text>
      {cart.map((l) => (
        <Row key={l.id} title={`${l.name} × ${l.qty}`} subtitle={l.sku} meta={money(l.price * l.qty)} />
      ))}
      <View style={{ flexDirection: "row", gap: 8 }}>
        <Pressable style={[styles.btn, { flex: 1, backgroundColor: colors.card }]} onPress={() => setCart([])}>
          <Text style={[styles.btnText, { color: colors.text }]}>Clear</Text>
        </Pressable>
        <Pressable
          style={[styles.btn, { flex: 1, opacity: cart.length && !busy ? 1 : 0.5 }]}
          disabled={!cart.length || busy}
          onPress={() => void checkout()}
        >
          <Text style={styles.btnText}>{busy ? "Charging…" : `Cash ${money(total)}`}</Text>
        </Pressable>
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  input: {
    backgroundColor: colors.card,
    borderColor: colors.border,
    borderWidth: 1,
    borderRadius: 10,
    color: colors.text,
    paddingHorizontal: 14,
    paddingVertical: 12,
  },
  btn: { backgroundColor: colors.accent, borderRadius: 10, paddingVertical: 12, alignItems: "center" },
  btnText: { color: colors.bg, fontWeight: "700" },
  section: { color: colors.muted, fontWeight: "700", marginTop: 8 },
  ok: { color: colors.success, fontWeight: "700" },
});
