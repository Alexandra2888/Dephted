"use client";

import { useEffect } from "react";
import { wakeBackend } from "@/lib/api/wake";

/** Re-ping before Render's ~15 min idle spin-down while the tab is visible. */
const KEEP_AWAKE_MS = 10 * 60 * 1000;

/**
 * Wakes the FastAPI host on first paint, when the tab becomes visible again,
 * and every 10 minutes while the tab stays in the foreground.
 */
export function useWakeBackend() {
  useEffect(() => {
    let cancelled = false;

    const ping = () => {
      if (cancelled || document.visibilityState === "hidden") return;
      void wakeBackend();
    };

    ping();
    const id = window.setInterval(ping, KEEP_AWAKE_MS);
    document.addEventListener("visibilitychange", ping);

    return () => {
      cancelled = true;
      window.clearInterval(id);
      document.removeEventListener("visibilitychange", ping);
    };
  }, []);
}
