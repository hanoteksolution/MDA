import { useEffect, useState } from "react";
import type { PaginatedResponse } from "@/types/models/catalog";

export interface ListResult<T> {
  data: PaginatedResponse<T>;
}

export interface UsePaginatedListOptions {
  pageSize?: number;
}

/** Server-side paginated list. `fetcher` should be a stable reference (e.g. API module method). */
export function usePaginatedList<T, P extends Record<string, string | number | undefined>>(
  fetcher: (params: P & { page: number; page_size: number }) => Promise<ListResult<T>>,
  filters: P,
  options: UsePaginatedListOptions = {}
) {
  const { pageSize: initialPageSize = 10 } = options;
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(initialPageSize);
  const [data, setData] = useState<T[]>([]);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(true);
  const [reloadToken, setReloadToken] = useState(0);

  const filterKey = JSON.stringify(filters);

  useEffect(() => {
    setPage(1);
  }, [filterKey, pageSize]);

  useEffect(() => {
    let active = true;
    setLoading(true);
    fetcher({ ...(filters as P), page, page_size: pageSize })
      .then((res) => {
        if (!active) return;
        setData(res.data.results);
        setTotal(res.data.count);
        setTotalPages(
          res.data.total_pages || Math.max(1, Math.ceil(res.data.count / pageSize))
        );
      })
      .catch(() => {
        if (!active) return;
        setData([]);
        setTotal(0);
        setTotalPages(1);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [filterKey, page, pageSize, reloadToken, fetcher]);

  const reload = () => setReloadToken((n) => n + 1);

  return {
    data,
    loading,
    page,
    setPage,
    pageSize,
    setPageSize,
    total,
    totalPages,
    reload,
  };
}
