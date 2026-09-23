import { ChevronDown } from "lucide-react";
import { NavLink } from "react-router-dom";
import { cn } from "@/utils/cn";
import type { WorkspaceNavItem, WorkspaceNavSection } from "@/navigation/businessWorkspaces";

export function itemActive(item: Pick<WorkspaceNavItem, "to" | "end">, pathname: string): boolean {
  return item.end ? pathname === item.to : pathname === item.to || pathname.startsWith(`${item.to}/`);
}

export function sectionActive(section: WorkspaceNavSection, pathname: string): boolean {
  return section.items.some((item) => itemActive(item, pathname));
}

const linkClass = (collapsed: boolean) => ({ isActive }: { isActive: boolean }) =>
  cn(
    "group relative flex min-h-10 items-center gap-3 rounded-xl px-3 py-2 text-sm font-medium transition-all",
    collapsed && "justify-center px-2",
    isActive
      ? "bg-primary/10 text-primary shadow-sm"
      : "text-sidebar-foreground hover:bg-sidebar-accent hover:text-foreground"
  );

function ActiveMarker() {
  return <span className="absolute left-0 top-1/2 h-5 w-0.5 -translate-y-1/2 rounded-full bg-primary" />;
}

function FlatItems({ items, collapsed }: { items: WorkspaceNavItem[]; collapsed: boolean }) {
  return (
    <div className="space-y-0.5">
      {items.map(({ to, label, icon: Icon, end }) => (
        <NavLink key={`${to}-${label}`} to={to} end={end} title={label} aria-label={label} className={linkClass(collapsed)}>
          {({ isActive }) => (
            <>
              {isActive && <ActiveMarker />}
              <Icon className="h-[18px] w-[18px] shrink-0" />
              {!collapsed && <span className="truncate">{label}</span>}
            </>
          )}
        </NavLink>
      ))}
    </div>
  );
}

interface SidebarSectionProps {
  section: WorkspaceNavSection;
  collapsed: boolean;
  pathname: string;
  open: boolean;
  onToggle: () => void;
}

/** One sidebar section: a labelled flat list, or an expandable group for large modules. */
export function SidebarSection({ section, collapsed, pathname, open, onToggle }: SidebarSectionProps) {
  if (!section.collapsible) {
    return (
      <div className="mb-4 xl:mb-5">
        {!collapsed && (
          <p className="mb-1.5 px-3 text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">
            {section.label}
          </p>
        )}
        {collapsed && <div className="mx-auto mb-1.5 h-px w-6 bg-sidebar-border" aria-hidden />}
        <FlatItems items={section.items} collapsed={collapsed} />
      </div>
    );
  }

  const GroupIcon = section.icon ?? section.items[0].icon;
  const active = sectionActive(section, pathname);

  if (collapsed) {
    // Icon rail (laptop/tablet widths): one entry per group keeps the rail short.
    const target = section.items.find((item) => itemActive(item, pathname)) ?? section.items[0];
    return (
      <div className="mb-1">
        <NavLink
          to={target.to}
          end={target.end}
          title={section.label}
          aria-label={section.label}
          className={() => linkClass(true)({ isActive: active })}
        >
          {active && <ActiveMarker />}
          <GroupIcon className="h-[18px] w-[18px] shrink-0" />
        </NavLink>
      </div>
    );
  }

  const listId = `nav-group-${section.label.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`;
  return (
    <div className="mb-1">
      <button
        type="button"
        onClick={onToggle}
        aria-expanded={open}
        aria-controls={listId}
        className={cn(
          "flex min-h-10 w-full items-center gap-3 rounded-xl px-3 py-2 text-sm font-medium transition-colors",
          active ? "text-primary" : "text-sidebar-foreground hover:bg-sidebar-accent hover:text-foreground"
        )}
      >
        <GroupIcon className="h-[18px] w-[18px] shrink-0" />
        <span className="flex-1 truncate text-left">{section.label}</span>
        <ChevronDown className={cn("h-4 w-4 shrink-0 text-muted-foreground transition-transform", open && "rotate-180")} />
      </button>
      {open && (
        <div id={listId} role="group" aria-label={section.label} className="ml-5 mt-0.5 space-y-0.5 border-l border-sidebar-border pl-2">
          {section.items.map(({ to, label, end }) => (
            <NavLink
              key={`${to}-${label}`}
              to={to}
              end={end}
              className={({ isActive }) =>
                cn(
                  "flex min-h-9 items-center rounded-lg px-3 py-1.5 text-[13px] transition-colors",
                  isActive
                    ? "bg-primary/10 font-medium text-primary"
                    : "text-sidebar-foreground hover:bg-sidebar-accent hover:text-foreground"
                )
              }
            >
              <span className="truncate">{label}</span>
            </NavLink>
          ))}
        </div>
      )}
    </div>
  );
}
