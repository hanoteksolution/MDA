import { Search, SlidersHorizontal, Download, Printer, FileDown } from "lucide-react";
import { cn } from "@/utils/cn";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

export interface FilterOption {
  label: string;
  value: string;
}

export interface FilterConfig {
  key: string;
  label: string;
  options: FilterOption[];
  value?: string;
  onChange?: (value: string) => void;
}

interface FilterBarProps {
  searchPlaceholder?: string;
  searchValue?: string;
  onSearchChange?: (value: string) => void;
  filters?: FilterConfig[];
  onExport?: () => void;
  onPrint?: () => void;
  onPdfDownload?: () => void;
  actions?: React.ReactNode;
  className?: string;
  variant?: "standalone" | "inline";
}

export function FilterBar({
  searchPlaceholder = "Search...",
  searchValue = "",
  onSearchChange,
  filters = [],
  onExport,
  onPrint,
  onPdfDownload,
  actions,
  className,
  variant = "standalone",
}: FilterBarProps) {
  return (
    <div
      className={cn(
        "flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between",
        variant === "standalone" && "rounded-2xl border border-border/70 bg-card/80 p-4 backdrop-blur-sm",
        className
      )}
    >
      <div className="flex flex-1 flex-wrap items-center gap-3">
        {onSearchChange !== undefined && (
          <div className="relative min-w-[200px] max-w-sm flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder={searchPlaceholder}
              value={searchValue}
              onChange={(e) => onSearchChange(e.target.value)}
              className="h-10 pl-10"
            />
          </div>
        )}
        {filters.map((filter) => {
          const ALL = `__all__:${filter.key}`;
          const toSelect = (v?: string) => (v ? v : ALL);
          const fromSelect = (v: string) => (v === ALL ? "" : v);

          return (
            <Select
              key={filter.key}
              value={toSelect(filter.value)}
              onValueChange={(v) => filter.onChange?.(fromSelect(v))}
            >
              <SelectTrigger className="h-10 w-[160px]">
                <SlidersHorizontal className="mr-2 h-3.5 w-3.5 text-muted-foreground" />
                <SelectValue placeholder={filter.label} />
              </SelectTrigger>
              <SelectContent>
                {filter.options.map((opt) => (
                  <SelectItem key={toSelect(opt.value)} value={toSelect(opt.value)}>
                    {opt.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          );
        })}
      </div>
      <div className="flex flex-wrap items-center gap-2">
        {onPrint && (
          <Button variant="secondary" size="sm" onClick={onPrint}>
            <Printer className="h-4 w-4" />
            Print
          </Button>
        )}
        {onPdfDownload && (
          <Button variant="secondary" size="sm" onClick={onPdfDownload}>
            <FileDown className="h-4 w-4" />
            PDF
          </Button>
        )}
        {onExport && (
          <Button variant="secondary" size="sm" onClick={onExport}>
            <Download className="h-4 w-4" />
            CSV
          </Button>
        )}
        {actions}
      </div>
    </div>
  );
}
