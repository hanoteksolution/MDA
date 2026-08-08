import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  ArrowRight,
  Command,
  FileText,
  LayoutGrid,
  Moon,
  Package,
  Search,
  Sun,
  Users,
  Zap,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import type { HubQuickAction, ModuleWorkspace } from "@/navigation/moduleWorkspaces";
import { TONE_STYLES } from "@/navigation/moduleWorkspaces";
import { productsApi } from "@/services/api/catalog";
import { customersApi } from "@/services/api/partners";
import { salesApi } from "@/services/api/sales";
import { gymApi } from "@/services/api/gym";
import { useUIStore } from "@/store/uiStore";
import { cn } from "@/utils/cn";
import { recordHubVisit } from "./hubStorage";

interface HubCommandSearchProps {
  open: boolean;
  onClose: () => void;
  workspaces: ModuleWorkspace[];
  quickActions: HubQuickAction[];
  onOpenWorkspace: (code: string, route: string) => void;
}

type HitKind = "workspace" | "page" | "action" | "customer" | "product" | "invoice" | "member" | "command";

interface SearchHit {
  id: string;
  kind: HitKind;
  title: string;
  subtitle?: string;
  route: string;
  workspace?: string;
}

const KIND_LABEL: Record<HitKind, string> = {
  workspace: "Workspace",
  page: "Page",
  action: "Action",
  customer: "Customer",
  product: "Product",
  invoice: "Invoice",
  member: "Member",
  command: "Command",
};

