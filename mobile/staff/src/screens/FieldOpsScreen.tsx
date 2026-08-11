import React, { useCallback, useEffect, useState } from "react";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";

import { fetchProjectFieldSummary, fetchProjectFieldTasks } from "@/api/erp";
import { ErrorText, Kpi, Row } from "@/components/ErpUi";
import { Screen } from "@/components/Screen";
import type { RootStackParamList } from "@/navigation/types";

type Props = NativeStackScreenProps<RootStackParamList, "FieldOps">;

export function FieldOpsScreen({ navigation }: Props) {
  const [summary, setSummary] = useState<Record<string, unknown> | null>(null);
  const [tasks, setTasks] = useState<Record<string, unknown>[]>([]);
  const [error, setError] = useState("");
  const reload = useCallback(async () => {
    setError("");
    try {
      const [nextSummary, nextTasks] = await Promise.all([fetchProjectFieldSummary(), fetchProjectFieldTasks()]);
      setSummary(nextSummary); setTasks(nextTasks);
    } catch (err) { setError(err instanceof Error ? err.message : "Failed to load field operations"); }
  }, []);
  useEffect(() => { void reload(); }, [reload]);
  return <Screen title="Field Operations" onBack={() => navigation.navigate("WorkspaceSwitcher")} onRefresh={() => void reload()}>
    <ErrorText message={error} />
    <Kpi label="Open tasks" value={String(summary?.my_open_tasks ?? "—")} />
    <Kpi label="Active projects" value={String(summary?.active_projects ?? "—")} />
    {tasks.map((task) => <Row key={String(task.id)} title={String(task.title || "Task")} subtitle={`${task.priority || ""} · ${task.status || ""}`} meta={String(task.planned_end || "")} />)}
  </Screen>;
}
