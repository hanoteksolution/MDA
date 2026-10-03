import { Outlet, Navigate } from "react-router-dom";
import { MotionConfig } from "framer-motion";
import { useAuthStore } from "@/store/authStore";

/** Public auth/onboarding routes render inside the Safari platform brand scope. */
export function AuthLayout() {
  return (
    <MotionConfig reducedMotion="user">
      <div className="safari-brand min-h-dvh bg-background">
        <Outlet />
      </div>
    </MotionConfig>
  );
}

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const isLoading = useAuthStore((s) => s.isLoading);

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
}