export function HubCommandSearch({
  open,
  onClose,
  workspaces,
  quickActions,
  onOpenWorkspace,
}: HubCommandSearchProps) {
  const navigate = useNavigate();
  const toggleDarkMode = useUIStore((s) => s.toggleDarkMode);
  const darkMode = useUIStore((s) => s.darkMode);
  const [query, setQuery] = useState("");
  const [active, setActive] = useState(0);
  const [remote, setRemote] = useState<SearchHit[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!open) {
      setQuery("");
      setRemote([]);
      setActive(0);
      return;
    }
    const t = window.setTimeout(() => inputRef.current?.focus(), 30);
    return () => window.clearTimeout(t);
  }, [open]);

  const localHits = useMemo(() => {
    const q = query.trim().toLowerCase();
    const hits: SearchHit[] = [];

    workspaces.forEach((w) => {
      const hay = [w.label, w.description, ...w.pages].join(" ").toLowerCase();
      if (!q || hay.includes(q) || w.code.includes(q)) {
        hits.push({
          id: `ws-${w.code}`,
          kind: "workspace",
          title: w.label,
          subtitle: w.description,
          route: w.route,
          workspace: w.code,
        });
      }
      w.pages.forEach((page) => {
        if (q && page.toLowerCase().includes(q)) {
          hits.push({
            id: `page-${w.code}-${page}`,
            kind: "page",
            title: page,
            subtitle: w.label,
            route: w.route,
            workspace: w.code,
          });
        }
      });
    });

    quickActions.forEach((a) => {
      if (!q || a.label.toLowerCase().includes(q)) {
        hits.push({
          id: `act-${a.id}`,
          kind: "action",
          title: a.label,
          subtitle: "Quick action",
          route: a.route,
        });
      }
    });

    const commands: SearchHit[] = [
      {
        id: "cmd-theme",
        kind: "command",
        title: darkMode ? "Switch to light mode" : "Switch to dark mode",
        subtitle: "Appearance",
        route: "__theme__",
      },
      {
        id: "cmd-modules",
        kind: "command",
        title: "All workspaces",
        subtitle: "Hub",
        route: "/modules",
      },
    ];
    commands.forEach((c) => {
      if (!q || c.title.toLowerCase().includes(q) || (c.subtitle || "").toLowerCase().includes(q)) {
        hits.push(c);
      }
    });

    if (!q) return hits.slice(0, 12);
    return hits.slice(0, 20);
  }, [query, workspaces, quickActions, darkMode]);

  useEffect(() => {
    if (!open) return;
    const q = query.trim();
    if (q.length < 2) {
      setRemote([]);
      return;
    }
    let cancelled = false;
    const timer = window.setTimeout(async () => {
      const [products, customers, invoices, members] = await Promise.allSettled([
        productsApi.search(q, { limit: 5 }).catch(() => null),
        customersApi.list({ search: q, page_size: 5 }).catch(() => null),
        salesApi.invoices({ search: q, page_size: 5 }).catch(() => null),
        workspaces.some((w) => w.code === "gym")
          ? gymApi.members({ search: q, page_size: 5 }).catch(() => null)
          : Promise.resolve(null),
      ]);
      if (cancelled) return;
      const hits: SearchHit[] = [];
      const prod = products.status === "fulfilled" ? products.value?.data : null;
      (Array.isArray(prod) ? prod : []).forEach((p) => {
        hits.push({
          id: `prod-${p.id}`,
          kind: "product",
          title: p.name,
          subtitle: p.sku,
          route: `/products/${p.id}/edit`,
        });
      });
      const cust = customers.status === "fulfilled" ? customers.value?.data?.results : null;
      (cust ?? []).forEach((c) => {
        hits.push({
          id: `cust-${c.id}`,
          kind: "customer",
          title: c.full_name,
          subtitle: c.customer_code,
          route: `/customers/${c.id}/edit`,
        });
      });
      const inv = invoices.status === "fulfilled" ? invoices.value?.data?.results : null;
      (inv ?? []).forEach((i) => {
        hits.push({
          id: `inv-${i.id}`,
          kind: "invoice",
          title: i.number,
          subtitle: i.customer_name,
          route: `/sales/invoices/${i.id}/edit`,
        });
      });
      const mem = members.status === "fulfilled" ? members.value?.data?.results : null;
      (mem ?? []).forEach((m) => {
        hits.push({
          id: `mem-${m.id}`,
          kind: "member",
          title: m.full_name,
          subtitle: m.membership_number,
          route: "/gym",
          workspace: "gym",
        });
      });
      setRemote(hits);
    }, 220);
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [query, open, workspaces]);

  const hits = useMemo(() => {
    const seen = new Set<string>();
    const all = [...localHits, ...remote];
    return all.filter((h) => {
      if (seen.has(h.id)) return false;
      seen.add(h.id);
      return true;
    });
  }, [localHits, remote]);

  useEffect(() => {
    setActive(0);
  }, [query, remote.length]);

  const run = (hit: SearchHit) => {
    if (hit.route === "__theme__") {
      toggleDarkMode();
      onClose();
      return;
    }
    if (hit.workspace) {
      onOpenWorkspace(hit.workspace, hit.route);
    } else {
      if (hit.route.startsWith("/")) navigate(hit.route);
    }
    onClose();
  };

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        onClose();
      } else if (e.key === "ArrowDown") {
        e.preventDefault();
        setActive((i) => Math.min(hits.length - 1, i + 1));
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setActive((i) => Math.max(0, i - 1));
      } else if (e.key === "Enter" && hits[active]) {
        e.preventDefault();
        run(hits[active]);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, hits, active, onClose]);

  const iconFor = (kind: HitKind) => {
    switch (kind) {
      case "workspace":
        return LayoutGrid;
      case "action":
        return Zap;
      case "product":
        return Package;
      case "customer":
      case "member":
        return Users;
      case "invoice":
        return FileText;
      case "command":
        return darkMode ? Sun : Moon;
      default:
        return ArrowRight;
    }
  };

  return (
    <AnimatePresence>
      {open ? (
        <div className="fixed inset-0 z-[80] flex items-start justify-center px-4 pt-[12vh]">
          <motion.button
            type="button"
            aria-label="Close search"
            className="absolute inset-0 bg-black/45 backdrop-blur-sm"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
          />
          <motion.div
            role="dialog"
            aria-label="Global search"
            initial={{ opacity: 0, y: 12, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 8, scale: 0.98 }}
            transition={{ duration: 0.18 }}
            className="hub-glass relative z-[81] w-full max-w-2xl overflow-hidden rounded-2xl shadow-2xl"
          >
            <div className="flex items-center gap-3 border-b border-border/70 px-4 py-3">
              <Search className="h-5 w-5 text-muted-foreground" />
              <input
                ref={inputRef}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search modules, customers, invoices, products…"
                className="h-10 min-w-0 flex-1 bg-transparent text-base outline-none placeholder:text-muted-foreground"
                aria-label="Search anything"
              />
              <kbd className="hidden items-center gap-1 rounded-md border border-border bg-muted/60 px-1.5 py-0.5 text-[10px] text-muted-foreground sm:inline-flex">
                <Command className="h-3 w-3" />K
              </kbd>
            </div>
            <ul className="max-h-[55vh] overflow-y-auto p-2 scrollbar-thin">
              {hits.length === 0 ? (
                <li className="px-3 py-10 text-center text-sm text-muted-foreground">No matches.</li>
              ) : (
                hits.map((hit, i) => {
                  const Icon = iconFor(hit.kind);
                  const ws = workspaces.find((w) => w.code === hit.workspace);
                  const tone = ws ? TONE_STYLES[ws.tone] : TONE_STYLES.slate;
                  return (
                    <li key={hit.id}>
                      <button
                        type="button"
                        onMouseEnter={() => setActive(i)}
                        onClick={() => {
                          if (hit.workspace) recordHubVisit(hit.workspace);
                          run(hit);
                        }}
                        className={cn(
                          "flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left transition-colors",
                          i === active ? "bg-muted/80" : "hover:bg-muted/50"
                        )}
                      >
                        <span className={cn("flex h-9 w-9 shrink-0 items-center justify-center rounded-xl", tone.accent)}>
                          <Icon className="h-4 w-4" />
                        </span>
                        <span className="min-w-0 flex-1">
                          <span className="block truncate text-sm font-medium">{hit.title}</span>
                          {hit.subtitle ? (
                            <span className="block truncate text-xs text-muted-foreground">{hit.subtitle}</span>
                          ) : null}
                        </span>
                        <span className="shrink-0 rounded-full bg-muted px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
                          {KIND_LABEL[hit.kind]}
                        </span>
                      </button>
                    </li>
                  );
                })
              )}
            </ul>
          </motion.div>
        </div>
      ) : null}
    </AnimatePresence>
  );
}
