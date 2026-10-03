import { CheckCircle2, Loader2, XCircle } from "lucide-react";
import { Input } from "@/components/ui/input";
import { cn } from "@/utils/cn";
import type { WorkspaceAvailability, WorkspaceUrlUiState } from "./workspaceUrl";
import { workspaceHttpsUrl } from "./workspaceUrl";

const FEEDBACK: Record<
  WorkspaceUrlUiState,
  { tone: string; message: (hostname: string) => string } | null
> = {
  empty: null,
  checking: {
    tone: "text-muted-foreground",
    message: () => "Checking availability…",
  },
  available: {
    tone: "text-emerald-700 dark:text-emerald-300",
    message: (host) => `${host} is available`,
  },
  taken: {
    tone: "text-red-700 dark:text-red-300",
    message: () => "This workspace URL is already taken.",
  },
  reserved: {
    tone: "text-red-700 dark:text-red-300",
    message: () => "This workspace URL is reserved. Please choose another.",
  },
  invalid: {
    tone: "text-red-700 dark:text-red-300",
    message: () => "Use lowercase letters, numbers, and hyphens only.",
  },
  error: {
    tone: "text-amber-800 dark:text-amber-200",
    message: () => "We couldn't check this URL. Try again in a moment.",
  },
};

export function WorkspaceUrlField({
  slug,
  baseDomain,
  state,
  status,
  fieldError,
  onChange,
  onSelectSuggestion,
}: {
  slug: string;
  baseDomain: string;
  state: WorkspaceUrlUiState;
  status: WorkspaceAvailability | null;
  fieldError?: string;
  onChange: (value: string) => void;
  onSelectSuggestion: (value: string) => void;
}) {
  const hostname = status?.hostname || (slug ? `${slug}.${baseDomain}` : "");
  const httpsUrl = workspaceHttpsUrl(slug, baseDomain);
  const feedback = FEEDBACK[state];
  const invalid = state === "taken" || state === "reserved" || state === "invalid";
  const suggestions = status?.suggestions || [];

  return (
    <div className="space-y-4">
      <div>
        <label htmlFor="workspace-slug" className="mb-1.5 block text-sm font-medium">
          Workspace URL <span className="text-destructive" aria-hidden>*</span>
        </label>
        <div
          className={cn(
            "flex flex-col overflow-hidden rounded-xl border bg-brand-surface focus-within:ring-2 focus-within:ring-ring sm:flex-row sm:items-stretch",
            invalid || fieldError ? "border-destructive" : "border-input",
            state === "available" && "border-brand-primary"
          )}
        >
          <Input
            id="workspace-slug"
            value={slug}
            onChange={(e) => onChange(e.target.value)}
            autoComplete="off"
            spellCheck={false}
            aria-invalid={invalid || Boolean(fieldError)}
            aria-describedby="workspace-url-status workspace-url-preview"
            className="border-0 bg-transparent font-mono text-sm focus-visible:ring-0"
            placeholder="barista"
          />
          <span className="shrink-0 border-t border-border bg-muted/50 px-3 py-2 font-mono text-xs text-muted-foreground sm:flex sm:items-center sm:border-l sm:border-t-0">
            .{baseDomain}
          </span>
        </div>
      </div>

      <div
        id="workspace-url-status"
        role="status"
        aria-live="polite"
        className={cn("flex min-h-[1.5rem] items-center gap-2 text-sm font-medium", feedback?.tone)}
      >
        {state === "checking" ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : null}
        {state === "available" ? <CheckCircle2 className="h-4 w-4" aria-hidden /> : null}
        {invalid ? <XCircle className="h-4 w-4" aria-hidden /> : null}
        {feedback ? <span>{feedback.message(hostname)}</span> : null}
        {fieldError ? <span className="text-red-700 dark:text-red-300">{fieldError}</span> : null}
      </div>

      {(state === "taken" || state === "reserved") && suggestions.length > 0 ? (
        <div>
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Try
          </p>
          <div className="flex flex-wrap gap-2">
            {suggestions.map((item) => (
              <button
                key={item}
                type="button"
                onClick={() => onSelectSuggestion(item)}
                className="rounded-full border border-brand-primary/25 bg-brand-surface px-3 py-1.5 font-mono text-xs font-semibold text-brand-soft-foreground shadow-sm transition hover:border-brand-primary hover:bg-brand-soft focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                {item}
              </button>
            ))}
          </div>
        </div>
      ) : null}

      <div
        id="workspace-url-preview"
        className="rounded-2xl border border-border bg-brand-soft p-4"
      >
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Your workspace will be available at
        </p>
        <p className="mt-1 break-all font-mono text-sm font-semibold text-brand-deep">
          {httpsUrl || `https://your-company.${baseDomain}`}
        </p>
      </div>
    </div>
  );
}
