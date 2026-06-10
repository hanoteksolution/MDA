import { create } from "zustand";

interface UIState {
  sidebarCollapsed: boolean;
  darkMode: boolean;
  toggleSidebar: () => void;
  toggleDarkMode: () => void;
}

export const useUIStore = create<UIState>((set) => ({
  sidebarCollapsed: false,
  darkMode: localStorage.getItem("darkMode") === "true",
  toggleSidebar: () =>
    set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
  toggleDarkMode: () =>
    set((state) => {
      const darkMode = !state.darkMode;
      localStorage.setItem("darkMode", String(darkMode));
      document.documentElement.classList.toggle("dark", darkMode);
      return { darkMode };
    }),
}));
