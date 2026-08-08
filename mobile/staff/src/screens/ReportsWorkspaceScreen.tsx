import React, { useCallback, useEffect, useState } from "react";
import { Text } from "react-native";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";

import { fetchReportCatalog, fetchReportData, money } from "@/api/erp";
import { Screen } from "@/components/Screen";
import { ErrorText, Row } from "@/components/ErpUi";
import type { RootStackParamList } from "@/navigation/types";
import { colors } from "@/theme/colors";

type Props = NativeStackScreenProps<RootStackParamList, "ReportsWorkspace">;

export function ReportsWorkspaceScreen({ navigation }: Props) {
  const [packs, setPacks] = useState<Record<string, unknown>[]>([]);
  const [active, setActive] = useState<{ category: string; report: string } | null>(null);
  const [rows, setRows] = useState<Record<string, unknown>[]>([]);
  const [columns, setColumns] = useState<string[]>([]);
  const [error, setError] = useState("");

  const reload = useCallback(async () => {
    setError("");
    try {
      const catalog = await fetchReportCatalog();
      setPacks(Array.isArray(catalog) ? catalog : []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load reports");
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  const run = async (category: string, report: string) => {
    setError("");
    setActive({ category, report });
    try {
      const data = await fetchReportData(category, report);
      const cols = (data.columns as string[]) || [];
      const table = (data.rows as Record<string, unknown>[]) || [];
      setColumns(cols);
      setRows(table);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Report failed");
    }
  };

  return (
    <Screen title="Reports" onRefresh={() => void reload()} onBack={() => navigation.navigate("WorkspaceSwitcher")}>
      <ErrorText message={error} />
      {packs.map((pack) => (
        <React.Fragment key={String(pack.id)}>
          <Text style={{ color: colors.text, fontWeight: "700", marginTop: 8 }}>{String(pack.title)}</Text>
          <Text style={{ color: colors.muted }}>{String(pack.description || "")}</Text>
          {((pack.reports as string[]) || []).map((report) => (
            <Row
              key={`${pack.id}-${report}`}
              title={report}
              subtitle={active?.report === report ? "loaded" : "tap to run"}
              onPress={() => void run(String(pack.id), report)}
            />
          ))}
        </React.Fragment>
      ))}
      {active && rows.length ? (
        <>
          <Text style={{ color: colors.muted, fontWeight: "700", marginTop: 12 }}>
            {active.report}
          </Text>
          {rows.slice(0, 20).map((row, i) => {
            const title = String(row[columns[0]] ?? row.name ?? row.customer ?? row.product ?? `Row ${i + 1}`);
            const metaKey = columns.find((c) => /amount|total|revenue|value|qty|sold/i.test(c));
            return (
              <Row
                key={i}
                title={title}
                subtitle={columns.slice(1, 3).map((c) => String(row[c] ?? "")).join(" · ")}
                meta={metaKey ? money(row[metaKey]) : undefined}
              />
            );
          })}
        </>
      ) : null}
    </Screen>
  );
}
