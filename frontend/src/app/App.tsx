import { useEffect } from "react";
import { AppRouter } from "@/app/router";
import { DesktopBootGate } from "@/components/desktop/DesktopBootGate";
import { useAuthStore } from "@/store/authStore";
import { useUIStore } from "@/store/uiStore";
import { startSessionMonitor } from "@/services/api/http";

export function App() {
  const loadUser = useAuthStore((s) => s.loadUser);
  const darkMode = useUIStore((s) => s.darkMode);

  useEffect(() => {
    loadUser();
  }, [loadUser]);

  useEffect(() => {
    return startSessionMonitor(60_000);
  }, []);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", darkMode);
  }, [darkMode]);

  return (
    <DesktopBootGate>
      <AppRouter />
    </DesktopBootGate>
  );
}
