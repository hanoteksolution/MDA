import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowUpRight } from "lucide-react";
import { cn } from "@/utils/cn";

export interface QuickAction {
  label: string;
  description?: string;
  icon: ReactNode;
  to?: string;
  onClick?: () => void;
  variant?: "default" | "primary";
}

interface QuickActionsProps {
  actions: QuickAction[];
  className?: string;
}

export function QuickActions({ actions, className }: QuickActionsProps) {
  return (
    <div className={cn("grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4", className)}>
      {actions.map((action, index) => {
        const content = (
          <>
            <div
              className={cn(
                "flex h-11 w-11 items-center justify-center rounded-xl transition-transform duration-300 group-hover:scale-105",
                action.variant === "primary"
                  ? "bg-gradient-to-br from-primary to-emerald-600 text-primary-foreground shadow-lg shadow-primary/25"
                  : "bg-primary/10 text-primary"
              )}
            >
              {action.icon}
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-semibold text-foreground">{action.label}</p>
              {action.description && (
                <p className="mt-0.5 text-xs text-muted-foreground">{action.description}</p>
              )}
            </div>
            <ArrowUpRight className="h-4 w-4 shrink-0 text-muted-foreground opacity-0 transition-all group-hover:translate-x-0.5 group-hover:-translate-y-0.5 group-hover:opacity-100" />
          </>
        );

        const classNames = cn(
          "group flex items-center gap-4 rounded-xl border border-border/70 bg-card/80 p-4 backdrop-blur-sm transition-all duration-300",
          "hover:border-primary/30 hover:bg-accent/40 hover:shadow-elevated"
        );

        const motionProps = {
          initial: { opacity: 0, y: 12 } as const,
          animate: { opacity: 1, y: 0 } as const,
          transition: { duration: 0.35, delay: index * 0.05 },
          whileHover: { y: -2 } as const,
        };

        if (action.to) {
          return (
            <motion.div key={action.label} {...motionProps}>
              <Link to={action.to} className={classNames}>
                {content}
              </Link>
            </motion.div>
          );
        }

        return (
          <motion.button
            key={action.label}
            type="button"
            onClick={action.onClick}
            className={cn(classNames, "w-full text-left")}
            {...motionProps}
          >
            {content}
          </motion.button>
        );
      })}
    </div>
  );
}
