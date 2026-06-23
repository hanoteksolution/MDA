import { CloudConnectionForm } from "@/components/desktop/CloudConnectionForm";

export function ConnectionPage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-background px-6 py-10">
      <div className="w-full max-w-2xl">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-foreground">Shop connection</h1>
          <p className="mt-2 text-sm text-muted-foreground">
            Link this PC to your shop on the live server. Daily work still runs locally — internet is only
            needed for the first sign-in and to upload sales.
          </p>
        </div>
        <div className="rounded-2xl border border-border bg-card p-6 shadow-sm">
          <CloudConnectionForm showBackLink />
        </div>
      </div>
    </div>
  );
}
