import { useEffect, useState, useSyncExternalStore } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { AlertTriangle, CheckCircle2, Info } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/utils/cn";

export type DialogTone = "default" | "danger" | "success";

type AlertRequest = {
  kind: "alert";
  title: string;
  message: string;
  tone: DialogTone;
  confirmLabel: string;
  resolve: () => void;
};

type ConfirmRequest = {
  kind: "confirm";
  title: string;
  message: string;
  tone: DialogTone;
  confirmLabel: string;
  cancelLabel: string;
  resolve: (ok: boolean) => void;
};

type DialogRequest = AlertRequest | ConfirmRequest;

type AlertOptions = {
  title?: string;
  tone?: DialogTone;
  confirmLabel?: string;
};

type ConfirmOptions = {
  title?: string;
  tone?: DialogTone;
  confirmLabel?: string;
  cancelLabel?: string;
};

let current: DialogRequest | null = null;
const listeners = new Set<() => void>();

function emit() {
  listeners.forEach((l) => l());
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

function getSnapshot() {
  return current;
}

function enqueue(next: DialogRequest) {
  current = next;
  emit();
}

function clear() {
  current = null;
  emit();
}

/** Imperative dialog API — use instead of window.alert / window.confirm. */
export const appDialog = {
  alert(message: string, options: AlertOptions = {}): Promise<void> {
    return new Promise((resolve) => {
      enqueue({
        kind: "alert",
        title: options.title ?? (options.tone === "danger" ? "Error" : options.tone === "success" ? "Success" : "Notice"),
        message,
        tone: options.tone ?? "default",
        confirmLabel: options.confirmLabel ?? "OK",
        resolve: () => {
          clear();
          resolve();
        },
      });
    });
  },

  confirm(message: string, options: ConfirmOptions = {}): Promise<boolean> {
    return new Promise((resolve) => {
      enqueue({
        kind: "confirm",
        title: options.title ?? "Confirm",
        message,
        tone: options.tone ?? "danger",
        confirmLabel: options.confirmLabel ?? "Confirm",
        cancelLabel: options.cancelLabel ?? "Cancel",
        resolve: (ok) => {
          clear();
          resolve(ok);
        },
      });
    });
  },
};

function ToneIcon({ tone }: { tone: DialogTone }) {
  if (tone === "success") return <CheckCircle2 className="h-5 w-5" />;
  if (tone === "danger") return <AlertTriangle className="h-5 w-5" />;
  return <Info className="h-5 w-5" />;
}

/** Mount once near the app root. */
export function AppDialogHost() {
  const request = useSyncExternalStore(subscribe, getSnapshot, getSnapshot);
  const [mounted, setMounted] = useState(false);

  useEffect(() => setMounted(true), []);
  if (!mounted) return null;

  const open = Boolean(request);

  return (
    <AnimatePresence>
      {open && request && (
        <motion.div
          className="fixed inset-0 z-[100] flex items-end justify-center p-4 sm:items-center"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
        >
          <button
            type="button"
            className="absolute inset-0 bg-foreground/40 backdrop-blur-[2px]"
            aria-label="Close"
            onClick={() => {
              if (request.kind === "confirm") request.resolve(false);
              else request.resolve();
            }}
          />
          <motion.div
            role="dialog"
            aria-modal="true"
            aria-labelledby="app-dialog-title"
            initial={{ opacity: 0, y: 16, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 10, scale: 0.98 }}
            transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
            className="relative w-full max-w-md overflow-hidden rounded-2xl border border-border/70 bg-card shadow-[0_24px_64px_-20px_hsl(var(--foreground)/0.35)]"
          >
            <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-primary/50 to-transparent" />
            <div className="space-y-4 p-6">
              <div className="flex items-start gap-3">
                <div
                  className={cn(
                    "flex h-10 w-10 shrink-0 items-center justify-center rounded-xl",
                    request.tone === "danger" && "bg-destructive/10 text-destructive",
                    request.tone === "success" && "bg-emerald-500/10 text-emerald-600",
                    request.tone === "default" && "bg-primary/10 text-primary"
                  )}
                >
                  <ToneIcon tone={request.tone} />
                </div>
                <div>
                  <h3 id="app-dialog-title" className="text-base font-semibold tracking-tight">
                    {request.title}
                  </h3>
                  <p className="mt-1 whitespace-pre-wrap text-sm text-muted-foreground">{request.message}</p>
                </div>
              </div>
              <div className="flex justify-end gap-2 pt-1">
                {request.kind === "confirm" && (
                  <Button type="button" variant="secondary" onClick={() => request.resolve(false)}>
                    {request.cancelLabel}
                  </Button>
                )}
                <Button
                  type="button"
                  className={
                    request.tone === "danger"
                      ? "bg-destructive text-destructive-foreground shadow-md shadow-destructive/25 hover:bg-destructive/90"
                      : undefined
                  }
                  onClick={() => {
                    if (request.kind === "confirm") request.resolve(true);
                    else request.resolve();
                  }}
                >
                  {request.confirmLabel}
                </Button>
              </div>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
