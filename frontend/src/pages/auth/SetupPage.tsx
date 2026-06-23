import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Building2, Lock, User, ArrowRight, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { FormField, FormGrid, FormSection } from "@/components/forms/FormField";
import { LoginBrandingPanel } from "@/components/auth/LoginBrandingPanel";
import { setupApi } from "@/services/api/setup";
import { useAuthStore } from "@/store/authStore";
import { clearBrandingCache } from "@/documents/branding";

export function SetupPage() {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuthStore();
  const [checking, setChecking] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [companyName, setCompanyName] = useState("");
  const [legalName, setLegalName] = useState("");
  const [taxId, setTaxId] = useState("");
  const [companyEmail, setCompanyEmail] = useState("");
  const [companyPhone, setCompanyPhone] = useState("");
  const [address, setAddress] = useState("");

  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  useEffect(() => {
    if (isAuthenticated) {
      navigate("/dashboard", { replace: true });
      return;
    }

    setupApi.status()
      .then((res) => {
        if (!res.data.needs_setup) {
          navigate("/login", { replace: true });
        }
      })
      .catch(() => setError("Could not reach the local API. Ensure the backend is running."))
      .finally(() => setChecking(false));
  }, [isAuthenticated, navigate]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setSaving(true);
    try {
      const res = await setupApi.complete({
        company: {
          name: companyName,
          legal_name: legalName,
          tax_id: taxId,
          email: companyEmail,
          phone: companyPhone,
          address,
        },
        user: { username, email, password },
      });

      localStorage.setItem("access_token", res.data.access);
      localStorage.setItem("refresh_token", res.data.refresh);
      clearBrandingCache();
      useAuthStore.setState({
        user: res.data.user,
        isAuthenticated: true,
        isLoading: false,
        error: null,
      });
      navigate("/dashboard", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Setup failed");
    } finally {
      setSaving(false);
    }
  };

  if (checking) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col lg:flex-row">
      <div className="lg:w-[45%] order-2 lg:order-1">
        <LoginBrandingPanel />
      </div>

      <div className="relative flex lg:w-[55%] order-1 lg:order-2 flex-col justify-center bg-background px-6 py-10 sm:px-10 lg:px-12 xl:px-16 overflow-y-auto">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mx-auto w-full max-w-xl"
        >
          <div className="mb-8">
            <h1 className="text-2xl font-bold tracking-tight">Welcome to MDA ERP</h1>
            <p className="mt-2 text-sm text-muted-foreground">
              Set up your company profile and create the administrator account.
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-8">
            <FormSection
              title="Company Profile"
              description="You can update these details anytime in Settings."
            >
              <FormGrid>
                <FormField label="Company Name" required>
                  <Input required value={companyName} onChange={(e) => setCompanyName(e.target.value)} />
                </FormField>
                <FormField label="Legal Name">
                  <Input value={legalName} onChange={(e) => setLegalName(e.target.value)} />
                </FormField>
                <FormField label="Tax ID">
                  <Input value={taxId} onChange={(e) => setTaxId(e.target.value)} />
                </FormField>
                <FormField label="Company Email">
                  <Input type="email" value={companyEmail} onChange={(e) => setCompanyEmail(e.target.value)} />
                </FormField>
                <FormField label="Phone">
                  <Input value={companyPhone} onChange={(e) => setCompanyPhone(e.target.value)} />
                </FormField>
                <FormField label="Address" className="md:col-span-2">
                  <Input value={address} onChange={(e) => setAddress(e.target.value)} />
                </FormField>
              </FormGrid>
            </FormSection>

            <FormSection
              title="Administrator Account"
              description="This user will have full super-admin access."
            >
              <FormGrid>
                <FormField label="Username" required>
                  <div className="relative">
                    <User className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                    <Input
                      required
                      className="pl-10"
                      value={username}
                      onChange={(e) => setUsername(e.target.value)}
                    />
                  </div>
                </FormField>
                <FormField label="Email" required>
                  <Input required type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
                </FormField>
                <FormField label="Password" required>
                  <div className="relative">
                    <Lock className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                    <Input
                      required
                      type="password"
                      minLength={8}
                      className="pl-10"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                    />
                  </div>
                </FormField>
                <FormField label="Confirm Password" required>
                  <Input
                    required
                    type="password"
                    minLength={8}
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                  />
                </FormField>
              </FormGrid>
            </FormSection>

            {error && (
              <p className="text-sm text-destructive" role="alert">
                {error}
              </p>
            )}

            <Button type="submit" className="w-full" size="lg" loading={saving}>
              <Building2 className="h-4 w-4" />
              Complete Setup
              <ArrowRight className="h-4 w-4" />
            </Button>
          </form>

          <div className="mt-8 flex items-center justify-center gap-2 text-muted-foreground">
            <ShieldCheck className="h-4 w-4 text-primary" />
            <span className="text-xs">Your data is stored locally on this device</span>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
