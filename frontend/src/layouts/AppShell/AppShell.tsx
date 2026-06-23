import { Outlet } from "react-router-dom";
import { PageMetaProvider } from "@/contexts/PageMetaContext";
import { SubscriptionAlertDialog } from "@/components/platform/SubscriptionAlertDialog";
import { CloudSyncManager } from "@/components/desktop/CloudSyncManager";
import { Sidebar } from "@/layouts/Sidebar/Sidebar";
import { Header } from "@/layouts/Header/Header";
import { FooterStatusBar } from "@/layouts/Footer/FooterStatusBar";

export function AppShell() {
  return (
    <PageMetaProvider>
      <SubscriptionAlertDialog />
      <CloudSyncManager />
      <div className="flex h-screen overflow-hidden bg-background">
        <Sidebar />
        <div className="flex flex-1 flex-col overflow-hidden">
          <Header />
          <main className="flex-1 overflow-y-auto p-6 scrollbar-thin">
            <Outlet />
          </main>
          <FooterStatusBar />
        </div>
      </div>
    </PageMetaProvider>
  );
}
