import { useEffect, useState } from "react";

const POLL_MS = 2000;

/** Load data, and keep reloading every two seconds while `again` says so. */
export function useLoad<T>(
  load: () => Promise<T>,
  again?: (data: T) => boolean,
) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    let live = true;
    load()
      .then((loaded) => {
        if (live) {
          setData(loaded);
          setError(null);
        }
      })
      .catch((failure: unknown) => {
        if (live) setError(String(failure));
      });
    return () => {
      live = false;
    };
  }, [load, tick]);

  useEffect(() => {
    if (data === null || !again?.(data)) return;
    const timer = setTimeout(() => {
      setTick((count) => count + 1);
    }, POLL_MS);
    return () => {
      clearTimeout(timer);
    };
  }, [data, again]);

  const reload = () => {
    setTick((count) => count + 1);
  };
  return { data, error, reload };
}
