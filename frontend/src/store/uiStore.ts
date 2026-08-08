import { create } from "zustand";
import { applyWorkspaceBrand } from "@/theme/workspaceBrand";

interface UIState {
  sidebarCollapsed: boolean;
  darkMode: boolean;
  notificationDrawerOpen: boolean;
  /** Module switcher workspace code (overview | gym | pos | …) */
  activeWorkspace: string;
  toggleSidebar: () => void;
  setSidebarCollapsed: (collapsed: boolean) => void;
  toggleDarkMode: () => void;
  setNotificationDrawerOpen: (open: boolean) => void;
  toggleNotificationDrawer: () => void;
  setActiveWorkspace: (code: string) => void;
}

const initialDarkMode = typeof window !== "undefined" && localStorage.getItem("darkMode") === "true";
const initialWorkspace =
  (typeof window !== "undefined" && localStorage.getItem("activeWorkspace")) || "hub";

if (typeof document !== "undefined") {
  document.documentElement.classList.toggle("dark", initialDarkMode);
  applyWorkspaceBrand(initialWorkspace, initialDarkMode);
}

export const useUIStore = create<UIState>((set, get) => ({
  sidebarCollapsed: typeof window !== "undefined" && window.innerWidth <= 1440,
  darkMode: initialDarkMode,
  notificationDrawerOpen: false,
  activeWorkspace: initialWorkspace,
  toggleSidebar: () =>
    set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
  setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),
  toggleDarkMode: () =>
    set((state) => {
      const darkMode = !state.darkMode;
      localStorage.setItem("darkMode", String(darkMode));
      document.documentElement.classList.toggle("dark", darkMode);
      applyWorkspaceBrand(state.activeWorkspace, darkMode);
      return { darkMode };
    }),
  setNotificationDrawerOpen: (open) => set({ notificationDrawerOpen: open }),
  toggleNotificationDrawer: () =>
    set((state) => ({ notificationDrawerOpen: !state.notificationDrawerOpen })),
  setActiveWorkspace: (code) => {
    localStorage.setItem("activeWorkspace", code);
    applyWorkspaceBrand(code, get().darkMode);
    set({ activeWorkspace: code });
  },
}));
