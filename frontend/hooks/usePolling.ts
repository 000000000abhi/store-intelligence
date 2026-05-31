'use client';

import { useEffect, useState } from 'react';

export function usePolling<T>(
  fetcher: () => Promise<T>,
  intervalMs = 10000
): { data: T | null; loading: boolean; error: string | null } {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    const fetch = async () => {
      try {
        const result = await fetcher();
        if (active) {
          setData(result);
          setError(null);
        }
      } catch (e) {
        if (active) setError(e instanceof Error ? e.message : 'Unknown error');
      } finally {
        if (active) setLoading(false);
      }
    };

    fetch();
    const timer = setInterval(fetch, intervalMs);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, [fetcher, intervalMs]);

  return { data, loading, error };
}
