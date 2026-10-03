import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowLeft, Mail } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { SafariLogo } from "@/components/brand/SafariLogo";

export function ForgotPasswordPage() {
  return (
    <div className="flex min-h-dvh flex-col bg-background">
      <div className="safari-brand-rule h-1 w-full" aria-hidden />
      <div className="flex flex-1 flex-col items-center justify-center px-4 py-10">
      <SafariLogo size="md" className="mb-8" />
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-md rounded-2xl border border-border bg-brand-surface p-6 shadow-[0_1px_2px_hsl(var(--foreground)/0.04),0_12px_32px_-12px_hsl(var(--brand-primary)/0.18)] sm:p-8"
      >
        <Link
          to="/login"
          className="mb-6 inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to sign in
        </Link>

        <h1 className="text-2xl font-bold tracking-tight">Reset your password</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Enter your email and we&apos;ll send you a verification code.
        </p>

        <form className="mt-8 space-y-5" onSubmit={(e) => e.preventDefault()}>
          <div className="space-y-2">
            <Label htmlFor="email">Email address</Label>
            <div className="relative">
              <Mail aria-hidden className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input id="email" type="email" placeholder="you@company.com" className="pl-11" />
            </div>
          </div>
          <Button type="submit" className="w-full" size="lg">
            Send verification code
          </Button>
        </form>
      </motion.div>
      </div>
    </div>
  );
}
