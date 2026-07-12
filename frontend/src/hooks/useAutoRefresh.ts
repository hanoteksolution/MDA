import { useEffect, useEffectEvent } from "react";

export const DATA_REFRESH_EVENT = "mda:data-refresh";

export type UseAutoRefreshOptions = {
  /** Poll interval in ms. Default 30_000. Set 0 to disable polling. */
  intervalMs?: number;
  /** Refresh when the tab becomes visible again. Default true. */
  onVisible?: boolean;
  /** Refresh when the window gains focus. Default true. */
  onFocus?: boolean;
  /** When false, auto-refresh is paused. Default true. */
  enabled?: boolean;
};

/**
 * Calls `onRefresh` on an interval and when the user returns to the tab/window.
 * Skips ticks while the document is hidden.
 */
export function useAutoRefresh(
  onRefresh: () => void | Promise<void>,
  options: UseAutoRefreshOptions = {}
) {
  const {
    intervalMs = 30_000,
    onVisible = true,
    onFocus = true,
    enabled = true,
  } = options;

  const refresh = useEffectEvent(() => {
    if (!enabled) return;
    if (typeof document !== "undefined" && document.visibilityState === "hidden") return;
    void onRefresh();
  });

  useEffect(() => {
    if (!enabled) return;

    const onVisibility = () => {
      if (onVisible && document.visibilityState === "visible") refresh();
    };
    const onWindowFocus = () => {
      if (onFocus) refresh();
    };
    const onGlobal = () => refresh();

    if (onVisible) document.addEventListener("visibilitychange", onVisibility);
    if (onFocus) window.addEventListener("focus", onWindowFocus);
    window.addEventListener(DATA_REFRESH_EVENT, onGlobal);

    let timer: number | undefined;
    if (intervalMs > 0) {
      timer = window.setInterval(() => refresh(), intervalMs);
    }

    return () => {
      if (onVisible) document.removeEventListener("visibilitychange", onVisibility);
      if (onFocus) window.removeEventListener("focus", onWindowFocus);
      window.removeEventListener(DATA_REFRESH_EVENT, onGlobal);
      if (timer) window.clearInterval(timer);
    };
  }, [enabled, intervalMs, onVisible, onFocus, refresh]);
}

/** Ask every mounted auto-refresh subscriber to reload now. */
export function requestDataRefresh() {
  window.dispatchEvent(new Event(DATA_REFRESH_EVENT));
}
