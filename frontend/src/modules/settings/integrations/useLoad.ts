import { useCallback, useEffect, useRef, useState } from "react";
import { describeApiError } from "./lib";

export interface Loaded<T> {
  data: T[];
  loading: boolean;
  error: string | null;
  reload: () => Promise<void>;
}

/** Fetch a list once (and on demand). `enabled=false` skips the request entirely (no permission). */
export function useLoad<T>(fetcher: () => Promise<{ data: T[] }>, enabled: boolean, deps: unknown[] = []): Loaded<T> {
  const [data, setData] = useState<T[]>([]);
  const [loading, setLoading] = useState(enabled);
  const [error, setError] = useState<string | null>(null);
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;
  const seq = useRef(0);

  const reload = useCallback(async () => {
    if (!enabled) return;
    const mine = ++seq.current;
    setLoading(true);
    try {
      const res = await fetcherRef.current();
      if (mine !== seq.current) return; // a newer request superseded this one
      setData(res.data ?? []);
      setError(null);
    } catch (err) {
      if (mine !== seq.current) return;
      setError(describeApiError(err, "Request failed."));
    } finally {
      if (mine === seq.current) setLoading(false);
    }
  }, [enabled]);

  useEffect(() => {
    void reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reload, ...deps]);

  return { data, loading: enabled && loading, error, reload };
}
