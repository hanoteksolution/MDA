import { Bell, Moon, Sun, Search, ChevronDown } from "lucide-react";
import { useUIStore } from "@/store/uiStore";
import { useAuthStore } from "@/store/authStore";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/utils/cn";

interface HeaderProps {
  /** Tighter chrome for POS / short laptop screens */
  compact?: boolean;
}

export function Header({ compact }: HeaderProps) {
  const { darkMode, toggleDarkMode } = useUIStore();
  const user = useAuthStore((s) => s.user);

  return (
    <header
      className={cn(
        "flex shrink-0 items-center border-b border-border bg-card",
        compact ? "h-12 gap-3 px-3 xl:h-14 xl:gap-4 xl:px-4" : "h-14 gap-4 px-4 xl:h-[72px] xl:gap-6 xl:px-6"
      )}
    >
      <div className={cn("relative min-w-0 flex-1", compact ? "max-w-md" : "max-w-xl")}>
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          type="search"
          placeholder={compact ? "Search…" : "Search products, customers, invoices..."}
          className={cn(
            "border-transparent bg-muted/50 pl-10 focus:border-input",
            compact ? "h-9" : "h-10"
          )}
        />
        <kbd className="absolute right-3 top-1/2 hidden h-5 -translate-y-1/2 items-center rounded border border-border bg-background px-1.5 text-[10px] text-muted-foreground xl:inline-flex">
          ⌘K
        </kbd>
      </div>

      <div className="flex shrink-0 items-center gap-1.5 sm:gap-2">
        {user?.branch && (
          <button
            type="button"
            className="hidden items-center gap-2 rounded-xl border border-border bg-background px-3 py-2 text-sm transition-colors hover:bg-muted/50 md:flex"
          >
            <span className="hidden text-muted-foreground xl:inline">Branch</span>
            <span className="max-w-[120px] truncate font-medium text-foreground xl:max-w-none">
              {user.branch.name}
            </span>
            <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
          </button>
        )}

        <button
          type="button"
          className="relative rounded-xl p-2 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
        >
          <Bell className="h-[18px] w-[18px]" />
          <Badge className="absolute -right-0.5 -top-0.5 flex h-4 w-4 items-center justify-center p-0 text-[10px]">
            3
          </Badge>
        </button>

        <button
          type="button"
          onClick={toggleDarkMode}
          className="rounded-xl p-2 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
        >
          {darkMode ? <Sun className="h-[18px] w-[18px]" /> : <Moon className="h-[18px] w-[18px]" />}
        </button>

        <div className="ml-1 hidden items-center gap-2.5 border-l border-border pl-2 sm:flex">
          <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-primary/10 text-sm font-semibold text-primary xl:h-9 xl:w-9">
            {user?.username?.[0]?.toUpperCase() || "U"}
          </div>
          <div className="hidden min-w-0 xl:block">
            <p className="truncate text-sm font-medium leading-none text-foreground">
              {user?.first_name || user?.username}
            </p>
            <p className="mt-0.5 truncate text-xs text-muted-foreground">{user?.role?.name}</p>
          </div>
        </div>
      </div>
    </header>
  );
}
