import type { ReactNode } from "react";
import { cn } from "@/utils/cn";
import { Label } from "@/components/ui/label";

interface FormFieldProps {
  label: string;
  htmlFor?: string;
  required?: boolean;
  error?: string;
  hint?: string;
  children: ReactNode;
  className?: string;
}

export function FormField({
  label,
  htmlFor,
  required,
  error,
  hint,
  children,
  className,
}: FormFieldProps) {
  return (
    <div className={cn("space-y-2", className)}>
      <Label htmlFor={htmlFor} className="text-[13px] font-medium tracking-tight text-foreground">
        {label}
        {required && <span className="text-destructive ml-1">*</span>}
      </Label>
      {children}
      {hint && !error && <p className="text-xs text-muted-foreground">{hint}</p>}
      {error && <p className="text-xs text-destructive">{error}</p>}
    </div>
  );
}

interface FormSectionProps {
  title: string;
  description?: string;
  children: ReactNode;
  className?: string;
  variant?: "default" | "premium";
  icon?: ReactNode;
}

export function FormSection({
  title,
  description,
  children,
  className,
  variant = "default",
  icon,
}: FormSectionProps) {
  return (
    <div
      className={cn(
        variant === "premium" ? "ds-card-premium overflow-hidden" : "ds-card",
        className
      )}
    >
      <div className="border-b border-border/60 px-6 py-4">
        <div className="flex items-start gap-3">
          {icon && (
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
              {icon}
            </div>
          )}
          <div>
            <h3 className="text-[15px] font-semibold tracking-tight text-foreground">{title}</h3>
            {description && (
              <p className="mt-1 text-sm leading-relaxed text-muted-foreground">{description}</p>
            )}
          </div>
        </div>
      </div>
      <div className="p-6">{children}</div>
    </div>
  );
}

export function FormGrid({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div className={cn("grid grid-cols-1 gap-x-6 gap-y-5 md:grid-cols-2 xl:grid-cols-3", className)}>
      {children}
    </div>
  );
}

/** Use on FormField when the control should span the full form row. */
export const formFieldFullWidthClass = "md:col-span-2 xl:col-span-3";

interface FormPanelProps {
  title?: string;
  description?: string;
  children: ReactNode;
  className?: string;
}

/** Single card container for multi-section forms. */
export function FormPanel({ title, description, children, className }: FormPanelProps) {
  return (
    <div className={cn("ds-card-premium overflow-hidden", className)}>
      {(title || description) && (
        <div className="border-b border-border/60 px-6 py-5">
          {title && <h3 className="text-base font-semibold tracking-tight text-foreground">{title}</h3>}
          {description && (
            <p className="mt-1 text-sm text-muted-foreground">{description}</p>
          )}
        </div>
      )}
      <div className="divide-y divide-border/50">{children}</div>
    </div>
  );
}

interface FormPanelSectionProps {
  title: string;
  description?: string;
  icon?: ReactNode;
  children: ReactNode;
  className?: string;
}

export function FormPanelSection({
  title,
  description,
  icon,
  children,
  className,
}: FormPanelSectionProps) {
  return (
    <section className={className}>
      <div className="flex items-start gap-3 border-b border-border/40 bg-muted/10 px-6 py-4">
        {icon && (
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
            {icon}
          </div>
        )}
        <div>
          <h4 className="text-sm font-semibold tracking-tight text-foreground">{title}</h4>
          {description && (
            <p className="mt-0.5 text-xs leading-relaxed text-muted-foreground">{description}</p>
          )}
        </div>
      </div>
      <div className="p-6">{children}</div>
    </section>
  );
}
