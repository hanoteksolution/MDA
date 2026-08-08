import { Outlet, useLocation } from "react-router-dom";
import { useEffect } from "react";
import { PageMetaProvider } from "@/contexts/PageMetaContext";
import { NotificationDrawer } from "@/components/notifications/NotificationDrawer";
import { SubscriptionAlertDialog } from "@/components/platform/SubscriptionAlertDialog";
import { SubscriptionPaywallBanner } from "@/components/platform/SubscriptionPaywallBanner";
import { CloudSyncManager } from "@/components/desktop/CloudSyncManager";
import { Sidebar } from "@/layouts/Sidebar/Sidebar";
import { Header } from "@/layouts/Header/Header";
import { FooterStatusBar } from "@/layouts/Footer/FooterStatusBar";
import { useUIStore } from "@/store/uiStore";
import { cn } from "@/utils/cn";

/** Collapse sidebar on laptop-width screens so catalog / tables have room. */
function useLaptopSidebarCollapse() {
  const setSidebarCollapsed = useUIStore((s) => s.setSidebarCollapsed);

  useEffect(() => {
    const mq = window.matchMedia("(max-width: 1440px)");
    const apply = () => {
      if (mq.matches) setSidebarCollapsed(true);
    };
    apply();
    mq.addEventListener("change", apply);
    return () => mq.removeEventListener("change", apply);
  }, [setSidebarCollapsed]);
}

export function AppShell() {
  const location = useLocation();
  const isPos = location.pathname === "/pos" || location.pathname.startsWith("/pos/");
  useLaptopSidebarCollapse();

  return (
    <PageMetaProvider>
      <SubscriptionAlertDialog />
      <CloudSyncManager />
      <NotificationDrawer />
      <div className="flex h-dvh max-h-dvh overflow-hidden bg-background">
        <Sidebar />
        <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
          <Header compact={isPos} />
          <SubscriptionPaywallBanner />
          <main
            className={cn(
              "min-h-0 flex-1 overflow-y-auto scrollbar-thin",
              isPos ? "overflow-hidden p-0 sm:p-2 xl:p-3" : "p-4 xl:p-6"
            )}
          >
            <Outlet />
          </main>
          {!isPos && <FooterStatusBar />}
        </div>
      </div>
    </PageMetaProvider>
  );
}
