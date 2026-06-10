import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

export interface PageMeta {
  title: string;
  description?: string;
  breadcrumbs?: string[];
}

interface PageMetaContextValue {
  meta: PageMeta;
  setMeta: (meta: PageMeta) => void;
}

const PageMetaContext = createContext<PageMetaContextValue | null>(null);

export function PageMetaProvider({ children }: { children: ReactNode }) {
  const [meta, setMeta] = useState<PageMeta>({ title: "Dashboard", breadcrumbs: ["Home"] });

  return (
    <PageMetaContext.Provider value={{ meta, setMeta }}>
      {children}
    </PageMetaContext.Provider>
  );
}

export function usePageMeta() {
  const ctx = useContext(PageMetaContext);
  if (!ctx) throw new Error("usePageMeta must be used within PageMetaProvider");
  return ctx;
}

export function useSetPageMeta(meta: PageMeta) {
  const { setMeta } = usePageMeta();
  useEffect(() => {
    setMeta(meta);
  }, [meta.title, meta.description, meta.breadcrumbs?.join("/"), setMeta]);
}
