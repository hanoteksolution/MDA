import { useCallback, useEffect, useState } from "react";
import { Coffee, RefreshCw } from "lucide-react";
import { PageLayout } from "@/components/layout/PageLayout";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useAuthStore } from "@/store/authStore";
import {
  restaurantApi,
  type BaristaQueue,
  type BaristaTicket,
} from "@/services/api/restaurant";

function formatElapsed(seconds: number) {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

function urgencyClass(seconds: number, priority: string) {
  if (priority === "rush" || seconds > 900) return "border-amber-700/40 bg-amber-50/80";
  if (seconds > 480) return "border-amber-500/30 bg-amber-50/40";
  return "border-border/70 bg-background";
}

function TicketCard({
  ticket,
  onAction,
  busy,
}: {
  ticket: BaristaTicket;
  onAction: (id: string, action: "accept" | "start" | "ready" | "complete") => void;
  busy: string | null;
}) {
  const actions =
    ticket.board_column === "NEW"
      ? (["accept", "start"] as const)
      : ticket.board_column === "PREPARING"
        ? (["ready"] as const)
        : (["complete"] as const);

  return (
    <article
      className={`rounded-xl border p-4 shadow-sm transition ${urgencyClass(
        ticket.elapsed_seconds,
        ticket.priority
      )}`}
    >
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="text-lg font-semibold tracking-tight">{ticket.order_number}</p>
          {ticket.queue_number ? (
            <p className="text-sm text-muted-foreground">Queue #{ticket.queue_number}</p>
          ) : null}
        </div>
        <div className="text-right">
          <Badge variant="secondary">{formatElapsed(ticket.elapsed_seconds)}</Badge>
          {ticket.priority !== "normal" ? (
            <p className="mt-1 text-xs uppercase text-amber-800">{ticket.priority}</p>
          ) : null}
        </div>
      </div>
      <p className="mt-2 text-sm text-muted-foreground">
        {ticket.service_type.replace("_", " ")}
        {ticket.waiter_name ? ` · ${ticket.waiter_name}` : ""}
      </p>
      <ul className="mt-3 space-y-1.5">
        {ticket.lines.map((line) => (
          <li key={line.id} className="text-sm">
            <span className="font-medium">
              {line.quantity}× {line.name}
            </span>
            {line.modifiers?.length ? (
              <span className="block text-xs text-muted-foreground">
                {line.modifiers.map((m) => m.name).join(", ")}
              </span>
            ) : null}
            {line.notes ? (
              <span className="block text-xs italic text-muted-foreground">{line.notes}</span>
            ) : null}
          </li>
        ))}
      </ul>
      <div className="mt-4 flex flex-wrap gap-2">
        {actions.map((action) => (
          <Button
            key={action}
            size="sm"
            className="min-w-[5.5rem]"
            disabled={busy === ticket.id}
            onClick={() => onAction(ticket.id, action)}
          >
            {action.charAt(0).toUpperCase() + action.slice(1)}
          </Button>
        ))}
      </div>
    </article>
  );
}

export function BaristaBoardPage() {
  const branchId = useAuthStore((s) => s.user?.branch?.id);
  const [queue, setQueue] = useState<BaristaQueue | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    if (!branchId) return;
    setLoading(true);
    setError(null);
    try {
      const res = await restaurantApi.baristaQueue(branchId);
      setQueue(res.data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load barista queue");
    } finally {
      setLoading(false);
    }
  }, [branchId]);

  useEffect(() => {
    void reload();
    const id = window.setInterval(() => void reload(), 15000);
    return () => window.clearInterval(id);
  }, [reload]);

  const onAction = async (
    orderId: string,
    action: "accept" | "start" | "ready" | "complete"
  ) => {
    setBusy(orderId);
    try {
      await restaurantApi.baristaAction(orderId, action);
      await reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Action failed");
    } finally {
      setBusy(null);
    }
  };

  const columns = [
    { key: "NEW" as const, title: "New", hint: "Accept & start prep" },
    { key: "PREPARING" as const, title: "Preparing", hint: "In progress" },
    { key: "READY" as const, title: "Ready", hint: "Serve / pick up" },
  ];

  return (
    <PageLayout
      title="Barista Queue"
      description="Touch-friendly preparation board for coffee and café stations."
      actions={
        <Button variant="outline" onClick={() => void reload()} disabled={loading}>
          <RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </Button>
      }
    >
      {error ? (
        <p className="mb-4 rounded-lg border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive">
          {error}
        </p>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-3">
        {columns.map((col) => {
          const tickets = queue?.columns?.[col.key] ?? [];
          return (
            <section key={col.key} className="min-h-[20rem] rounded-2xl border border-border/60 bg-muted/20 p-3">
              <header className="mb-3 flex items-center justify-between px-1">
                <div>
                  <h2 className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wide">
                    <Coffee className="h-4 w-4 text-amber-800" />
                    {col.title}
                  </h2>
                  <p className="text-xs text-muted-foreground">{col.hint}</p>
                </div>
                <Badge variant="outline">{tickets.length}</Badge>
              </header>
              <div className="space-y-3">
                {tickets.length === 0 ? (
                  <p className="px-2 py-8 text-center text-sm text-muted-foreground">
                    {loading ? "Loading…" : "No tickets"}
                  </p>
                ) : (
                  tickets.map((t) => (
                    <TicketCard key={t.id} ticket={t} onAction={onAction} busy={busy} />
                  ))
                )}
              </div>
            </section>
          );
        })}
      </div>
    </PageLayout>
  );
}
