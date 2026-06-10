import { Bell, Moon, Sun, Search, ChevronDown } from "lucide-react";
import { useUIStore } from "@/store/uiStore";
import { useAuthStore } from "@/store/authStore";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";

export function Header() {
  const { darkMode, toggleDarkMode } = useUIStore();
  const user = useAuthStore((s) => s.user);

  return (
    <header className="flex h-[72px] shrink-0 items-center gap-6 border-b border-border bg-card px-6">
      <div className="relative flex-1 max-w-xl">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          type="search"
          placeholder="Search products, customers, invoices..."
          className="h-10 pl-10 bg-muted/50 border-transparent focus:border-input"
        />
        <kbd className="absolute right-3 top-1/2 -translate-y-1/2 hidden lg:inline-flex h-5 items-center rounded border border-border bg-background px-1.5 text-[10px] text-muted-foreground">
          ⌘K
        </kbd>
      </div>

      <div className="flex items-center gap-2">
        {user?.branch && (
          <button className="hidden sm:flex items-center gap-2 rounded-xl border border-border bg-background px-3 py-2 text-sm hover:bg-muted/50 transition-colors">
            <span className="text-muted-foreground">Branch</span>
            <span className="font-medium text-foreground">{user.branch.name}</span>
            <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
          </button>
        )}

        <button className="relative rounded-xl p-2.5 text-muted-foreground hover:bg-muted hover:text-foreground transition-colors">
          <Bell className="h-[18px] w-[18px]" />
          <Badge className="absolute -right-0.5 -top-0.5 h-4 w-4 p-0 flex items-center justify-center text-[10px]">
            3
          </Badge>
        </button>

        <button
          onClick={toggleDarkMode}
          className="rounded-xl p-2.5 text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
        >
          {darkMode ? <Sun className="h-[18px] w-[18px]" /> : <Moon className="h-[18px] w-[18px]" />}
        </button>

        <div className="hidden sm:flex items-center gap-2.5 pl-2 ml-1 border-l border-border">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary/10 text-primary text-sm font-semibold">
            {user?.username?.[0]?.toUpperCase() || "U"}
          </div>
          <div className="hidden lg:block">
            <p className="text-sm font-medium text-foreground leading-none">
              {user?.first_name || user?.username}
            </p>
            <p className="text-xs text-muted-foreground mt-0.5">{user?.role?.name}</p>
          </div>
        </div>
      </div>
    </header>
  );
}
