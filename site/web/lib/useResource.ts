"use client";

import { useEffect, useState } from "react";

export function useResource<T>(load: (signal: AbortSignal) => Promise<T>) {
  const [data, setData] = useState<T | null>(null);
  const [pending, setPending] = useState(true);
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setPending(true);
    setError("");
    setData(null);
    load(controller.signal)
      .then(value => { if (!controller.signal.aborted) setData(value); })
      .catch((cause: unknown) => {
        if (!controller.signal.aborted) setError(cause instanceof Error && cause.message !== "Failed to fetch" ? cause.message : "収録情報に接続できませんでした。");
      })
      .finally(() => { if (!controller.signal.aborted) setPending(false); });
    return () => controller.abort();
  }, [load, attempt]);
  return { data, pending, error, retry: () => setAttempt(value => value + 1) };
}
