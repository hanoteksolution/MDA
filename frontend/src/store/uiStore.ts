import { create } from "zustand";

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

export const useUIStore = create<UIState>((set) => ({
  sidebarCollapsed: typeof window !== "undefined" && window.innerWidth <= 1440,
  darkMode: localStorage.getItem("darkMode") === "true",
  notificationDrawerOpen: false,
  activeWorkspace: localStorage.getItem("activeWorkspace") || "overview",
  toggleSidebar: () =>
    set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
  setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),
  toggleDarkMode: () =>
    set((state) => {
      const darkMode = !state.darkMode;
      localStorage.setItem("darkMode", String(darkMode));
      document.documentElement.classList.toggle("dark", darkMode);
      return { darkMode };
    }),
  setNotificationDrawerOpen: (open) => set({ notificationDrawerOpen: open }),
  toggleNotificationDrawer: () =>
    set((state) => ({ notificationDrawerOpen: !state.notificationDrawerOpen })),
  setActiveWorkspace: (code) => {
    localStorage.setItem("activeWorkspace", code);
    set({ activeWorkspace: code });
  },
}));
