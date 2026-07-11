import { create } from "zustand";

interface UIState {
  sidebarCollapsed: boolean;
  darkMode: boolean;
  toggleSidebar: () => void;
  setSidebarCollapsed: (collapsed: boolean) => void;
  toggleDarkMode: () => void;
}

export const useUIStore = create<UIState>((set) => ({
  sidebarCollapsed: typeof window !== "undefined" && window.innerWidth <= 1440,
  darkMode: localStorage.getItem("darkMode") === "true",
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
}));
