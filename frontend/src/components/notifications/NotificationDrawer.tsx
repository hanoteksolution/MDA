import { useCallback, useEffect, useState } from "react";
import { Bell, CheckCheck, Loader2, Package, Pill, Dumbbell, X } from "lucide-react";
import { notificationsApi, type NotificationItem } from "@/services/api/notifications";
import { useUIStore } from "@/store/uiStore";
import { cn } from "@/utils/cn";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

function typeIcon(type: string) {
  switch (type) {
    case "low_stock":
      return Package;
    case "gym_membership_expiry":
      return Dumbbell;
    case "pharmacy_batch_expiry":
      return Pill;
    default:
      return Bell;
  }
}

function formatWhen(iso: string) {
  try {
    const d = new Date(iso);
    const now = new Date();
    const diffMs = now.getTime() - d.getTime();
    const mins = Math.floor(diffMs / 60000);
    if (mins < 1) return "Just now";
    if (mins < 60) return `${mins}m ago`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `${hours}h ago`;
    return d.toLocaleDateString();
  } catch {
    return "";
  }
}

export function NotificationDrawer() {
  const open = useUIStore((s) => s.notificationDrawerOpen);
  const setOpen = useUIStore((s) => s.setNotificationDrawerOpen);
  const [items, setItems] = useState<NotificationItem[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(false);

  const refreshCount = useCallback(async () => {
    try {
      const res = await notificationsApi.unreadCount();
      setUnreadCount(res.data?.count ?? 0);
    } catch {
      /* ignore polling errors */
    }
  }, []);

  const loadFeed = useCallback(async () => {
    setLoading(true);
    try {
      const res = await notificationsApi.list({ page_size: 30 });
      setItems(res.data?.results ?? []);
      await refreshCount();
    } finally {
      setLoading(false);
    }
  }, [refreshCount]);

  useEffect(() => {
    refreshCount();
    const id = window.setInterval(refreshCount, 60_000);
    return () => window.clearInterval(id);
  }, [refreshCount]);

  useEffect(() => {
    if (open) loadFeed();
  }, [open, loadFeed]);

  const markRead = async (item: NotificationItem) => {
    if (item.is_read) return;
    try {
      await notificationsApi.markRead(item.id);
      setItems((prev) =>
        prev.map((n) => (n.id === item.id ? { ...n, is_read: true } : n))
      );
      setUnreadCount((c) => Math.max(0, c - 1));
    } catch {
      /* ignore */
    }
  };

  const markAllRead = async () => {
    try {
      await notificationsApi.markAllRead();
      setItems((prev) => prev.map((n) => ({ ...n, is_read: true })));
      setUnreadCount(0);
    } catch {
      /* ignore */
    }
  };

  const handleItemClick = (item: NotificationItem) => {
    void markRead(item);
    if (item.link) {
      setOpen(false);
      window.location.href = item.link;
    }
  };

  if (!open) return null;

  return (
    <>
      <button
        type="button"
        aria-label="Close notifications"
        className="fixed inset-0 z-40 bg-black/40"
        onClick={() => setOpen(false)}
      />
      <aside
        className="fixed right-0 top-0 z-50 flex h-dvh w-full max-w-md flex-col border-l border-border bg-card shadow-xl"
        role="dialog"
        aria-label="Notifications"
      >
        <div className="flex items-center justify-between border-b border-border px-4 py-3">
          <div className="flex items-center gap-2">
            <Bell className="h-5 w-5 text-primary" />
            <h2 className="text-base font-semibold">Notifications</h2>
            {unreadCount > 0 && (
              <Badge variant="secondary" className="text-xs">
                {unreadCount} unread
              </Badge>
            )}
          </div>
          <div className="flex items-center gap-1">
            {unreadCount > 0 && (
              <Button type="button" variant="ghost" size="sm" onClick={() => void markAllRead()}>
                <CheckCheck className="mr-1 h-4 w-4" />
                Mark all
              </Button>
            )}
            <button
              type="button"
              className="rounded-lg p-2 text-muted-foreground hover:bg-muted"
              onClick={() => setOpen(false)}
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto scrollbar-thin">
          {loading ? (
            <div className="flex items-center justify-center py-16 text-muted-foreground">
              <Loader2 className="mr-2 h-5 w-5 animate-spin" />
              Loading…
            </div>
          ) : items.length === 0 ? (
            <div className="px-4 py-16 text-center text-sm text-muted-foreground">
              No notifications yet.
            </div>
          ) : (
            <ul className="divide-y divide-border">
              {items.map((item) => {
                const Icon = typeIcon(item.type);
                return (
                  <li key={item.id}>
                    <button
                      type="button"
                      className={cn(
                        "flex w-full gap-3 px-4 py-3 text-left transition-colors hover:bg-muted/50",
                        !item.is_read && "bg-primary/5"
                      )}
                      onClick={() => handleItemClick(item)}
                    >
                      <div
                        className={cn(
                          "mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl",
                          item.is_read ? "bg-muted" : "bg-primary/10 text-primary"
                        )}
                      >
                        <Icon className="h-4 w-4" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="flex items-start justify-between gap-2">
                          <p className="text-sm font-medium leading-snug text-foreground">
                            {item.title}
                          </p>
                          <span className="shrink-0 text-[11px] text-muted-foreground">
                            {formatWhen(item.created_at)}
                          </span>
                        </div>
                        <p className="mt-1 line-clamp-2 text-xs text-muted-foreground">
                          {item.message}
                        </p>
                      </div>
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      </aside>
    </>
  );
}

export function NotificationBellButton() {
  const toggleOpen = useUIStore((s) => s.toggleNotificationDrawer);
  const unreadCount = useNotificationUnreadCount();

  return (
    <button
      type="button"
      onClick={toggleOpen}
      className="relative rounded-xl p-2 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
      aria-label="Open notifications"
    >
      <Bell className="h-[18px] w-[18px]" />
      {unreadCount > 0 && (
        <Badge className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center px-0.5 text-[10px]">
          {unreadCount > 99 ? "99+" : unreadCount}
        </Badge>
      )}
    </button>
  );
}

function useNotificationUnreadCount() {
  const [count, setCount] = useState(0);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const res = await notificationsApi.unreadCount();
        if (!cancelled) setCount(res.data?.count ?? 0);
      } catch {
        /* ignore */
      }
    };
    load();
    const id = window.setInterval(load, 60_000);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, []);

  return count;
}
